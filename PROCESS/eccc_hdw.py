"""

    Use files that have been downloaded to the avail directory
    for a specific model and save hwd to a geodataframe for later forecasts
    Save a different geodataframe for each time step
    Save to the ./avail directory

"""
#%%
import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
import metpy.calc as mpcalc

import os
import json
import cfgrib

from metpy.units import units 
from shapely.geometry import Point
from context import forecast_dir, download_dir, utils_dir
from file_funcs import find_files, match_grib_variable

#%%
with open(f"{forecast_dir}/forecast.json", 'r') as f:
    forecast_info = json.load(f)

rdps_horizon_inits = forecast_info["RDPS"]["horizon"]
rdps_horizon = np.arange(rdps_horizon_inits[0], rdps_horizon_inits[1], rdps_horizon_inits[2])
print(rdps_horizon)

with open(f"{download_dir}/rdps_vars.json", "r") as f:
    rdps_info = json.load(f)
file_names = rdps_info["wx_vars"]
grib_names = rdps_info["grib_vars"]

#%%
# collect all pressure data
pressure_dfs = []
for hh in rdps_horizon:
    # extract the surface pressure for this forecast hour
    hourly_files = [f for f in find_files(f"{download_dir}avail/", "Pressure_Sfc") if f"PT{hh:03}H" in f and f.endswith(".grib2")]
    print(hourly_files)

    for file in hourly_files:
        print(f"Processing file: {file}")

        ds = cfgrib.open_dataset(file)
        data_var = next(iter(ds.data_vars))
        da = ds[data_var]

        pressure_df = da.to_dataframe(name=f"Pressure_Sfc_{hh:03}").reset_index()
        pressure_df = pressure_df[["latitude", "longitude", f"Pressure_Sfc_{hh:03d}"]].drop_duplicates(subset=["latitude", "longitude"])
        pressure_dfs.append(pressure_df)

# merge all pressure dataframes together
if pressure_dfs:
    all_pressure = pressure_dfs[0]
    for pdf in pressure_dfs[1:]:
        all_pressure = all_pressure.merge(pdf, on=["latitude", "longitude"], how="outer")
    
    # divide surface pressure columns by 100 to convert to hPa
    pressure_cols = [col for col in all_pressure.columns if col.startswith("Pressure_Sfc_")]
    all_pressure[pressure_cols] = all_pressure[pressure_cols] / 100

    # compute 40m, 80m, and 120m pressure for each forecast hour
    for hh in rdps_horizon:
        surface_col = f"Pressure_Sfc_{hh:03}"
        if surface_col not in all_pressure.columns:
            continue

        surface_pressure = all_pressure[surface_col].astype(float).values * units.hPa

        for height_m in (40, 80, 120):
            out_col = f"{height_m}m_press_h{hh:03}"
            all_pressure[out_col] = mpcalc.add_height_to_pressure(
                surface_pressure,
                height_m * units.meter,
            ).to("hPa").magnitude

    print(f"Created all_pressure with {len(all_pressure)} rows")

print(all_pressure.head())

#%%
# helper to get the level string from the file name
def parse_level_from_filename(file_path):
    name = os.path.basename(file_path)
    if "Pressure_Sfc" in name:
        return "surface"
    if "_AGL-" in name:
        str_long = name.split("_AGL-")[-1]
        return str_long.split("_")[0]
    if "_IsbL-" in name:
        str_long = name.split("_IsbL-")[-1]
        return f"{str_long.split("_")[0]}"
    return None

# %%
all_data = None
for hh in rdps_horizon:
    print(f"Processing forecast hour: {hh}")

    # extract all files with the substring hourly in it
    search_string = f"PT{hh:03}H"
    hourly_files = find_files(f"{download_dir}avail/", search_string)
    print(hourly_files)

    # loop through the files and extract the variables we need, save to a geodataframe
    for file in hourly_files[0:10]: # ***** NOTE *****
        print(f"Processing file: {file}")

        if file.endswith(".idx"):
            continue

        file_key, grib_name = match_grib_variable(file, file_names, grib_names)
        if file_key is None or grib_name is None:
            print(f"Skipping unmatched file: {file}")
            continue

        ds = cfgrib.open_dataset(file)
        data_var = next(iter(ds.data_vars))
        da = ds[data_var]

        variable_col = f"{grib_name}_h{hh:03}"
        level_value = parse_level_from_filename(file)
        level_col = f"{grib_name}_lev_{level_value}_h{hh:03}"

        df = da.to_dataframe(name=variable_col).reset_index()
        df = df[["latitude", "longitude", variable_col]]
        df[level_col] = level_value

        if all_data is None:
            all_data = df
        else:
            all_data = all_data.merge(df, on=["latitude", "longitude"], how="outer")

# %%
if all_data is not None:
    if 'all_pressure' in locals():
        merged_df = all_data.merge(all_pressure, on=["latitude", "longitude"], how="outer")
        print(merged_df.head())
    else:
        print(all_data.head())

# %%
# caculate the Vapour Pressure Deficit for each height and isobaric level  
lev_cols = sorted([c for c in merged_df.columns if "lev" in c])
print(lev_cols)

# %%
# note get unqiue heights from this list (we already have the forecast hours)
unique_levs = list(set([col.split("_")[2] for col in lev_cols ]))
print(unique_levs)

# %%
# loop through forecast hours and unique levels
vpd = pd.DataFrame()
for hh in rdps_horizon:
    print(f"Processing forecast hour: {hh}")

    for lev in unique_levs:
        print(f"at level {lev}") 

        # calculate the VPD 
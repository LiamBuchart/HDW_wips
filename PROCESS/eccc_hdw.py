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
#rdps_horizon = rdps_horizon[0]  # ***** NOTE *****
print(rdps_horizon)

with open(f"{download_dir}/rdps_vars.json", "r") as f:
    rdps_info = json.load(f)
file_names = rdps_info["wx_vars"]
grib_names = rdps_info["grib_vars"]

#%%
# collect all pressure data
pressure_dfs = []
Pname = "Pressure_Sfc_h"
for hh in rdps_horizon:
    # extract the surface pressure for this forecast hour
    hourly_files = [f for f in find_files(f"{download_dir}avail/", "Pressure_Sfc") if f"PT{hh:03}H" in f and f.endswith(".grib2")]
    print(hourly_files)

    for file in hourly_files:
        print(f"Processing file: {file}")

        ds = cfgrib.open_dataset(file)
        data_var = next(iter(ds.data_vars))
        da = ds[data_var] / 100  # to hPa

        pressure_df = da.to_dataframe(name=f"{Pname}{hh:03}").reset_index()
        pressure_df = pressure_df[["latitude", "longitude", f"Pressure_Sfc_h{hh:03d}"]].drop_duplicates(subset=["latitude", "longitude"])
        pressure_dfs.append(pressure_df)
print(pressure_dfs)

#%%
# merge all pressure dataframes together
if pressure_dfs:
    all_pressure = pressure_dfs[0]
    for pdf in pressure_dfs[1:]:
        all_pressure = all_pressure.merge(pdf, on=["latitude", "longitude"], how="outer")
    
    # compute 40m, 80m, and 120m pressure for each forecast hour
    for hh in rdps_horizon:
        surface_col = f"{Pname}{hh:03}"
        print(surface_col)
        if surface_col not in all_pressure.columns:
            continue

        surface_pressure = all_pressure[surface_col].astype(float).values * units.hPa

        for height_m in (40, 80, 120):
            out_col = f"{height_m}_press_h{hh:03}"
            print(out_col)
            all_pressure[out_col] = mpcalc.add_height_to_pressure(
                surface_pressure,
                height_m * units.meter,
            ).to("hPa").magnitude

    print(f"Created all_pressure with {len(all_pressure)} rows")

print(all_pressure.head())
print(all_pressure.columns)

#%%
# helper to get the level string from the file name
def parse_level_from_filename(file_path):
    name = os.path.basename(file_path)
    if "Pressure_Sfc" in name:
        return None
    if "_AGL-" in name:
        str_long = name.split("_AGL-")[-1]
        return None
    if "_IsbL-" in name:
        str_long = name.split("_IsbL-")[-1]
        return f"{str_long.split("_")[0]}"
    return None

# %%
# ***** NOTE ***** need to revamp this loop - parallelize and clean up column names. There is some weird _x and _y being added 
all_data = None
for hh in rdps_horizon:
    print(f"Processing forecast hour: {hh}")

    # extract all files with the substring hourly in it
    search_string = f"PT{hh:03}H"
    hourly_files = find_files(f"{download_dir}avail/", search_string)
    print(hourly_files)

    # loop through the files and extract the variables we need, save to a geodataframe
    for file in hourly_files:  # ***** NOTE *****
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

        # naming columns correctly is nice - one for the variable and one with the pressure level
        variable_col = f"{grib_name}_h{hh:03}"
        level_value = parse_level_from_filename(file)
        if level_value and level_value.startswith("0"):
            level_value = level_value[1:]
        print("The level value is: ", level_value)

        df = da.to_dataframe(name=variable_col).reset_index()
        df = df[["latitude", "longitude", variable_col]]
        if level_value:
            print("Adding level column")
            level_col = f"{level_value}_press_h{hh:03}"

            print(variable_col, level_col)

            if level_col not in (all_data.columns if all_data is not None else []):
                df[level_col] = int(level_value) 

        # merge the dataframe as needed
        print(df.columns)
        if all_data is None:
            all_data = df
        else:
            all_data = all_data.merge(df, on=["latitude", "longitude"], how="outer")   
print("Dunzzo")

# %%
if all_data is not None:
    if 'all_pressure' in locals():
        merged_df = all_data.merge(all_pressure, on=["latitude", "longitude"], how="outer")
        print(merged_df.head())
    else:
        print(all_data.head())

#%%
print(sorted(list(merged_df.columns)))

# %%
# caculate the Vapour Pressure Deficit for each height and isobaric level  
lev_cols = sorted([c for c in merged_df.columns if "press" in c])
print(lev_cols)

# %%
# note get unqiue heights from this list (we already have the forecast hours)
unique_levs = list(set([col.split("_")[0] for col in lev_cols ]))
print(unique_levs)

#%%
def calc_VPD(temp, rh, press):
    # df outputs for a specific height
    temp = temp * units("degC")
    press = press * units("hPa")

    mixing = mpcalc.mixing_ratio_from_relative_humidity(press, temp, rh, phase='liquid').to('g/kg')
    svp = mpcalc.saturation_vapor_pressure(temp, phase='liquid').to('hPa')
    vp = mpcalc.vapor_pressure(press, mixing).to('hPa')

    print(np.mean(svp), np.mean(vp))

    vpd = svp - vp

    print(np.mean(vpd))

    return vpd

# %%
# loop through forecast hours and unique levels
all_cols = merged_df.columns
for hh in rdps_horizon:
    print(f"Processing forecast hour: {hh:03}")

    # have the surface pressure available, 
    # same with the lat and lon
    sfc_press = merged_df[f"{Pname}{hh:03}"]
    lats = merged_df["latitude"]
    lons = merged_df["longitude"]

    for lev in unique_levs:
        print(f"at level {lev}")

        #else: 
        #    print(f"Level - {lev} does not have enough data to get VPD") 
        r_pat = f"r{lev}"
        t_pat = f"t{lev}"
        p_pat = f"{lev}_press_"
        hh_pat = f"h{hh:03}"

        # verify both r, t, and press are prsent
        # Get the actual strings (column names)
        r_col = [c for c in all_cols if r_pat in c and hh_pat in c]
        t_col = [c for c in all_cols if t_pat in c and hh_pat in c]
        p_col = [c for c in all_cols if p_pat in c and hh_pat in c]

        # Check if they exist
        has_r = bool(r_col)
        has_t = bool(t_col)
        has_p = bool(p_col)

        if has_r and has_t and has_p:
            print(f"Level - {lev} has enough data for VPD...calculating...")
            #selected = merged_df[matched_cols]
            # use selected DataFrame for calculations    
            #print(r_col)
            #print(t_col)
            #print(p_col)

            print(np.mean(merged_df[t_col].values - 273.15),  # convert to Celsius
                  np.mean(merged_df[r_col].values / 100),  # convert to fraction
                  np.mean(merged_df[p_col].values))

            # calcualte the VPD
            merged_df[f"VPD_press_{lev}_h{hh:03}"] = calc_VPD(merged_df[t_col].values - 273.15,  # convert to Celsius
                                                              merged_df[r_col].values / 100,  # convert to fraction
                                                              merged_df[p_col].values)

        else:
            print(f"{lev} does not have enought data")  # empty, or handle missing case

# %%
# loop through merged_df 
# copy all columns that contains "VPD_" into the new dataframe
vpd_cols = [c for c in merged_df.columns if "VPD_" in c]
# same for wind speed
spd_cols = [c for c in merged_df.columns if "ws" in c]

vpd_df = merged_df[["latitude", "longitude"] + vpd_cols].copy()
mws_df = merged_df[["latitude", "longitude"] + spd_cols].copy()

# %%
print(vpd_df.head())
print(mws_df.head())

# %%
hdw_df = pd.DataFrame()
hdw_df = merged_df[["latitude", "longitude"]].copy()

for hh in rdps_horizon:
    print(f"Processing forecast hour: {hh:03}")
    hh_pat = f"h{hh:03}"

    vpd_hh = vpd_df.filter(like=hh_pat)   # select columns for this hour
    mws_hh = mws_df.filter(like=hh_pat)

    vpd_max = vpd_hh.max(axis=1)         # max value for each row
    mws_max = mws_hh.max(axis=1)
    
    hdw_df[f"VPD_max_h{hh:03}"] = vpd_max
    hdw_df[f"MWS_max_h{hh:03}"] = mws_max

    hdw_df[f"HDW_h{hh:03}"] = vpd_max * mws_max

# %%
print(hdw_df.head())\

# %%
# canada plot
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
from datetime import datetime

plot_projection = ccrs.PlateCarree()  # 3978

fig = plt.figure(figsize=(12, 12))
ax = plt.axes(projection=plot_projection)

ax.set_extent(
    [-142, -52, 41, 71],   # lon_min, lon_max, lat_min, lat_max
    crs=ccrs.PlateCarree()
)

# --------------------------------------
# Base map
# --------------------------------------
ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#e6f2ff", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f7f7f7", zorder=1)
ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor="#e6f2ff", edgecolor="black", linewidth=0.3, zorder=2)
ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.8, edgecolor="black", zorder=5)
ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.8, edgecolor="black", zorder=5)
ax.add_feature(cfeature.RIVERS.with_scale("50m"), edgecolor="black", linewidth=0.4, alpha=0.8, zorder=6)
ax.add_feature(
    cfeature.NaturalEarthFeature(
        category="cultural",
        name="admin_1_states_provinces_lines",
        scale="50m",
        facecolor="none",
        zorder=7
    ),
    edgecolor="black",
    linewidth=1
)
ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor="none", edgecolor="#2e6eb5", linewidth=0.35, zorder=7)

# Plot the selected HDW field with an easy-to-change colormap
plot_col = "HDW_h000" if "HDW_h000" in hdw_df.columns else "HWD_h000"
cmap_name = "YlOrBr"  # change to any matplotlib colormap, e.g. "plasma", "terrain", "coolwarm"

plot_data = hdw_df.dropna(subset=[plot_col])
if not plot_data.empty:
    vmin = 0
    vmax = 400
    norm = plt.Normalize(vmin=vmin, vmax=vmax)

    scatter = ax.scatter(
        plot_data["longitude"],
        plot_data["latitude"],
        c=plot_data[plot_col],
        cmap=cmap_name,
        norm=norm,
        s=20,
        alpha=0.8,
        transform=ccrs.PlateCarree(),
        zorder=2,
    )

    cbar = fig.colorbar(
        scatter,
        ax=ax,
        orientation="horizontal",
        fraction=0.04,
        pad=0.01,
        shrink=0.8,
        extend="max",
    )
    cbar.set_label(plot_col)
    cbar.set_ticks(np.arange(vmin, vmax + 1, 50))

plt.title(f"Hot Dry Windy Index: {datetime.now().strftime('%Y-%m-%d')} - 12UTC")

plt.show()


# %%

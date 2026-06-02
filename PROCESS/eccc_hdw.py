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

import os
import json
import cfgrib

from shapely.geometry import Point
from context import forecast_dir, download_dir
from file_funcs import find_files

#%%
with open(f"{forecast_dir}/forecast.json", 'r') as f:
    forecast_info = json.load(f)

rdps_horizon_inits = forecast_info["RDPS"]["horizon"]
rdps_horizon = np.arange(rdps_horizon_inits[0], rdps_horizon_inits[1], rdps_horizon_inits[2])
print(rdps_horizon)

#%%
# geodataframe with data from each variable (temp, rh, ws)
# then store data for each height in a different column
columns = ["rep_date", "forecast_hour", "latitude", "longitude", 
           "2m", "2m-pres", 
           "10m", "10m-pres", 
           "40m", "40m-pres", 
           "80m", "80m-pres",
           "120m", "120m-pres",
           "1015hPa", "1000hPa", "985hPa", "970hPa", 
           "950hPa", "925hPa", "900hPa", "875hPa", "850hPa"]

temp_df = pd.DataFrame(columns=columns)
rh_df = pd.DataFrame(columns=columns)
ws_df = pd.DataFrame(columns=columns)

# %%
for hh in rdps_horizon:
    print(f"Processing forecast hour: {hh}")

    # extract all files with the substring hourly in it
    search_string = f"PT{hh:03}H"
    hourly_files = find_files(f"{download_dir}avail/", search_string)
    print(hourly_files)

    # loop through the files and extract the variables we need, save to a geodataframe
    for file in hourly_files:
        print(f"Processing file: {file}")
        ds = xr.open_dataset(file, engine="cfgrib")
        print(ds)

        # extract the variable from t
    
# %%

"""

    Carry out the functions to download the data from the ECCC datamart, 
    extract the variables we need, and save them to a local directory for processing.

    Start with the 12 UTC model run data for RDPS (every 3h for full forecast length)

    To do: carry out the same process on HRDPS and GDPS

    Liam.Buchart@NRCan-RNCan.gc.ca
    June 1, 2026

"""
#%%
import cfgrib
import os
import xarray as xr
import requests
import shutil
import difflib
import numpy as np
import pandas as pd
import geopandas as gpd
import json
import metpy.calc as mpcalc
from metpy.units import units

from shapely.geometry import Point
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from file_funcs import set_filenames, download_data, clean_avail_dir
from context import forecast_dir

##### User Input #####
date_base = datetime.today()
date = date_base.strftime("%Y-%m-%d")
print(date)
##### END ######

save_dir = "./temp"
with open(f"{forecast_dir}/forecast.json", 'r') as f:
    forecast_info = json.load(f)

rdps_horizon_inits = forecast_info["RDPS"]["horizon"]
fcst_horizon = np.arange(rdps_horizon_inits[0], rdps_horizon_inits[1], rdps_horizon_inits[2])
#fcst_horizon = np.arange(0, 30, 6)  #0, 78, 6)  # every 6h from 0 to 72h forecast

#%%
with open('rdps_vars.json', 'r') as f:
    rdps_info = json.load(f)

# %%
rdps_files = set_filenames("rdps", date, fcst_horizon)
print(rdps_files.shape)

future = [[row["file"], row["full_path"]] for index, row in rdps_files.iterrows()]
print(future)

# %%
print(f"The current time is {datetime.now()}. Starting downloads...")
# Remove duplicate file names before parallel download to avoid collisions
rdps_files = rdps_files.drop_duplicates(subset=["file"])

# parallization cause this thang is slooow
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(download_data, row["full_path"], row["file"], save_dir) for index, row in rdps_files.iterrows()]
    for future in as_completed(futures):
        result = future.result()  # handle result or exceptions if needed
print(f"Downloads completed at {datetime.now()}.")

# %%
clean_avail_dir(save_dir, "./avail")

# %%

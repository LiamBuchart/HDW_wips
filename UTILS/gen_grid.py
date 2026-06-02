""" 

    Generate a .csv file of lat/lon coordinates for
    a specified model. Will be used in HDW processing
    

"""
#%%
from context import download_dir, forecast_dir

import os
import cfgrib

import xarray as xr
import numpy as np
import geopandas as gpd
import geopandas

model_select = "RDPS"  # ["RDPS", "HRDPS", "GDPS"]
save_dir = "./RESOURCES"

#%%
# grab the first file in the avail directory for the model we want to process
avail_files = os.listdir(f"{download_dir}avail/")

avail_file = [f for f in avail_files if model_select in f][0]
print(avail_file)

#%%
ds = xr.open_dataset(f"{download_dir}avail/{avail_file}", engine="cfgrib")
lats = ds.latitude.values.flatten()
lons = ds.longitude.values.flatten()

#%%
# create geodataframe for grid points
gdf = gpd.GeoDataFrame(
    {"lat": lats, "lon": lons},
    geometry=gpd.points_from_xy(lons, lats),
    crs="EPSG:4326",
)

#%%
out_csv = f"grid_{model_select}_info.csv"
gdf.to_csv(f"{save_dir}/{out_csv}", index=False)
print(f"Grid information saved to {save_dir}/{out_csv}")
# %%

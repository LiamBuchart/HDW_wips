""" 

    Grab the yearly files for VPD and WS from the corresponding folders and create similar HDW files
    will be references to make climatoligcal means

    Liam.Buchart@NRcan-RNcan.gc.ca
    May 14, 2026

"""
#%%
from datetime import date

from context import clim_dir

import os
import xarray as xr
import numpy as np
import pandas as pd
import metpy.calc as mpcalc

from scipy.spatial import cKDTree as KDTree
from metpy.units import units

vpd_dir = clim_dir + "./VPD/"
ws_dir = clim_dir + "./WS/"

print(ws_dir)

#%%
# list and sort files in each of these directories - make pairs by year
vpd_files = os.listdir(vpd_dir)
vpd_files = sorted([file for file in vpd_files if ".nc" in file])

ws_files = os.listdir(ws_dir)
ws_files = sorted([file for file in ws_files if ".nc" in file])

print(vpd_files)
print(ws_files)

# %%
ws_file = ws_files[0]
ws_year = xr.open_dataset(f"{ws_dir}{ws_file}", engine="netcdf4")

print(ws_year)

# %%
def load_coords(dataset):
    # extract longitude and latitude from the dataset
    longitude = dataset["longitude"].values
    latitude = dataset["latitude"].values

    lat1 = latitude.flatten()
    lon1 = longitude.flatten()

    # meshgrid the lat and lon to get the coordinates for each point in the grid
    lat, lon = np.meshgrid(lat1, lon1)

    # re-flatten the lat and lon arrays to get a list of coordinates for each point in the grid
    lon = lon.flatten()
    lat = lat.flatten()

    # return the coloacted points as lat lon points in a list
    points = list(zip(lat, lon))

    return points

def build_kdtree(points):
    """
    Build a KDTree from latitude and longitude arrays.
    points: zipped list of (lat, lon) coordinates
    """
    return KDTree(points)

def find_nearest_point(kdtree, query_lat, query_lon, points):
    """
    Find the nearest point in the KDTree to the given query coordinates.
    """
    #query_rad = np.deg2rad([query_lat, query_lon])
    # stack the lat and lon into a 2D array for the query point
    query_points = np.column_stack((lat, lon))
    print("Query Points Shape: ", np.shape(query_points))


    dist, idx = kdtree.query([query_lat, query_lon], k=1)
    print(dist, idx)
    return points[idx][0], points[idx][1], dist, idx

def extract_daily_values(dataset, qlat, qlon):
    """
    Extract daily values from the dataset at the given index.
    """
    daily_values = []
    # time is the 0th index
    #for ii in range(len(dataset['date'])):
    #    daily_array = dataset['ws'][ii, :, :].flatten()

        # now get the index for the point of interest and extract the value
    #    daily_value = daily_array[idx]
    #    daily_values.append(daily_value)
    # Select value at specific lat/lon
    value = dataset.sel(lat=qlat, lon=qlon, method="nearest")
    print(value)

    return daily_values

#%%
# convert the source dates to numeric timestamps
ws_dates = pd.to_datetime(ws_year["date"].values)
print(ws_dates)

#%%
# carry out the KDTree interpolation on a yearly file
# coordinates
qlat = 56.67
qlon = -111.69

all_points = load_coords(ws_year)
# build the KDTree 
kdtree = build_kdtree(all_points)
# carry out the search
lat, lon, dist, idx = find_nearest_point(kdtree, qlat, qlon, all_points)
print(f"Nearest point to {qlat} {qlon} is at ({lat}, {lon}) with distance {dist} and index {idx}")

#%%
# get the values
daily_ws_values = extract_daily_values(ws_year, qlat, qlon)
print(daily_ws_values)


# %%

""" 

    Grab the yearly files for VPD and WS from the corresponding folders and create similar HDW files
    will be references to make climatoligcal means

    Liam.Buchart@NRcan-RNcan.gc.ca
    May 14, 2026

"""
#%%
from context import clim_dir
from plot_functions import set_plot, percentile_colormap

import os
import sys, importlib

import xarray as xr
import numpy as np
import pandas as pd
import metpy.calc as mpcalc
import matplotlib.pyplot as plt

from datetime import date
from scipy.spatial import cKDTree as KDTree
from metpy.units import units

from context import forecast_dir, clim_dir

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
# single dataset
ws_file = ws_files[0]
ws_year = xr.open_dataset(f"{ws_dir}{ws_file}", engine="netcdf4")
vpd_year = xr.open_dataset(f"{vpd_dir}{vpd_files[0]}", engine="netcdf4")

# %%
# functions
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

def find_nearest_point(kdtree, query_lat, query_lon, query_points):
    """
    Find the nearest point in the KDTree to the given query coordinates.
    """
    print("Query Points Shape: ", np.shape(query_points))
    dist, idx = kdtree.query([query_lat, query_lon], k=1)
    print(dist, idx)

    return query_points[idx][0], query_points[idx][1], dist, idx

def extract_daily_values(dataset, qlat, qlon):
    """
    Extract daily values from the dataset at the given index.
    """
    value = dataset.sel(latitude=qlat, 
                        longitude=qlon, 
                        method="nearest")
    #print(value)

    return value

#%%
# convert the source dates to numeric timestamps
ws_dates = pd.to_datetime(ws_year["date"].values)
print(ws_dates)

# convert to day of year
ws_doy = ws_dates.dayofyear
print(ws_doy)

#%%
# carry out the KDTree interpolation on a yearly file
# coordinates
qlat = 53.01
qlon = -106.26

#%%
# initialize a dataframe to hold the values and dates
ws_df = pd.DataFrame(columns=["year_day"])
ws_df["year_day"] = ws_doy
vpd_df = pd.DataFrame(columns=["year_day"])
vpd_df["year_day"] = ws_doy

#%%
all_points = load_coords(ws_year)
# build the KDTree 
kdtree = build_kdtree(all_points)
# carry out the search
lat, lon, dist, idx = find_nearest_point(kdtree, qlat, qlon, all_points)

for file in ws_files:
    print(file)
    ws_year = xr.open_dataset(f"{ws_dir}{file}", engine="netcdf4")

    # get the year from the file name
    year = file.split("_")[2].split(".")[0]
    print(year)

    # grab the point data from each file
    daily_ws_values = extract_daily_values(ws_year, lat, lon)

    ws_df[year] = daily_ws_values["ws"].values

    # plot vlaues and dates
    plt.plot(ws_doy, daily_ws_values["ws"].values)
    plt.xlabel("Date")
    plt.ylabel("Wind Speed (m/s)")
    plt.title("Daily Wind Speed at Nearest Point")

#%%
for file in vpd_files:
    print(file)
    vpd_year = xr.open_dataset(f"{vpd_dir}{file}", engine="netcdf4")

    # get the year from the file name
    year = file.split("_")[2].split(".")[0]
    print(year)

    # grab the point data from each file
    daily_vpd_values = extract_daily_values(vpd_year, lat, lon)

    vpd_df[year] = (daily_vpd_values["vpd"].values * 10)  # convert to hPa

    # plot vlaues and dates
    plt.plot(ws_doy, daily_vpd_values["vpd"].values * 10)
    plt.xlabel("Date")
    plt.ylabel("Vapor Pressure Deficit (hPa)")
    plt.title("Daily Vapor Pressure Deficit at Nearest Point")

#%%
print(ws_df)
print(vpd_df)

# %%
# mulitply the two dataframes together to get the HDW values
hdw_df = ws_df.copy()
hdw_df[ws_df.columns[1:]] = ws_df[ws_df.columns[1:]].values * vpd_df[vpd_df.columns[1:]].values
print(hdw_df)

#%%
# plot each year of the HDW values
for column in hdw_df.columns[1:]:
    plt.plot(hdw_df["year_day"], hdw_df[column], label=column)
plt.xlabel("Date")
plt.ylabel("Hot Dry Windy []")
plt.title("Hot Dry Windy at Nearest Point")
plt.legend()
plt.show()

# %%
# pivot the dataframe to have year as index and year_day as columns
hdw_pivot = hdw_df.melt(id_vars=["year_day"], var_name="year", value_name="hdw")
hdw_pivot = hdw_pivot.pivot(index="year", columns="year_day", values="hdw")
print(hdw_pivot)

#%%
# get percentiles each column (day of year) and add to a new dataframe
percentiles_df = pd.DataFrame(columns=hdw_pivot.columns)
for column in hdw_pivot.columns:
    percentiles_df[column] = np.percentile(hdw_pivot[column].values, [25, 50, 75, 90, 95])

print(percentiles_df)

#%%
percentiles = pd.DataFrame(columns=hdw_pivot.columns)

p = np.percentile(hdw_pivot[hdw_pivot.columns[0]].values, [25, 50, 75, 90, 95])  # or use quantile
percentiles[hdw_pivot.columns[0]] = p

for col in hdw_pivot.columns.values[1:-1]:  # skip the first and last two columns to avoid edge cases
    start = col-1 if col-1 in hdw_pivot.columns else col
    end = col+1 if col+1 in hdw_pivot.columns else col
    #print(f"Calculating percentiles for columns: {start}, {col}, {end}")
    dcols = np.arange(start, end+1)

    window_data = hdw_pivot.loc[:, dcols].values.flatten()  # get values from adjacent columns
    #print(f"Window data shape for column {col}: {window_data.shape}")
    p_values = np.percentile(window_data, [25, 50, 75, 90, 95])
    #print(p_values)  # calculate percentile for the window
    
    percentiles[col] = list(p_values)

p = np.percentile(hdw_pivot[hdw_pivot.columns[-1]].values, [25, 50, 75, 90, 95])  # or use quantile
percentiles[hdw_pivot.columns[-1]] = p

percentiles.index = [25, 50, 75, 90, 95]
print(percentiles)

# %%
# get todays date in yyyy-mm-dd format
today = date.today()
start_day = today.strftime("%Y-%m-%d")

#%%
importlib.reload(sys.modules["plot_functions"])
from plot_functions import set_plot, percentile_colormap

#%%
cmap = percentile_colormap(percentiles.index)
pfig, fax = set_plot(percentiles, start_day, qlat, qlon)

# %%
# test - open the forecast output
fcst = pd.read_csv(f"{forecast_dir}OUTPUT/hdw_forecast.csv")
print(fcst)

#%%
# plot forecast points using real datetimes on the x-axis
fcst['rep_datetime'] = pd.to_datetime(fcst['rep_date'])
fcst = fcst.sort_values('rep_datetime')

# plot all forecast points (matplotlib will handle clipping if outside x-limits)
fax.plot(fcst["rep_datetime"], fcst['HDW'], c='k', marker='o', zorder=5, label="RDPS Prog Tephi Forecast")

# add to legend
fax.legend(loc='upper left')

# save/show
pfig.savefig(f"{forecast_dir}FIGURES/{start_day}_hdw_forecast_lat={qlat}_lon={qlon}_plot.png")
plt.show()

# %%

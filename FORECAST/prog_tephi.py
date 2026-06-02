""" 

    Caculate the HDW based on prog tephi data stored on the local database
    Foreast extends for the duration of the HRDPS model

    Daily HWD corresponds to the 12-03UTC maximum value for east of Saskatchewan
    and 15-06 UTC maximum value for west of Saskatchewan 
    All forecasts are based on 3-hourly model output

    Liam.Bucart@NRCan-RNCan.gc.ca
    May 27, 2026

"""
#%%
import psycopg2
import paramiko
import json
import csv
import sshtunnel

from metpy.units import units
from sshtunnel import SSHTunnelForwarder
from datetime import datetime, timedelta

import metpy.calc as mpcalc
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

from prog_tephi_query import set_query, db_query

#%%
# get todays date can convert to yyyy-mm-dd format
today = datetime.now().strftime("%Y-%m-%d")
# end date is 48 hours later
end_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d") 

today = f"{today} 12:00:00"  # add time to the date for the query
end_date = f"{end_date} 12:00:00"  # add time to the date for the query
print(f"Querying prog tephi data from {today} to {end_date}")

#%%
# we already process and clean the EC prog tephi data 
# so will put that data into this script to be processed and interpolated using idw
query = set_query(today, end_date)
df = db_query(query)

# %%
# now load the csv
df = pd.read_csv("vprof_query_output.csv")
print(df)

# %%
# create a column with the vapour pressure deficit (VPD) using the formula VPD = SVP - VP
# where SVP is the saturation vapour pressure and AVP is the vapour pressure
# leverage metpy for calculations
# mixing ratio
df["mixing_ratio"] = mpcalc.mixing_ratio_from_relative_humidity(df["pres"].to_numpy() * units("hPa"),
                                                                df["temp"].to_numpy() * units("degC"),
                                                                df["rh"].to_numpy()).to("g/kg")

# saturation vapour pressure
df["SVP"] = mpcalc.saturation_vapor_pressure(df["temp"].to_numpy() * units("degC")).to("hPa")

# vapour pressure
df["VP"] = mpcalc.vapor_pressure(df["pres"].to_numpy() * units("hPa"),
                                 df["mixing_ratio"].to_numpy() * units("g/kg")).to("hPa")

# finally the vapour pressure deficit
df["VPD"] = df["SVP"] - df["VP"]

# %%
# get unique times and wmo values from the dataframe
unique_times = df["rep_date"].unique()
unique_wmos = df["wmo"].unique()

print(f"Unique times: {unique_times}",
      f"\nUnique wmos: {len(unique_wmos)}")

#%%
# create a new dataframe to store the HDW values for each time and wmo
hdw_df = pd.DataFrame(columns=["rep_date", "wmo", "lat", "lon", "VPD", "WS", "HDW"])

# nested loop to extract the weather variables for each unqiue wmo and time
for station in unique_wmos:
    for time in unique_times:
        # subset the dataframe for the current station and time
        subset = df[(df["wmo"] == station) & (df["rep_date"] == time)]

        # remove rows with missing values
        subset = subset.dropna()

        # also remove any rows with negative values for column "z"
        subset = subset[subset["z"] >= 0]

        # now just want data within 500m of the surface, so remove any rows with "z" greater than z_min+500
        subset = subset[subset["z"] <= (subset["z"].min() + 500)]

        if subset.empty:
            continue

        # HDW = max(VPD) * max(WS)
        max_vpd = subset["VPD"].max()
        max_ws = subset["ws"].max()

        # calculate the HDW for the current station and time
        hdw = max_vpd * max_ws

        # addd the result to the HDW dataframe
        info = {
            "rep_date": time, 
            "wmo": station, 
            "VPD": max_vpd, 
            "WS": max_ws, 
            "lat": subset["lat"].iloc[0], 
            "lon": subset["lon"].iloc[0],
            "HDW": hdw
        }

        hdw_df.loc[len(hdw_df)] = info

print(hdw_df)

# save the dataframe to a csv file
hdw_df.to_csv("hwd_vprof_query_output.csv", index=False)

# %%
# interpolte the HDW values using IDW to get a spatial map of the HDW values for each time step
# use geopandas to help
q_lat = 53.00  # example latitude for the point of interest
q_lon = -103.00  # example longitude for the point of interest

# store the results in a new dataframe
idw_hdw_df = pd.DataFrame(columns=["rep_date", "HDW"])

# interpolate the HDW values for each time step
for time in unique_times:
# interpolate for each timestep
    subset = hdw_df[hdw_df["rep_date"] == time]

    # create a geodataframe from the subset
    gdf = gpd.GeoDataFrame(subset, geometry=gpd.points_from_xy(subset["lon"], subset["lat"]))

    # calculate the distance from each point to the point of interest
    gdf["distance"] = gdf.geometry.distance(gpd.points_from_xy([q_lon], [q_lat])[0])

    # calculate the weights for IDW (inverse of distance)
    gdf["weight"] = 1 / gdf["distance"]

    # calculate the weighted average of the HDW values
    idw_hdw = (gdf["HDW"] * gdf["weight"]).sum() / gdf["weight"].sum()

    # add the result to the idw_hdw_df dataframe
    idw_hdw_df.loc[len(idw_hdw_df)] = {"rep_date": time, "HDW": idw_hdw}

# %%
print(idw_hdw_df)

# save to a csv file
idw_hdw_df.to_csv("./OUTPUT/hdw_forecast.csv", index=False)
# %%

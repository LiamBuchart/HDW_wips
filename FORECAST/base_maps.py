""" 

    Use the save prog tephi query to create base maps that will be used on
    the ineractive map. Also save static maps for reference

    Liam.Buchart@NRCan-RNCan.gc.ca
    May 29, 2026

"""
#%%
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from datetime import date
from shapely.geometry import Point

#%%
# load the csv
df = pd.read_csv("hwd_vprof_query_output.csv")
print(df)
print(df.columns)

unique_times = df["rep_date"].unique()

# get todays date can convert to yyyy-mm-dd format
today = date.today().strftime("%Y-%m-%d")

# define major Canadian cities to label on the map
canadian_cities = [
    ("Toronto", -79.3832, 43.6532),
    ("Montreal", -73.5673, 45.5017),
    ("Vancouver", -123.1207, 49.2827),
    ("Calgary", -114.0719, 51.0447),
    ("Edmonton", -113.4909, 53.5461),
    ("Ottawa", -75.6972, 45.4215),
    ("Quebec City", -71.2080, 46.8139),
    ("Winnipeg", -97.1384, 49.8951),
    ("Halifax", -63.5752, 44.6488),
    ("Victoria", -123.3656, 48.4284),
    ("Regina", -104.6189, 50.4452),
    ("Saskatoon", -106.6700, 52.1332),
    ("Yellowknife", -114.3718, 62.4540),
    ("Whitehorse", -135.0568, 60.7212),
]

province_feature = cfeature.NaturalEarthFeature(
    category="cultural",
    name="admin_1_states_provinces",
    scale="50m",
    facecolor="none",
)

#%%
for time in unique_times:
    df_time = df[df["rep_date"] == time]
    print(f"Processing data for time: {time}")
    
    # create a geometry column for geopandas
    geometry = [Point(xy) for xy in zip(df_time["lon"], df_time["lat"])]
    gdf = gpd.GeoDataFrame(df_time, geometry=geometry, crs="EPSG:4326")

    fig = plt.figure(figsize=(14, 11))
    ax = plt.axes(projection=ccrs.LambertConformal(central_longitude=-95, central_latitude=60))

    # clip the map domain to the data extent and the Arctic Circle in the north
    city_lons = [lon for _, lon, _ in canadian_cities]
    city_lats = [lat for _, _, lat in canadian_cities]
    lon_min = min(gdf["lon"].min(), min(city_lons)) - 2
    lon_max = max(gdf["lon"].max(), max(city_lons)) + 2
    lat_min = min(gdf["lat"].min(), min(city_lats)) - 2
    lat_max = 66.5622  # Arctic Circle
    ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

    ax.add_feature(cfeature.OCEAN, facecolor="lightblue", zorder=0)
    ax.add_feature(cfeature.LAND, facecolor="whitesmoke", zorder=1)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, zorder=2)
    ax.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.6, zorder=2)
    ax.add_feature(province_feature, edgecolor="gray", linewidth=0.7, zorder=3)

    if len(gdf) >= 3:
        cont = ax.tricontourf(
            gdf["lon"],
            gdf["lat"],
            gdf["HDW"],
            levels=12,
            cmap="coolwarm",
            alpha=0.8,
            transform=ccrs.PlateCarree(),
            zorder=4,
        )
        cb = fig.colorbar(cont, ax=ax, orientation="vertical", pad=0.02, aspect=30)
        cb.set_label("HDW")
    else:
        ax.scatter(
            gdf["lon"],
            gdf["lat"],
            c=gdf["HDW"],
            cmap="coolwarm",
            s=50,
            edgecolor="black",
            transform=ccrs.PlateCarree(),
            zorder=5,
        )

    ax.scatter(
        gdf["lon"],
        gdf["lat"],
        color="black",
        s=20,
        transform=ccrs.PlateCarree(),
        zorder=6,
    )

    city_lons = [lon for _, lon, _ in canadian_cities]
    city_lats = [lat for _, _, lat in canadian_cities]
    ax.scatter(
        city_lons,
        city_lats,
        color="darkred",
        s=40,
        marker="^",
        transform=ccrs.PlateCarree(),
        zorder=7,
        label="Cities",
    )

    for name, lon, lat in canadian_cities:
        ax.text(
            lon + 0.8,
            lat + 0.4,
            name,
            transform=ccrs.PlateCarree(),
            fontsize=8,
            color="black",
            zorder=8,
            bbox=dict(facecolor="white", alpha=0.6, edgecolor="none", pad=1),
        )

    ax.set_title(f"HDW over Canada at {time}", fontsize=16)
    ax.gridlines(draw_labels=False, linewidth=0.3, color="gray", alpha=0.5, linestyle="--")

    # add _ to space in the time string for the filename
    time_str = time.replace(" ", "_").replace(":", "-")

    plt.savefig(f"./MAPS/{today}_hdw_contour_canada_{time_str}.png", bbox_inches="tight", dpi=150)
    plt.close()
# %%

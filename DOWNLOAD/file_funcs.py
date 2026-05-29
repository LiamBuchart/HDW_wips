# required functions to get everything that we need
import subprocess
import json
from datetime import datetime, timedelta
import cfgrib
import os
import xarray as xr
import requests
import shutil
import numpy as np

import pandas as pd
def set_filenames(model, date, horizon):
    """
        Set the filenames based on the model, run, year, month, day, and forecast length.
        Paramters are selected in other .py scripts - funciton also loads specific model variables from JSON files.

        model: str - the model name (e.g., 'rdps', 'hrdps')
        date: str - the date in the format 'YYYY-MM-DD'
        horizon: str - hhh (e.g., '000' for 0h forecast, '003' for 3h forecast, etc.)
        Returns a DataFrame with the full path, extension, and file name for variable.

        The dry lightning forecast only uses 12UTC analysis output to run
        so forecast length is inherenetly 0. 
    """    
    year = int(date[0:4])
    month = int(date[5:7])
    day = int(date[8:10])

    print(f"Selected Model: {model}")
    print(f"Selected Model Run: 12Z")
    print(f"Selected Date: {year}-{month}-{day}--12Z")

    file_list = pd.DataFrame(columns=['full_path', 'extension', 'file', 'variable', 'datetime'])
    # Create the filename based on the selections
    if str(model) == 'rdps':
        # load the rdps_vars.json file
        with open('rdps_vars.json', 'r') as f:
            model_vars = json.load(f)
    elif str(model) == 'hrdps':
        # load the hrdps_vars.json file
        with open('hrdps_vars.json', 'r') as f:
            model_vars = json.load(f)

    model_initialization = 12  # 12 UTC

    # full datamart extension - for 0h 12 UTC forecast
    extension = f"https://dd.weather.gc.ca/today/model_{model}/{model_vars['configuration']['resolution']}/12/{horizon}/"

    for ii in range(len(model_vars['wx_vars'])):  #model_vars['wx_vars'].values():
            var = list(model_vars['wx_vars'].values())[ii]
            quick_var = list(model_vars['grib_vars'].values())[ii]

            file = f"{year}{month:02d}{day:02d}T12Z_MSC_{model.upper()}_{var}_RLatLon{model_vars['configuration']['grid']}_PT{horizon}H.grib2"

            # get a datetime variable and add it to the dataframe - this moves it to the local time set by the user
            timestamp = datetime(int(year), int(month), int(day), 12)

            print(timestamp, file)

            # populate the file_list DataFrame
            new_row = {
                'full_path': extension + file,
                'extension': extension,
                'file': file,
                'variable': quick_var,
                'datetime': timestamp
            }
            file_list.loc[len(file_list)] = new_row

    return file_list
""" 

    Functions to quickly make the plots

    Liam.Buchart@NRcan-RNcan.gc.ca
    May 22, 2026

"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

def percentile_colormap(percentiles):
    # create a colormap for the percentiles
    cmap = plt.get_cmap("Reds")
    colors = cmap(np.linspace(0, 1, len(percentiles)+2))[1:] # get the colors for the percentiles, excluding the last two (for above 95th percentile)

    return colors

def set_plot(df, start_date, qlat, qlon):
    # df: output from HWD_clim
    # start_date: string in the format "YYYY-MM-DD"
    # qlat and qlon: latitude and longitude of the point of interest (for Title)
    start_dt = pd.to_datetime(start_date)
    # create a small window around start_date (2 days before and after)
    plot_dates = pd.date_range(start_dt - pd.Timedelta(days=2),
                               start_dt + pd.Timedelta(days=2), freq="D")
    # map the plot dates to day-of-year to index df columns
    plot_doys = plot_dates.dayofyear

    fig, ax = plt.subplots(figsize=(10, 6))
    # plot percentiles using datetime x-axis
    for percentile in df.index:
        ax.plot(plot_dates, df.loc[percentile, plot_doys], color="Grey")

    # fill between percentiles with colormap
    colors = percentile_colormap(df.index)
    for i in range(len(df.index) - 1):
        ax.fill_between(plot_dates,
                        df.loc[df.index[i], plot_doys],
                        df.loc[df.index[i + 1], plot_doys],
                        color=colors[i], alpha=0.5,
                        label=f"{df.index[i]}-{df.index[i + 1]} Percentile")

    # Get current y-limits (before filling)
    ymin, ymax = ax.get_ylim()
    y = df.loc[95, plot_doys]
    ax.fill_between(plot_dates, y, ymax, where=(y < ymax),
                    color=colors[-1], alpha=0.5, label="Above 95th Percentile")

    # vertical dashed line on start_date
    ax.axvline(x=start_dt, color="Black", linestyle="--", label="Start Date")

    # format x-axis as dates
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()

    ax.set_xlim(plot_dates[0], plot_dates[-1])
    ax.set_ylim(ymin-1, ymax)

    ax.set_xlabel("Datetime UTC", fontsize=15)
    ax.set_ylabel("Hot Dry Windy []", fontsize=15)
    ax.set_title(f"HDW Percentiles at Nearest Point ({qlat}, {qlon})", fontsize=16)
    ax.legend(loc="upper left")

    fig.tight_layout()

    return fig, ax
        


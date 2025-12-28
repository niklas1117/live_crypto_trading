# info based filters
import pandas as pd


def return_filter(info, ax, **kwargs):

    """
    # 1
    Filter for period return 
    """

    min_return = kwargs.get("min_return")
    ret = float(info['priceChangePercent'])

    if ax: 
        pd.Series({'Return': ret}).plot.barh(ax=ax, color='grey', grid=True)
        ax.axvline(x=min_return, color='blue', linestyle='--')
        ax.set_title(f"Return filter")
        ax.set_xlabel("Return")
        ax.set_ylabel("Time")

    return ret > min_return


def volume_filter(info, ax, **kwargs):

    """
    # 1
    Filter for period volume
    """

    min_volume = kwargs.get("min_volume")
    vol = float(info['volume'])

    if ax: 
        pd.Series({'Volume': vol}).plot.barh(ax=ax, color='grey', grid=True)
        ax.axvline(x=min_volume, color='blue', linestyle='--')
        ax.set_title(f"Volume filter")
        ax.set_xlabel("Volume")
        ax.set_ylabel("Time")

    return vol > min_volume
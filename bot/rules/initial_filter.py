# info based filters
import pandas as pd
from loguru import logger


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

    result = ret > min_return

    logger.info(f"{'✅' if result else '❌'} - Return: {ret:.2f}%")

    return result


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

    result = vol > min_volume

    logger.info(f"{'✅' if result else '❌'} - Volume: {vol/1_000_000:.2f}M")

    return result
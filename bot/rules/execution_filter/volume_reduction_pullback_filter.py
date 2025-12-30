import pandas as pd
from loguru import logger

NAME = "volume_reduction_pullback_filter"
REQUIRES = ["volume_pullback_filter_bars", "relative_volume_reduction_filter"]

def vec(df: pd.DataFrame, volume_pullback_filter_bars: int, relative_volume_reduction_filter: float):

    mean_volume = df['Volume'].rolling(volume_pullback_filter_bars).mean()

    signal = df['Volume'] < (mean_volume * relative_volume_reduction_filter)
    score =  (df['Volume'] / (mean_volume * relative_volume_reduction_filter)) - 1
    return signal, score

def event(df: pd.DataFrame, volume_pullback_filter_bars: int, relative_volume_reduction_filter: float):
    signal, score = vec(df, volume_pullback_filter_bars, relative_volume_reduction_filter)
    result = signal.iloc[-1]
    logger.info(f"{'✅' if result else '❌'} - Volume reduction: {score.iloc[-1]:.2f}")
    return result
import pandas as pd
import talib as ta
from loguru import logger

NAME = "distance_to_mean_filter"
REQUIRES = ["distance_to_mean_bars", "atr_bars", "entry_atr"]

def vec(df: pd.DataFrame, distance_to_mean_bars: int, atr_bars: int, entry_atr: float): 

    mean = df['Close'].rolling(distance_to_mean_bars).mean()
    atr = ta.ATR(df['High'], df['Low'], df['Close'], timeperiod=atr_bars)

    signal = (df['Close'] - mean) < (entry_atr * atr)
    score = (df['Close'] - mean) / (entry_atr * atr) - 1

    return signal, score

def event(df: pd.DataFrame, distance_to_mean_bars: int, atr_bars: int, entry_atr: float):
    signal, score = vec(df, distance_to_mean_bars, atr_bars, entry_atr)
    result = signal.iloc[-1]
    logger.info(f"{'✅' if result else '❌'} - Distance to mean: {score.iloc[-1]:.2f}")
    return result
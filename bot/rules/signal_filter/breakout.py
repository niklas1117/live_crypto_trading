import pandas as pd
import talib as ta
from loguru import logger

NAME = "breakout"
REQUIRES = ['breakout_bars', 'breakout_n_atr']


def vec(df: pd.DataFrame, breakout_bars: int, breakout_n_atr: int):
    high = df['High']
    cum_high = high.rolling(breakout_bars).max()
    atr = ta.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
    signal = df['Close'] > (cum_high.shift(1) + (breakout_n_atr * atr))
    score = df['Close'] / (cum_high.shift(1) + (breakout_n_atr * atr))
    return signal, score

def event(df: pd.DataFrame, breakout_bars: int, breakout_n_atr: int):
    signal, score = vec(df, breakout_bars, breakout_n_atr)
    result = signal.iloc[-1]
    logger.info(f"{'✅' if result else '❌'} - Breakout - {score.iloc[-1]:.2f} ATRs")
    return result
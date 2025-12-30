import pandas as pd
import talib as ta
from loguru import logger

NAME = "recent_atr_compression"
REQUIRES = ["atr_compression_rank_bars", "atr_compression_cutoff"]

def vec(df: pd, atr_compression_rank_bars: int, atr_compression_cutoff: float):

    atr = ta.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
    atr_compression = atr.rolling(atr_compression_rank_bars).rank(pct=True).shift(1)

    signal = atr_compression < atr_compression_cutoff
    score = atr_compression

    return signal, score

def event(df: pd, atr_compression_rank_bars: int, atr_compression_cutoff: float):
    signal, score = vec(df, atr_compression_rank_bars, atr_compression_cutoff)
    result = signal.iloc[-1]
    logger.info(f"{'✅' if result else '❌'} - ATR rank: {score.iloc[-1]:.3f}")
    return result
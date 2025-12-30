from loguru import logger
import pandas as pd

NAME = "upper_donchian_breach"
REQUIRES = ["donchian_entry_bars"]

def vec(df: pd.DataFrame, donchian_entry_bars: int):
    donchian_channel = df['High'].rolling(donchian_entry_bars).max().shift(1)
    signal = df['Close'] > donchian_channel
    score = df['Close'] / donchian_channel
    return signal, score

def event(df: pd.DataFrame, donchian_entry_bars: int):
    signal, score = vec(df, donchian_entry_bars)
    result = signal.iloc[-1]
    logger.info(f"{'✅' if result else '❌'} - Donchian Upper Entry: {score.iloc[-1]:.2f}")
    return result
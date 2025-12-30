import pandas as pd
from loguru import logger

NAME = 'volume_filter'
REQUIRES = ['min_volume']

def event(info: dict, min_volume: float):
    vol = float(info['volume'])
    result = vol > min_volume
    logger.info(f"{'✅' if result else '❌'} - Volume: {vol/1_000_000:.2f}M")
    return result
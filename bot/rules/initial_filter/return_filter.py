import pandas as pd
from loguru import logger

NAME = "return_filter"
REQUIRES = ["min_return"]

def event(info: dict, min_return: float):
    ret = float(info['priceChangePercent'])
    result = ret > min_return
    logger.info(f"{'✅' if result else '❌'} - Return: {ret:.2f}%")
    return result
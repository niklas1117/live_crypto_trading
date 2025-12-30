from loguru import logger

NAME = "volume_breakout"
REQUIRES = ['volume_quantile_bars', 'volume_quantile']

def vec(df, volume_quantile_bars, volume_quantile):
    volume = df['Volume']
    volume_quantile = volume.rolling(volume_quantile_bars).quantile(volume_quantile).shift(1)
    signal = volume > volume_quantile
    score = volume / volume_quantile

    return signal, score

def event(df, volume_quantile_bars, volume_quantile):
    signal, score = vec(df, volume_quantile_bars, volume_quantile)
    result = signal.iloc[-1]
    logger.info(f"{'✅' if result else '❌'} - Volume breakout - {score.iloc[-1]:.2f}")
    return result
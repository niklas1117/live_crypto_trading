# return based direction
import pandas as pd
import statsmodels.api as sm
from loguru import logger

NAME = "trend_regression_entry"
REQUIRES = ['regression_bars']

def event(df: pd.DataFrame, regression_bars: int):
    X = df.index.values.reshape(-1, 1)[-regression_bars:]
    y = df['Close'].values[-regression_bars:]

    model = sm.OLS(y, sm.add_constant(X)).fit()
    t = model.tvalues[1]

    result = t > 1.96
    logger.info(f"{'✅' if result else '❌'} - Price trend beta(t): {t:.3f}")
    return result
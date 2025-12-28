import statsmodels.api as sm
import talib as ta

# return based direction
def trend_regression_entry(df, ax, **kwargs):

    """
    Trend detection via linear regression of price on time
    """


    regression_bars = kwargs.get("regression_bars")

    X = df.index.values.reshape(-1, 1)[-regression_bars:]
    y = df['Close'].values[-regression_bars:]

    model = sm.OLS(y, sm.add_constant(X)).fit()
    t = model.tvalues[1]
    if ax:
        ax.plot(X, y, color='black')
        ax.set_title(f"Trend regression entry - {t=:.3f}")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.legend()

    return t > 1.96


def volume_trend_regression_entry(df, ax, **kwargs):

    """
    Volume trend detection via linear regression of volume on time
    """

    regression_bars = kwargs.get("regression_bars")

    X = df.index.values.reshape(-1, 1)[-regression_bars:]
    y = df['Volume'].values[-regression_bars:]

    model = sm.OLS(y, sm.add_constant(X)).fit()
    t = model.tvalues[1]

    if ax:
        ax.plot(X, y, color='black')
        ax.set_title(f"Volume trend regression entry - {t=:.3f}")
        ax.set_xlabel("Time")
        ax.set_ylabel("Volume")
        ax.legend()

    return t > 1.96


def volume_breakout(df, ax, **kwargs):

    """
    Volume breakout filter, [> MA], [> PrevMax]
    """

    volume_ma_bars = kwargs.get("volume_ma_bars")

    volume = df['Volume']
    volume_ma = df['Volume'].rolling(volume_ma_bars).mean()

    if ax:
        volume.plot(ax=ax, color='black', label='Volume')
        volume_ma.plot(ax=ax, color='grey', label='Volume MA')
        ax.axhline(volume.quantile(0.975), color='blue', linestyle='--', label='PrevMax')
        ax.set_title(f"Volume above MA")
        ax.set_xlabel("Time")
        ax.set_ylabel("Volume")
        ax.legend()

    return (volume.iloc[-1] > volume_ma.iloc[-1]) & (volume.iloc[-1] >= volume.quantile(0.975))


def breakout(df, ax, **kwargs):

    """
    Breakout detection via price action
    """

    breakout_bars = kwargs.get("breakout_bars")

    high = df['High']
    cum_high = high.rolling(breakout_bars).max()

    atr = ta.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)

    signal = high > (cum_high.shift(1) + atr)

    if ax: 
        high.plot(ax=ax, color='black', label='High Price')
        cum_high.shift(1).plot(ax=ax, color='grey', label='Previous High')
        (cum_high.shift(1) + atr).plot(ax=ax, color='blue', label='Previous High + ATR')
        for date in high.loc[high > (cum_high.shift(1) + atr)].index:
            ax.axvline(date, c='grey', alpha=0.3)

        ax.set_title(f"Breakout - ATRs away from high {((high - cum_high.shift(1)) / atr).iloc[-1]:.2f}")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.legend()

    return signal.iloc[-1]

def recent_atr_compression(df, ax, **kwargs):

    """
    Recent ATR compression detection
    """

    atr_compression_rank_bars = kwargs.get("atr_compression_rank_bars")
    atr_compression_cutoff = kwargs.get("atr_compression_cutoff")

    atr = ta.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
    atr_compression = atr.rolling(atr_compression_rank_bars).rank(pct=True).shift(1)

    if ax:
        atr_compression.plot(ax=ax, color='black', label='ATR Rank')
        ax.set_title(f"Recent ATR compression - {atr_compression.iloc[-1]}")
        ax.set_xlabel("Time")
        ax.set_ylabel("ATR")
        ax.set_ylim(0, 1)
        ax.legend()

    return atr_compression.iloc[-1] < atr_compression_cutoff
import pandas as pd
import talib as ta


def distance_to_mean_filter(df, price, ax, **kwargs):

    distance_to_mean_bars = kwargs.get("distance_to_mean_bars")
    atr_bars = kwargs.get("atr_bars")
    entry_atr = kwargs.get("entry_atr")

    mean = df['Close'].rolling(distance_to_mean_bars).mean()
    atr = ta.ATR(df['High'], df['Low'], df['Close'], timeperiod=atr_bars)

    mean_last = mean.iloc[-1]
    atr_last = atr.iloc[-1]

    pd.concat({
        f'mean {distance_to_mean_bars} bars': mean,
        f'Close': df['Close']
    }, axis=1).plot(ax=ax, color=['grey', 'black'], grid=True)
    ax.legend()
    ax.set_title(f"Distance to mean filter")
    ax.set_xlabel("Distance")
    ax.set_ylabel("Time")

    return (price - mean_last) < (entry_atr * atr_last)


def volume_reduction_pullback_filter(df, price, ax, **kwargs):

    volume_pullback_filter_bars = kwargs.get('volume_pullback_filter_bars')
    relative_volume_reduction_filter = kwargs.get("relative_volume_reduction_filter")


    mean_volume = df['Volume'].rolling(volume_pullback_filter_bars).mean()

    mean_volume_last = mean_volume.iloc[-1]
    volume_last = df['Volume'].iloc[-1]


    pd.concat({
        f'Mean Volume {volume_pullback_filter_bars} bars': mean_volume,
        f'Volume': df['Volume']
    }, axis=1).plot(ax=ax, color=['grey', 'black'], grid=True)

    ax.set_title(f"Volume reduction pullback filter")
    ax.set_xlabel("Volume")
    ax.set_ylabel("Time")

    return volume_last < (mean_volume_last * relative_volume_reduction_filter)


def upper_donchian_breach(df, price, ax, **kwargs):

    donchian_entry_bars = kwargs.get("donchian_entry_bars")

    donchian_channel = df['High'].rolling(donchian_entry_bars).max().shift(1)
    donchian_channel.plot(ax=ax, color='black', label='Upper Donchian Channel')
    df['Close'].plot(ax=ax, color='grey', label='Close Price')
    ax.axhline(price, color='blue', label='Price')
    ax.set_title(f"Upper Donchian Breach")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.legend()

    return (df['Close'] > donchian_channel).iloc[-1]
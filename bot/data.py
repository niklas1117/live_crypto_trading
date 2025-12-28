import os

import pandas as pd
from binance import Client
from dotenv import load_dotenv

load_dotenv() 

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

client = Client(api_key, api_secret)


def load_ohlcv(ticker, interval, start_str="2 hours ago UTC"):
    klines = client.get_historical_klines(ticker, interval, start_str)
    df = pd.DataFrame(klines, columns=
                     [
        "Open time",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Close time",
        "Quote asset volume",
        "Number of trades",
        "Taker buy base asset volume",
        "Taker buy quote asset volume",
        "Ignore."
    ])
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
    df[['Close', 'High', 'Low', 'Open', 'Volume', 'Taker buy base asset volume', 'Taker buy quote asset volume']] = df[['Close', 'High', 'Low', 'Open', 'Volume', 'Taker buy base asset volume', 'Taker buy quote asset volume']].astype(float)
    # only get closed bars
    while df['Close time'].iloc[-1] > pd.to_datetime('now', utc=True).to_datetime64():
        df = df.iloc[:-1].copy()
    return df.set_index('Close time')

def create_features(df):
    return pd.Series(
        {
            'ret_1h': df.iloc[0]['Close'] / df.iloc[0]['Open'] - 1,
            'vol_1h': df['Volume'].sum(),
            'ma_1h': df['Close'].mean(),
            'last_price': df.iloc[-1]['Close']
        }
    )

def get_ticker_info(ticker, window_size: str = "1h"):
    ser = pd.Series(client._request_api("get", "ticker", signed=False, data={'symbol': ticker, "windowSize": window_size}, version="v3"))
    ser = ser.convert_dtypes()
    return ser 


def get_position(ticker):
    return float([k for k in client.get_margin_account()['userAssets'] if k['asset'] == ticker][0]['free'])

def get_usdt_balance():
    return get_position('USDT')

def check_order_status(ticker, order_id):
    order = client.get_margin_order(symbol=ticker, orderId=order_id)
    return order['status']

def get_precision(ticker):
    return [a for a in client.get_exchange_info()['symbols'] if a['symbol']==ticker][0]['baseAssetPrecision']

from binance import Client
from binance.enums import *

from dotenv import load_dotenv
import os

import matplotlib.pyplot as plt
from tqdm import tqdm
from binance.enums import *
from decimal import Decimal

import pandas as pd
import datetime as dt
import time
import math
import statsmodels.api as sm
import numpy as np

import talib as ta

from IPython.display import clear_output, display

load_dotenv()  # loads the variables from .env

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


def trade_live(
        tickers: list[str], 
        info_based_filters: list,
        return_based_direction_filters: list,
        return_based_entry_filters: list,
        exit_filters: list,
        show_stages: int,
        **kwargs
    ):

    max_n_filters = max(len(filter) for filter in [
        info_based_filters,
        return_based_direction_filters,
        return_based_entry_filters,
        exit_filters
    ])

    tickers_pass_2 = tickers.copy()
    n = 1
    while True:
        print(f"Iteration {n}")
        n += 1


        tickers_to_loop = [t for t in tickers if t in tickers_pass_2]
        tickers_pass_2 = []

        for ticker in tickers_to_loop:

            fig, axs = plt.subplots(4, max_n_filters, figsize=(6*max_n_filters, 10))
            fig.suptitle(f"Investigating signals for {ticker}")

            initial_filter_timeframe = kwargs.get('initial_filter_timeframe')
            info = get_ticker_info(ticker, initial_filter_timeframe)
            results = [f(info, axs[0, a], **kwargs) for a, f in enumerate(info_based_filters)]

            if all(results):

                df_direction = load_ohlcv(ticker, kwargs.get('signal_filter_timeframe'), "5 days ago UTC")
                results = [f(df_direction, axs[1, a], **kwargs) for a, f in enumerate(return_based_direction_filters)]
                axs[1,0].set_title("Filter passed - " + axs[1,0].get_title())

                if all(results):
                    tickers_pass_2.append(ticker)

                    price = float(client.get_symbol_ticker(symbol=ticker)['price'])
                    df_entry = load_ohlcv(ticker, kwargs.get('execution_filter_timeframe'), "2 hours ago UTC")
                    results = [f(df_entry, price, axs[2, a], **kwargs) for a, f in enumerate(return_based_entry_filters)]
                    axs[2,0].set_title("Positive direction detected - " + axs[2,0].get_title())

                    # clear_output(wait=True)
                    # fig.tight_layout()
                    # display(fig)

                    if all(results):

                        axs[3,0].set_title("Buying - " + axs[3,0].get_title())

                        last_atr = ta.ATR(df_entry['High'], df_entry['Low'], df_entry['Close'], timeperiod=kwargs.get('atr_bars')).iloc[-1]

                        cash = get_usdt_balance()
                        quantity = cash / price
                        quantity = math.floor(quantity * kwargs.get('max_leverage'))
                        if quantity == 0:
                            print(f"Insufficient funds to buy {ticker}")
                            continue
                        order = client.create_margin_order(
                                symbol=ticker,
                                side=SIDE_BUY,
                                type=ORDER_TYPE_MARKET,
                                quantity=quantity,
                            )
                        order_id = order['orderId']
                        info = client.get_symbol_info(ticker)
                        buy_price = float(client.get_margin_trades(symbol=ticker, orderId=order_id)[0]['price'])
                        total_outlay = quantity * buy_price
                        print(f'bought {quantity} of {ticker} at {buy_price} for {total_outlay}')

                        while check_order_status(ticker, order_id) != 'FILLED': 
                            print('waiting for order fill')
                            time.sleep(1)
                        time.sleep(1)

                        quantity_close = get_position(ticker.split('USDT')[0])
                        step = Decimal(info['filters'][1]['stepSize'])
                        qty_dec = Decimal(str(quantity_close))
                        quantity_close = float((qty_dec // step) * step)
                        print(f"To close we need to sell {quantity_close}.")

                        cummmax = buy_price
                        last_price = buy_price
                        price_stable_days = 0

                        cummaxs = []
                        trailing_losses = []
                        prices = []
                        potential_profits = []

                        n_10_secs = 0
                        loss_multiplier = 1

                        while True:
                            n_10_secs += 1
                            price = float(client.get_symbol_ticker(symbol=ticker)['price'])
                            # if n_10_secs % half_loss_after == 0:
                            #     loss_multiplier /= 2

                            cummmax = max(cummmax, price)
                            trailing_loss = cummmax - (last_atr * kwargs.get('min_loss_atr') * loss_multiplier)
                            potential_profit = (price * quantity_close) - total_outlay

                            cummaxs.append(cummmax)
                            trailing_losses.append(trailing_loss)
                            prices.append(price)
                            potential_profits.append(potential_profit)

                            # clear_output(wait=True)

                            # clear axes before re-plotting
                            axs[-1, 0].clear()
                            axs[-1, 1].clear()

                            # top: price, cummax, trailing loss
                            axs[-1, 0].plot(prices, label='Price', color='C0')
                            axs[-1, 0].plot(cummaxs, label='CumMax', color='C1')
                            axs[-1, 0].plot(trailing_losses, label='Trailing Loss', color='C2')
                            axs[-1, 0].set_title(f"{ticker} - Price / CumMax / Trailing Loss")
                            axs[-1, 0].legend()
                            axs[-1, 0].grid(True)

                            # bottom: potential profit (separate scale)
                            axs[-1, 1].plot(potential_profits, label='Potential Profit', color='C3')
                            axs[-1, 1].axhline(0, color='k', linewidth=0.6)
                            axs[-1, 1].set_title(f"{ticker} - Potential Profit")
                            axs[-1, 1].legend()
                            axs[-1, 1].grid(True)

                            if price < trailing_loss:
                                print("Trailing loss hit, selling.")
                                break

                            if price_stable_days > 10 and potential_profit > 0:
                                print(f"Price has been stable, potential profit reached: {potential_profit}")
                                break

                            if price == last_price:
                                price_stable_days += 1
                            else:
                                price_stable_days = 0
                            last_price = price

                            fig.tight_layout()
                            display(fig) if show_stages >= 1 else None
                            time.sleep(10)


                        order = client.create_margin_order(
                            symbol=ticker,
                            side=SIDE_SELL,
                            type=ORDER_TYPE_MARKET,
                            quantity=quantity_close,
                        )
                    else: 
                        fig.tight_layout()
                        plt.show() if show_stages >= 2 else plt.close()

                else: 
                    fig.tight_layout()
                    plt.show() if show_stages >= 3 else plt.close()

            else: 
                fig.tight_layout()
                plt.show() if show_stages >= 4 else plt.close()

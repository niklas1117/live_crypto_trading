import math
import sys
import time
from decimal import Decimal

from loguru import logger

import matplotlib.pyplot as plt
import talib as ta
from binance.enums import *
from IPython.display import display

from bot.config.utils import read_tickers, write_tickers, read_config
from bot.data import (check_order_status, client, get_position,
                      get_ticker_info, get_usdt_balance, load_ohlcv)

logger.remove()
logger.add("bot/trade_live.log", rotation="10 MB", format="{time:HH:mm:ss} | {level} | {message}")
logger.add(sys.stderr, format="{time:HH:mm:ss} | {level} | {message}")

def evaluate_signal_filters_once(
    tickers, 
    info_based_filters, 
    return_based_direction_filters,
    **kwargs
):  
    
    passing_tickers = []
    
    for ticker in tickers:

        # Initial Filters

        logger.info(f"{ticker} - initial filters")

        initial_filter_timeframe = kwargs.get('initial_filter_timeframe')
        info = get_ticker_info(ticker, initial_filter_timeframe)
        results = [f(info, None, **kwargs) for a, f in enumerate(info_based_filters)]

        if all(results):

            logger.info("✅")
            logger.info(f"{ticker} - signal filters")

            # Signal Filters

            df_direction = load_ohlcv(ticker, kwargs.get('signal_filter_timeframe'), "5 days ago UTC")
            results = [f(df_direction, None, **kwargs) for a, f in enumerate(return_based_direction_filters)]

            if all(results):
                logger.info("✅")
                passing_tickers.append(ticker)
            else: 
                logger.info("❌")
        else: 
            logger.info("❌")
    return passing_tickers

def run_live_signal_filters(
    tickers: list[str], 
    info_based_filters: list,
    return_based_direction_filters: list,
    schedule_minutes: list[int],
    rerun_once_first: bool=False # run once and then schedule
):
    import schedule

    def job():
        logger.info("Running live signal filters...")
        passing_tickers = evaluate_signal_filters_once(
            tickers, 
            info_based_filters, 
            return_based_direction_filters,
            **read_config()
        )
        write_tickers(passing_tickers, filename='live_signal_tickers.txt')
        logger.info(f"Tickers passing filters: {passing_tickers}")

    for minute in schedule_minutes:
        schedule.every().hour.at(f":{minute:02d}").do(job)

    if rerun_once_first:
        logger.info("Running live signal filters once before scheduling...")
        job()

    logger.info("Starting scheduled live signal filters...")
    while True:
        schedule.run_pending()
        time.sleep(1)

def evaluate_entry_filters_and_execute_one_trade(
    tickers: list[str], 
    return_based_entry_filters: list,
    exit_filters: list,
    **kwargs
):  
    logger.info("Evaluating entry filters and executing trades...")
    logger.info(f"Tickers to evaluate: {tickers}")

    for ticker in tickers:

        logger.info(f"{ticker} - entry filters")

        price = float(client.get_symbol_ticker(symbol=ticker)['price'])
        df_entry = load_ohlcv(ticker, kwargs.get('execution_filter_timeframe'), "2 hours ago UTC")
        results = [f(df_entry, price, None, **kwargs) for a, f in enumerate(return_based_entry_filters)]

        if all(results):

            logger.info("✅")
            logger.info(f"{ticker} - executing trade")

            try: 

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
                while check_order_status(ticker, order_id) != 'FILLED': time.sleep(1)
                time.sleep(1)

                logger.info(f'bought {quantity} of {ticker} at {buy_price} for {total_outlay}')
                quantity_close = get_position(ticker.split('USDT')[0])
                step = Decimal(info['filters'][1]['stepSize'])
                qty_dec = Decimal(str(quantity_close))
                quantity_close = float((qty_dec // step) * step)

                logger.info(f"To close we need to sell {quantity_close}.")

                cummmax = buy_price
                last_price = buy_price
                price_stable_days = 0

                cummaxs = []
                trailing_losses = []
                prices = []
                potential_profits = []

                while True:
                    try: 
                        price = float(client.get_symbol_ticker(symbol=ticker)['price'])

                        cummmax = max(cummmax, price)
                        trailing_loss = cummmax - (last_atr * kwargs.get('min_loss_atr'))
                        potential_profit = (price * quantity_close) - total_outlay

                        cummaxs.append(cummmax), trailing_losses.append(trailing_loss), prices.append(price), potential_profits.append(potential_profit)
                        logger.info(f"Current price: {price}, Trailing loss: {trailing_loss}, Potential profit: {potential_profit}")

                        if price < trailing_loss:
                            logger.info("Trailing loss hit, selling.")
                            break

                        if price_stable_days > 10 and potential_profit > 0:
                            logger.info(f"Price has been stable, potential profit reached: {potential_profit}")
                            break

                        price_stable_days += 1 if price == last_price else 0
                        last_price = price

                    except Exception as e:
                        logger.error(f"Error during monitoring price for {ticker}: {e}, closing position.")
                        break

                order = client.create_margin_order(
                    symbol=ticker,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=quantity_close,
                )

            except Exception as e:
                logger.error(f"Error executing trade for {ticker}: {e}, skipping.")
            return 
        else: 
            logger.info("❌")
        
def run_live_entry_filters_and_execute_trades(
    return_based_entry_filters: list,
    exit_filters: list,
):
    logger.info("Running live entry filters...")

    while True: 

        tickers = read_tickers(filename='live_signal_tickers.txt')

        if len(tickers) > 0:
            evaluate_entry_filters_and_execute_one_trade(
                tickers, 
                return_based_entry_filters,
                exit_filters,
                **read_config()
            )
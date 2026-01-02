import json
import math
from os import write
import sys
import time
from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
import talib as ta
from binance.enums import *
from IPython.display import display
from loguru import logger

from bot.config.utils import close_position, read_config, read_positions, read_tickers, update_position, write_position, write_tickers
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

        logger.info(f"----- {ticker} - Signals -----")

        logger.info("initial filters")

        initial_filter_timeframe = kwargs.get('initial_filter_timeframe')
        info = get_ticker_info(ticker, initial_filter_timeframe)
        results = [f.event(info, **{k:kwargs[k] for k in f.REQUIRES}) for f in info_based_filters]

        if all(results):

            logger.info("✅")
            logger.info("signal filters")

            # Signal Filters

            df_direction = load_ohlcv(ticker, kwargs.get('signal_filter_timeframe'), "6 days ago UTC")
            results = [f.event(df_direction, **{k:kwargs[k] for k in f.REQUIRES}) for f in return_based_direction_filters]

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
    initial_filters: list,
    signal_filters: list,
    schedule_minutes: list[int],
    rerun_once_first: bool=False # run once and then schedule
):
    import schedule

    def job():
        logger.info("Running live signal filters...")
        time.sleep(2)
        passing_tickers = evaluate_signal_filters_once(
            tickers, 
            initial_filters, 
            signal_filters,
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

def evaluate_entry_filters_and_execute_trades(
    tickers: list[str], 
    return_based_entry_filters: list,
    **kwargs
):  
    logger.info("Evaluating entry filters and executing trades...")
    logger.info(f"Tickers to evaluate: {tickers}")

    for ticker in tickers:

        if ticker in read_positions().keys():
            logger.info(f"Already have position in {ticker}, skipping.")
            continue

        logger.info(f"----- {ticker} - Entry -----")

        logger.info("entry filters")

        df_entry = load_ohlcv(ticker, kwargs.get('execution_filter_timeframe'), "2 hours ago UTC")
        results = [f.event(df_entry, **{k:kwargs[k] for k in f.REQUIRES}) for f in return_based_entry_filters]

        if all(results):

            df_exit = load_ohlcv(ticker, kwargs.get('exit_filter_timeframe'), "1 day ago UTC")

            logger.info("✅")
            logger.info("executing trade")

            try: 

                info = client.get_symbol_info(ticker)
                last_atr = ta.ATR(df_exit['High'], df_exit['Low'], df_exit['Close'], timeperiod=14).iloc[-1]
                last_close = df_exit['Close'].iloc[-1]
                equity = float(client.get_margin_account()['totalCollateralValueInUSDT'])
                risk_pct  = float(kwargs['max_risk_per_trade'])
                total_risk_pct = float(kwargs['total_risk'])

                positions = read_positions()

                open_risk = sum([max(0.0,position['quantity'] * (position['buy_price'] - position['trailing_loss'])) for position in positions.values()])
                risk_left = total_risk_pct * equity - open_risk
                if risk_left <= 0:
                    logger.info("No risk budget left, skipping trade.")
                    continue

                risk_cash = equity * risk_pct
                risk_cash = min(equity * risk_pct, risk_left)                

                k = float(kwargs['entry_atr_stop_multiplier'])
                stop_distance = k * float(last_atr)
                if stop_distance <= 0:
                    continue

                raw_qty = float(risk_cash) / stop_distance

                # cap by notional/leverage for this single asset
                max_notional_per_asset = float(kwargs.get("max_leverage", 1.0)) * float(equity)
                raw_qty = min(raw_qty, max_notional_per_asset / float(last_close))

                # now round to LOT_SIZE
                lot = next(f for f in info["filters"] if f["filterType"] == "LOT_SIZE")
                step = Decimal(lot["stepSize"])
                min_qty = Decimal(lot["minQty"])

                qty_dec = Decimal(str(raw_qty))
                quantity = float((qty_dec // step) * step)

                min_notional_f = next((f for f in info["filters"] if f["filterType"] == "MIN_NOTIONAL"), None)
                if min_notional_f:
                    min_notional = float(min_notional_f["minNotional"])
                    if quantity * float(last_close) < min_notional:
                        continue

                # validate
                if Decimal(str(quantity)) < min_qty or quantity <= 0:
                    continue

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

                while check_order_status(ticker, order_id) != 'FILLED': time.sleep(1)
                time.sleep(1)

                buy_price = float(client.get_margin_trades(symbol=ticker, orderId=order_id)[0]['price'])
                total_outlay = quantity * buy_price

                logger.info(f'bought {quantity} of {ticker} at {buy_price} for {total_outlay}')
                quantity_close = get_position(ticker.split('USDT')[0])
                qty_dec = Decimal(str(quantity_close))
                quantity_close = float((qty_dec // step) * step)

                trailing_loss = buy_price - (last_atr * float(kwargs['entry_atr_stop_multiplier']))

                # Write new position to positions.json

                write_position(ticker, {
                    'quantity': quantity_close,
                    'buy_price': buy_price,
                    'total_outlay': total_outlay,
                    'trailing_loss': trailing_loss,
                    'atr_at_entry': last_atr,
                    'timestamp': time.time(),
                })

                logger.info(f"Position written with trailing loss at {trailing_loss}, last close {last_close}")

            except Exception as e:
                logger.error(f"Error executing trade for {ticker}: {e}, skipping.")
        else: 
            logger.info("❌")
        
def run_live_entry_filters_and_execute_trades(
    return_based_entry_filters: list,
):
    logger.info("Running live entry filters...")

    while True: 

        tickers = read_tickers(filename='live_signal_tickers.txt')

        if len(tickers) > 0:
            evaluate_entry_filters_and_execute_trades(
                tickers, 
                return_based_entry_filters,
                **read_config()
            )

        time.sleep(60)

def evaluate_exit_filters_and_execute_exits(
    exit_filters: list,
    **kwargs):
                
        positions = read_positions()

        for ticker, position in positions.items():
            try: 
                logger.info(f"----- Checking Stop Loss for {ticker} -----")
                quantity_close = position['quantity']
                total_outlay = position['total_outlay']
                trailing_loss = position['trailing_loss']
                last_atr = position['atr_at_entry']

                last_bar_close = load_ohlcv(ticker, kwargs.get('exit_filter_timeframe'), "1 day ago UTC")['Close'].iloc[-1]
                trailing_loss = max(trailing_loss, last_bar_close - (last_atr * kwargs.get('min_loss_atr')))
                potential_profit = (last_bar_close * quantity_close) - total_outlay

                logger.info(f"Last bar close: {last_bar_close}, Trailing loss: {trailing_loss}, Potential profit: {potential_profit}")

                update_position(ticker, {
                    'trailing_loss': trailing_loss,
                })

                if last_bar_close < trailing_loss:
                    logger.info("Trailing loss hit, selling.")
                    order = client.create_margin_order(
                        symbol=ticker,
                        side=SIDE_SELL,
                        type=ORDER_TYPE_MARKET,
                        quantity=quantity_close,
                    )
                    close_position(ticker)
                    logger.info(f"Sold {quantity_close} of {ticker} at market to close position.")

            except Exception as e:
                logger.error(f"Error during monitoring price for {ticker}: {e}, retrying next bar.")
                continue

def run_live_exit_filters_and_execute_exits(
    exit_filters: list,
    schedule_minutes: list[int],
    rerun_once_first: bool=False # run once and then schedule
):
    import schedule

    def job():
        logger.info("Running live exit filters...")
        time.sleep(2)
        evaluate_exit_filters_and_execute_exits(
            exit_filters,
            **read_config()
        )
    for minute in schedule_minutes:
        schedule.every().hour.at(f":{minute:02d}").do(job)

    
    if rerun_once_first:
        logger.info("Running live exit filters once before scheduling...")
        job()

    logger.info("Starting scheduled live exit filters...")
    while True:
        schedule.run_pending()
        time.sleep(1)

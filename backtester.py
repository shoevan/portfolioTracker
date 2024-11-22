import yfinance as yf
from requests_cache import CachedSession
from datetime import datetime, timezone, timedelta, date
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
import pandas as pd

Crypto = ("SOL-USD", "BTC-USD", "ETH-USD", "ADA-USD", "XRP-USD")
US_Shares = ("SPUS", "AAPL", "NVDA", "REIT", "VOO")


def calc_brokerage_cost(ticker_type: dict, amount_aud: int, usd_aud_rate):
    ticker_category = ticker_type["type"]
    if ticker_category == "Cryptocurrency":
        # Coinspot
        brokerage_cost = 0.01 * amount_aud
        remaining_amount = amount_aud - brokerage_cost
    elif ticker_category == "US_Shares":
        # Stake
        brokerage_cost = (0.007 * amount_aud + 3) * usd_aud_rate
        usd = amount_aud / usd_aud_rate
        remaining_amount = (usd - brokerage_cost) * usd_aud_rate
    return remaining_amount, brokerage_cost


def calc_dividends(ticker_type, total_units, dividends, buy_date: datetime, prev_month_buy_day: int, tz_string: str):
    start_date = buy_date
    month_delta = relativedelta(months=1)
    if prev_month_buy_day == 0:
        start_date = start_date.replace(day=1)
    else:
        start_date -= month_delta
        start_date = start_date.replace(day=prev_month_buy_day)
    delta = timedelta(days=1)
    found = False
    while start_date <= buy_date:
        full_date_string = f"{start_date.strftime('%Y-%m-%d')} 00:00:00{tz_string}"
        pd_date_index = pd.DatetimeIndex(data=[full_date_string])
        try:
            dividend_per_unit = dividends.loc[pd_date_index][0]
            if dividend_per_unit == 0.0:
                start_date += delta
                continue
            found = True
            break
        except KeyError:
            start_date += delta
            continue
        except Exception as e:
            print(e)
    if found:
        # print(f"Dividend found for buying period: {end_date.strftime('%Y-%m-%d')} = {dividend_per_unit}")0.0
        dividend_payout = dividend_per_unit * total_units
        if ticker_type["type"] == "US_Shares":
            tax = dividend_payout * 0.15
        net_dividend_payout = dividend_payout - tax
        # print(
        # f"Total Dividend payout: {dividend_payout}; Total dividend tax: {tax}; Total net: {net_dividend_payout}")
        return net_dividend_payout
    return 0


def closest_aud_price(aud_prices, buy_date: datetime):
    found = False
    delta = timedelta(days=1)
    start_date = datetime(year=buy_date.year, month=buy_date.month,
                          day=buy_date.day, tzinfo=ZoneInfo(key="Europe/Belfast"))
    while not found:
        utc_offset_str = get_utc_offset_str(date=start_date)
        full_date_string = f"{start_date.strftime('%Y-%m-%d')} 00:00:00{utc_offset_str}"
        pd_date_index = pd.DatetimeIndex(data=[full_date_string])
        try:
            aud_price = aud_prices["Close"].loc[pd_date_index][0]
            found = True
        except KeyError:
            start_date -= delta
        except Exception as e:
            print(e)
    return aud_price


def get_utc_offset_str(date: datetime):
    utc_offset = date.utcoffset()
    utc_offset_hours = utc_offset.total_seconds() // 3600
    utc_offset_minutes = (utc_offset.total_seconds() % 3600) // 60
    offset_str = f"{'+' if utc_offset_hours >= 0 else '-'}{'0' if utc_offset_hours < 10 else ''}{abs(int(utc_offset_hours))}:{int(utc_offset_minutes):02d}"
    return offset_str


def get_datetime_index(date: datetime):
    date_string = date.strftime('%Y-%m-%d')
    utc_offset_str = get_utc_offset_str(date=date)
    full_date_string = f"{date_string} 00:00:00{utc_offset_str}"
    return pd.DatetimeIndex(data=[full_date_string])


def strategy_price(ticker_prices: pd.DataFrame, initial_buy_date: datetime, strategy: str):
    strategies = ("Blind", "Red Day", "Red Low", "Red Day-5", "Red Day-10")
    day_delta = timedelta(days=1)
    if strategy not in strategies:
        exit(1)

    if strategy == "Blind":
        return ticker_prices["Close"].loc[get_datetime_index(date=initial_buy_date)][0], initial_buy_date
    elif strategy == "Red Day":
        open_price = ticker_prices["Open"].loc[get_datetime_index(
            date=initial_buy_date)][0]
        strat_price = ticker_prices["Close"].loc[get_datetime_index(
            date=initial_buy_date)][0]
        if strat_price < open_price:
            # print(f"{strat_price=} < {open_price=}")
            return strat_price, initial_buy_date
        else:
            found = False
            strategy_buy_date = initial_buy_date
            while not found:
                strategy_buy_date += day_delta
                try:
                    open_price = ticker_prices["Open"].loc[get_datetime_index(
                        date=strategy_buy_date)][0]
                    strat_price = ticker_prices["Close"].loc[get_datetime_index(
                        date=strategy_buy_date)][0]
                    if strat_price < open_price:
                        # print(f"{strat_price=} < {open_price=}")
                        return strat_price, strategy_buy_date
                except KeyError:
                    continue
    elif strategy == "Red Low":
        open_price = ticker_prices["Open"].loc[get_datetime_index(
            date=initial_buy_date)][0]
        strat_price = ticker_prices["Low"].loc[get_datetime_index(
            date=initial_buy_date)][0]
        if strat_price < open_price:
            # print(f"{strat_price=} < {open_price=}")
            return strat_price, initial_buy_date
        else:
            found = False
            strategy_buy_date = initial_buy_date
            while not found:
                strategy_buy_date += day_delta
                try:
                    open_price = ticker_prices["Open"].loc[get_datetime_index(
                        date=strategy_buy_date)][0]
                    strat_price = ticker_prices["Low"].loc[get_datetime_index(
                        date=strategy_buy_date)][0]
                    if strat_price < open_price:
                        # print(f"{strat_price=} < {open_price=}")
                        return strat_price, strategy_buy_date
                except KeyError:
                    continue


def main():
    tickers = ("BTC-USD", "SOL-USD", "ETH-USD", "XRP-USD")
    strategy = "Blind"
    day, month, year = 15, 1, 2021
    amount_added = 100

    session = CachedSession("yfinance.cache")
    session.headers["User-agent"] = 'my-program/1.0'
    for ticker in tickers:
        if ticker in Crypto:
            ticker_type = {
                "type": "Cryptocurrency",
                "timezone": ZoneInfo(key="Etc/Greenwich"),
                "tz_string_dst": "+00"

            }
        elif ticker in US_Shares:
            ticker_type = {
                "type": "US_Shares",
                "timezone": ZoneInfo(key="America/New_York"),
                "tz_string_dst": "-05"
            }
        ticker_info = yf.Ticker(ticker)
        ticker_prices = pd.DataFrame(ticker_info.history(period="5y"))
        aud = yf.Ticker("AUD=X")
        aud_prices = pd.DataFrame(aud.history(period="5y"))
        dividends = ticker_prices["Dividends"]
        total = 0
        total_brokerage_cost = 0
        total_current_value = 0
        dividend_total = 0
        total_units = 0
        dca_price = 0
        prev_month_buy_day = 0
        initial_date = datetime(year=year, month=month,
                                day=day,  tzinfo=ticker_type["timezone"])
        date_datetime = datetime(year=year, month=month,
                                 day=day,  tzinfo=ticker_type["timezone"])
        day_delta = timedelta(days=1)
        month_delta = relativedelta(months=1)
        date_now = datetime.now(tz=ticker_type["timezone"])
        while date_datetime < date_now:
            date_string = date_datetime.strftime('%Y-%m-%d')
            utc_offset_str = get_utc_offset_str(date=date_datetime)
            full_date_string = f"{date_string} 00:00:00{utc_offset_str}"
            datetime_index = pd.DatetimeIndex(data=[full_date_string])
            found = False
            while not found:
                try:
                    # date_price = ticker_prices["Close"].loc[datetime_index][0]
                    date_price, date_datetime = strategy_price(
                        ticker_prices=ticker_prices, initial_buy_date=date_datetime, strategy=strategy)
                    if ticker_type["type"] in ("US_Shares", "Cryptocurrency"):
                        usd_aud = closest_aud_price(
                            aud_prices=aud_prices, buy_date=date_datetime)
                    else:
                        usd_aud = 1
                    found = True
                    dividend_total += calc_dividends(ticker_type, total_units=total_units, dividends=dividends, buy_date=date_datetime,
                                                     prev_month_buy_day=prev_month_buy_day, tz_string=utc_offset_str)
                    prev_month_buy_day = date_datetime.day
                except KeyError:
                    date_datetime += day_delta
                    date_string = date_datetime.strftime('%Y-%m-%d')
                    full_date_string = f"{date_string} 00:00:00{utc_offset_str}"
                    datetime_index = pd.DatetimeIndex(data=[full_date_string])

            amount_added_minus_brokerage, brokerage_cost = calc_brokerage_cost(
                ticker_type=ticker_type, amount_aud=amount_added, usd_aud_rate=usd_aud)
            total += amount_added_minus_brokerage
            total_brokerage_cost += brokerage_cost
            units_bought = amount_added_minus_brokerage / usd_aud / date_price
            if dca_price == 0:
                dca_price = date_price
            else:
                dca_price = (dca_price * total_units + date_price *
                             units_bought) / (total_units + units_bought)
            total_units = total_units + units_bought
            total_current_value = total_units * date_price * usd_aud
            # print(f"{date_datetime}: \n\tPrice: {date_price:.2f}; Total added = ${total:.2f}; Total brokerage cost = ${total_brokerage_cost:.2f}; Total current value = ${total_current_value:.2f}; Return = {(total_current_value / total - 1) * 100:.2f}%; Total Dividend Income: {dividend_total * usd_aud:.2f}; Total Units = {total_units:.2f}; DCA = {dca_price:.2f}")
            date_datetime = date_datetime.replace(day=day)
            date_datetime += month_delta

        found = False
        day_delta = timedelta(days=1)
        date_shift = date_now
        print(f"{ticker=}; {strategy=}; From {initial_date.strftime('%Y-%m-%d')}")
        while not found:
            try:
                date_string = date_shift.strftime('%Y-%m-%d')
                full_date_string = f"{date_string} 00:00:00{utc_offset_str}"
                datetime_index = pd.DatetimeIndex(data=[full_date_string])
                date_price = ticker_prices["Close"].loc[datetime_index][0]
                if ticker_type["type"] in ("US_Shares", "Cryptocurrency"):
                    usd_aud = closest_aud_price(
                        aud_prices=aud_prices, buy_date=date_shift)
                total_current_value = total_units * date_price * usd_aud
                print(f"{date_now}: \n\tPrice: {date_price:.2f}; Total added = ${total:.2f}; Total brokerage cost = ${total_brokerage_cost:.2f}; Total current value = ${total_current_value:.2f}; Return = {(total_current_value / total - 1) * 100:.2f}%; Total Dividend Income: {dividend_total * usd_aud:.2f}; Total Units = {total_units:.2f}; DCA = {dca_price:.2f}")
                found = True
            except KeyError:
                date_shift -= day_delta


if __name__ == '__main__':
    main()

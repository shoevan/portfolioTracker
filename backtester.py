import yfinance as yf
from requests_cache import CachedSession
from datetime import datetime, timezone, timedelta, date
import pandas as pd

Crypto = ("SOL-USD", "BTC-USD", "ETH-USD")
US_Shares = ("SPUS", "AAPL", "NVDA", "REIT")


def calc_brokerage_cost(ticker_type: dict, amount_aud: int, usd_aud_rate):
    ticker_category = ticker_type["type"] 
    if ticker_category == "Cryptocurrency":
        # Coinspot
        brokerage_cost = 0.01 * amount_aud
        remaining_amount = amount_aud - brokerage_cost
    elif ticker_category == "US_Shares":
        #Stake
        brokerage_cost = 0.007 * amount_aud + 3
        usd = amount_aud / usd_aud_rate
        remaining_amount = usd - brokerage_cost
    return remaining_amount, brokerage_cost


def calc_dividends(ticker_type, total_units, dividends, year: int, month: int, buy_day: int, prev_month_buy_day: int, tz_string: str):
    if prev_month_buy_day == 0:
        start_date = date(year, month, 1)
    else:
        prev_month = month - 1
        if prev_month == 0:
            prev_month = 12
        start_date = date(year, prev_month, prev_month_buy_day)
    end_date = date(year, month, buy_day)
    delta = timedelta(days=1)
    found = False
    while start_date <= end_date:
        full_date_string = f"{start_date.strftime('%Y-%m-%d')} 00:00:00{tz_string}:00"
        pd_date_index = pd.DatetimeIndex(data=[full_date_string])
        try:
            dividend_per_unit = dividends.loc[pd_date_index][0]
            # print(f"{dividend_price=}")
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
        print(f"Total Dividend payout: {dividend_payout}; Total dividend tax: {tax}; Total net: {net_dividend_payout}")
        return net_dividend_payout
        # date = pd.DatetimeIndex(data=[full_date_string])
    return 0

def closest_aud_price(aud_prices, year: int, month: int, buy_day: int):
    found = False
    tz_flip = False
    delta = timedelta(days=1)
    tz_string = "+00"
    start_date = date(year, month, buy_day)
    while not found:
        full_date_string = f"{start_date.strftime('%Y-%m-%d')} 00:00:00{tz_string}:00"
        pd_date_index = pd.DatetimeIndex(data=[full_date_string])
        try:
            aud_price = aud_prices["Close"].loc[pd_date_index][0]
            # print(f"{aud_price=}")
            found = True
            break
        except KeyError:
            if not tz_flip:
                tz_string = "+01"
                tz_flip = True
            else:
                tz_flip = False
                tz_string = "+00"
                start_date += delta
            continue
        except Exception as e:
            print(e)
    return aud_price

def main():
    ticker = "BTC-USD"
    day, month, year = 1, 1, 2023
    amount_added = 100
    if ticker in Crypto:
        ticker_type = {
            "type": "Cryptocurrency",
            "tz_string_non_dst": "+00",
            "tz_string_dst": "+00"

        }
        tz_string_non_dst = "+00"
        tz_string_dst = "+00"
    elif ticker in US_Shares:
        ticker_type = {
            "type": "US_Shares",
            "tz_string_non_dst": "-04",
            "tz_string_dst": "-05"
        }
        tz_string_non_dst = "-04"
        tz_string_dst = "-05"

    session = CachedSession("yfinance.cache")
    session.headers["User-agent"] = 'my-program/1.0'
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
    date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(
        offset=-timedelta(hours=4), name="America/New_York"))
    date_now = datetime.now(tz=timezone(
        offset=-timedelta(hours=4), name="America/New_York"))
    while date_datetime < date_now:
        if month < 10:
            month_zero_pad = "0"
        else:
            month_zero_pad = ""
        if day < 10:
            day_zero_pad = f"0{day}"
        else:
            day_zero_pad = f"{day}"
        date_string = f"{year}-{month_zero_pad}{month}-{day_zero_pad}"
        tz_string = tz_string_non_dst
        full_date_string = f"{date_string} 00:00:00{tz_string}:00"
        date = pd.DatetimeIndex(data=[full_date_string])
        found = False
        while not found:
            try:
                date_price = ticker_prices["Close"].loc[date][0]
                if ticker_type["type"] in ("US_Shares", "Cryptocurrency"):
                    usd_aud = closest_aud_price(aud_prices, year=year, month=month, buy_day=day)
                else:
                    usd_aud = 1
                # print(f"{date_price=}")
                # aud_price = aud_prices["Close"].loc[date][0]
                # print(f"{aud_price=}")
                found = True
                dividend_total += calc_dividends(ticker_type, total_units=total_units, dividends=dividends, year=year, month=month, buy_day=day,
                               prev_month_buy_day=prev_month_buy_day, tz_string=tz_string)
                prev_month_buy_day = day
            except KeyError:
                day += 1
                if day > 30 or (day > 28 and month == 2):
                    tz_string = tz_string_dst
                    day = 1
                if day < 10:
                    day_zero_pad = f"0{day}"
                else:
                    day_zero_pad = f"{day}"
                date_string = f"{year}-{month_zero_pad}{month}-{day_zero_pad}"
                full_date_string = f"{date_string} 00:00:00{tz_string}:00"
                date = pd.DatetimeIndex(data=[full_date_string])
        
        # total += money_added
        amount_added_minus_brokerage, brokerage_cost = calc_brokerage_cost(ticker_type=ticker_type, amount_aud=amount_added, usd_aud_rate=usd_aud)
        total += amount_added_minus_brokerage
        total_brokerage_cost += brokerage_cost
        units_bought = amount_added_minus_brokerage / usd_aud / date_price
        if dca_price == 0:
            dca_price = date_price
        else:
            dca_price = (dca_price * total_units + date_price * units_bought) / (total_units + units_bought)
        total_units = total_units + units_bought
        total_current_value = total_units * date_price * usd_aud
        # dca_price = total / total_units + money_added / date_price
        date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(
            offset=-timedelta(hours=4), name="America/New_York"))
        print(f"{date_datetime}: \n\tPrice: {date_price:.2f}; Total added = ${total * usd_aud:.2f}; Total brokerage cost = ${total_brokerage_cost}; Total current value = ${total_current_value:.2f}; Return = {(total_current_value / total - 1) * 100:.2f}%; Total Dividend Income: {dividend_total:.2f}; Total Units = {total_units:.2f}; DCA = {dca_price:.2f}")
        month += 1
        day = 1
        if month == 13:
            month = 1
            year += 1
        date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(
            offset=-timedelta(hours=4), name="America/New_York"))
    found = False
    delta = timedelta(days=1)
    date_shift = date_now
    while not found:
        try:
            date_string = f"{date_shift.year}-{month_zero_pad}{date_shift.month}-{date_shift.day}"
            full_date_string = f"{date_string} 00:00:00{tz_string}:00"
            date = pd.DatetimeIndex(data=[full_date_string])
            date_price = ticker_prices["Close"].loc[date][0]
            if ticker_type["type"] in ("US_Shares", "Cryptocurrency"):
                usd_aud = closest_aud_price(aud_prices, year=date_shift.year, month=date_shift.month, buy_day=date_shift.day)
            total_current_value = total_units * date_price * usd_aud
            print(f"{date_now}: \n\tPrice: {date_price:.2f}; Total added = ${total * usd_aud:.2f}; Total brokerage cost = ${total_brokerage_cost:.2f}; Total current value = ${total_current_value * usd_aud:.2f}; Return = {(total_current_value / total - 1) * 100:.2f}%; Total Dividend Income: {dividend_total * usd_aud:.2f}; Total Units = {total_units:.2f}; DCA = {dca_price:.2f}")
            found = True
        except KeyError:
            date_shift -= delta

if __name__ == '__main__':
    main()

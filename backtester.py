import yfinance as yf
from requests_cache import CachedSession
from datetime import datetime, timezone, timedelta, date
import pandas as pd

Crypto = ("SOL-USD", "BTC-USD", "ETH-USD")
US_Shares = ("SPUS", "AAPL", "NVDA", "REIT")


def calc_brokerage_cost(ticker_type: str, amount_aud: int, usd_aud_rate):
    if ticker_type == "Cryptocurrency":
        brokerage_cost = 0.01 * amount_aud
        remaining_amount = amount_aud - brokerage_cost
    elif ticker_type == "US_Shares":
        brokerage_cost = 0.007 * amount_aud
        usd = amount_aud / usd_aud_rate
        remaining_amount = usd - brokerage_cost


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


def main():
    ticker = "BTC-USD"
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
    # print((ticker_prices.to_string()))
    # print((aud_prices.to_string()))
    # prices = pd.DataFrame(yf.download("AUD=X, SPUS", period="5y", prepost=True, threads=1))
    dividends = ticker_prices["Dividends"]
    # print(dividends.to_string())
    money_added = 100
    total = 0
    total_current_value = 0
    dividend_total = 0
    total_units = 0
    dca_price = 0
    day = 1
    prev_month_buy_day = 0
    month = 11
    year = 2023
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
        total += money_added
        if dca_price == 0:
            dca_price = date_price
        else:
            dca_price = (dca_price * total_units + date_price * money_added /
                         date_price) / (total_units + money_added / date_price)
        total_units = total_units + money_added / date_price
        total_current_value = total_units * date_price
        # dca_price = total / total_units + money_added / date_price
        date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(
            offset=-timedelta(hours=4), name="America/New_York"))
        print(f"{date_datetime}: Price: {date_price:.2f}; Total added = ${total}; Total current value = ${total_current_value:.2f}; Return = {(total_current_value / total - 1) * 100:.2f}%; Total Dividend Income: {dividend_total:.2f}; Total Units = {total_units:.2f}; DCA = {dca_price:.2f}")
        month += 1
        day = 1
        if month == 13:
            month = 1
            year += 1
        date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(
            offset=-timedelta(hours=4), name="America/New_York"))


if __name__ == '__main__':
    main()

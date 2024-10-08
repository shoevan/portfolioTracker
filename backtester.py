import yfinance as yf
from datetime import datetime, timezone, timedelta
import pandas as pd

Crypto = ("SOL-USD", "BTC-USD")
US_Shares = ("SPUS", "AAPL")

def calc_brokerage_cost(ticker_type: str, amount_aud: int, usd_aud_rate):
    if ticker_type == "Cryptocurrency":
        brokerage_cost = 0.01 * amount_aud
        remaining_amount = amount_aud - brokerage_cost
    elif ticker_type == "US_Shares":
        brokerage_cost = 0.007 * amount_aud
        usd = amount_aud / usd_aud_rate
        remaining_amount = usd - brokerage_cost


def main():
    ticker = "AAPL"
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
    ticker_info = yf.Ticker(ticker)
    prices = pd.DataFrame(ticker_info.history(period="5y"))
    dividends = prices["Dividends"]
    print(dividends.to_string())
    money_added = 100
    total = 0
    total_current_value = 0
    total_units = 0
    dca_price = 0
    day = 1
    month = 4
    year = 2020
    date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(offset=-timedelta(hours=4), name="America/New_York"))
    date_now = datetime.now(tz=timezone(offset=-timedelta(hours=4), name="America/New_York"))
    while date_datetime < date_now:
        print(f"{date_datetime} < {date_now}")
        if month < 10:
            month_zero_pad = "0"
        else: 
            month_zero_pad = ""
        date_string = f"{year}-{month_zero_pad}{month}-0{day}"
        tz_string = tz_string_non_dst
        full_date_string = f"{date_string} 00:00:00{tz_string}:00"
        date = pd.DatetimeIndex(data=[full_date_string])
        found = False
        while not found:
            try:
                date_price = prices["Close"].loc[date][0]
                found = True
            except KeyError:
                day += 1
                if day < 10:
                    day_zero_pad = "0"
                else: 
                    day_zero_pad = ""
                if day > 30 or (day > 28 and month == 2):
                    tz_string = tz_string_dst
                    day = 1
                date_string = f"{year}-{month_zero_pad}{month}-{day_zero_pad}{day}"
                full_date_string = f"{date_string} 00:00:00{tz_string}:00"
                date = pd.DatetimeIndex(data=[full_date_string])
        total += money_added
        if dca_price == 0:
            dca_price = date_price
        else:
            dca_price = (dca_price * total_units + date_price * money_added / date_price) / (total_units + money_added / date_price)
        total_units = total_units + money_added / date_price
        total_current_value = total_units * date_price
        # dca_price = total / total_units + money_added / date_price
        date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(offset=-timedelta(hours=4), name="America/New_York"))
        print(f"{date_datetime}: Price: {date_price}; Total added = ${total}; Total current value = ${total_current_value}; Total Units = {total_units}; DCA = {dca_price}")
        month += 1
        day = 1
        if month == 13:
            month = 1
            year += 1
        date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(offset=-timedelta(hours=4), name="America/New_York"))
        




if __name__ == '__main__':
    main()


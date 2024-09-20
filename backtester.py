import yfinance as yf
from datetime import datetime, timezone, timedelta
import pandas as pd


def main():
    spus = yf.Ticker("BTC-USD")
    prices = pd.DataFrame(spus.history(period="5y"))
    # print(prices.to_string())
    money_added = 1000
    total = 0
    total_current_value = 0
    total_units = 0
    dca_price = 0
    day = 1
    month = 4
    year = 2020
    date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(offset=-timedelta(hours=4), name="America/New_York"))
    while date_datetime < datetime.now(tz=timezone(offset=-timedelta(hours=4), name="America/New_York")):
        day = 1
        date_datetime = datetime(year=year, month=month, day=day,  tzinfo=timezone(offset=-timedelta(hours=4), name="America/New_York"))
        if month < 10:
            month_zero_pad = "0"
        else: 
            month_zero_pad = ""
        date_string = f"{year}-{month_zero_pad}{month}-0{day}"
        tz_string = 0
        full_date_string = f"{date_string} 00:00:00+0{tz_string}:00"
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
                    tz_string = "5"
                    day = 1
                date_string = f"{year}-{month_zero_pad}{month}-{day_zero_pad}{day}"
                full_date_string = f"{date_string} 00:00:00+0{tz_string}:00"
                date = pd.DatetimeIndex(data=[full_date_string])
        total += money_added
        if dca_price == 0:
            dca_price = date_price
        else:
            dca_price = (dca_price * total_units + date_price * money_added / date_price) / (total_units + money_added / date_price)
        total_units = total_units + money_added / date_price
        total_current_value = total_units * date_price
        # dca_price = total / total_units + money_added / date_price
        month += 1
        if month == 13:
            month = 1
            year += 1
        print(f"{date_datetime}: Price: {date_price}; Total added = ${total}; Total current value = ${total_current_value}; Total Units = {total_units}; DCA = {dca_price}")
        




if __name__ == '__main__':
    main()


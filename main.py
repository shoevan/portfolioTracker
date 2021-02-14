import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import openpyxl
from datetime import datetime as dt

def add_values_in_dict(sample_dict, key, list_of_values):
    """Append multiple values to a key in the given dictionary"""
    if key not in sample_dict:
        sample_dict[key] = list()
    sample_dict[key].extend(list_of_values)
    return sample_dict

# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    portfolio = pd.read_excel(r'E:\Users\Sajib Ahmed (Shovon)\Dropbox\Dropbox\Stock Portfolio.xlsx', usecols="A:C")
    portValue = pd.read_csv(r'E:\Users\Sajib Ahmed (Shovon)\Dropbox\Dropbox\Portfolio Value Tracking.csv')
    stocks = pd.DataFrame(portfolio)
    portValDf = pd.DataFrame(portValue)
    stocks = stocks.dropna()
    stonks = {}
    for ind, ticker in stocks.iterrows():
        name = ticker[0]
        units = ticker[1]
        priceBought = ticker[2]
        prevClose = yf.Ticker(ticker[0]).info['previousClose']
        usdToAUD = yf.Ticker("AUD=X").info['previousClose']
        if name.endswith("AX"):
            initValueAUD = units * priceBought
            currValueAUD = units * prevClose
        else:
            initValueAUD = units * priceBought * usdToAUD
            currValueAUD = units * prevClose * usdToAUD
        percChange = currValueAUD / initValueAUD * 100 - 100

        stonks = add_values_in_dict(stonks, name,
                                    [units, priceBought, prevClose, initValueAUD, currValueAUD, percChange])
    # print(aapl.history(start="2020-09-09", end=dt.today().strftime('%Y-%m-%d')))

    # print(stonks)
    initPortValue = 0
    currPortValue = 0
    for key in stonks:
        initPortValue += stonks[key][3]
        currPortValue += stonks[key][4]
    percPortChange = currPortValue / initPortValue * 100 - 100

    print("Initial Portfolio Value is: " + str(initPortValue))
    print("Current Portfolio Value is: " + str(currPortValue))
    print("Percentage Portfolio Performance: " + str(percPortChange))
    # data = yf.download("AAPL AMD", start="2020-09-09", end=dt.today().strftime('%Y-%m-%d'), group_by="ticker", threads=1)
    # print(data['AAPL']['Close'])

    if portValDf.iloc[len(portValDf) - 1][0] != dt.today().strftime('%Y-%m-%d'):
        df2 = pd.DataFrame([[dt.today().strftime('%Y-%m-%d'), currPortValue, percPortChange]],
                           columns=['Date', 'Value', 'Percentage'])
        portValDf = portValDf.append(df2, ignore_index=True)
    else:
        portValDf.iloc[len(portValDf) - 1][1] = currPortValue
        portValDf.iloc[len(portValDf) - 1][2] = percPortChange

    # print(portValDf)

    portValDf.plot(kind='scatter', x='Date', y='Value')
    plt.show()
    portValDf.to_csv(r'E:\Users\Sajib Ahmed (Shovon)\Dropbox\Dropbox\Portfolio Value Tracking.csv', index=False)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/

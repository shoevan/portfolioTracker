import pandas as pd
import yfinance as yf
import math
import matplotlib.pyplot as plt
from datetime import datetime as dt


def add_values_in_dict(sample_dict, keys, list_of_values):
    """Append multiple values to a key in the given dictionary"""
    if keys not in sample_dict:
        sample_dict[keys] = list()
    sample_dict[keys].extend(list_of_values)
    return sample_dict


if __name__ == '__main__':
    portfolio = pd.read_excel(r'E:\Users\Sajib Ahmed (Shovon)\Dropbox\Dropbox\Stock Portfolio.xlsx', usecols="A:C")
    portValue = pd.read_csv(r'E:\Users\Sajib Ahmed (Shovon)\Dropbox\Dropbox\Portfolio Value Tracking.csv')
    stocks = pd.DataFrame(portfolio)
    portValDf = pd.DataFrame(portValue)
    stocks = stocks.dropna()
    stonks = {}
    nameTickers = "AUD=X"
    for ind, ticker in stocks.iterrows():
        nameTickers += " " + ticker[0]
        stonks = add_values_in_dict(stonks, ticker[0], ['', '', '', '', '', ''])

    data = yf.download(nameTickers, period="3d", threads=1)
    dataDf = pd.DataFrame(data)

    for ind, ticker in stocks.iterrows():
        name = ticker[0]
        units = ticker[1]
        priceBought = ticker[2]
        dateOffset = 3
        while math.isnan(dataDf['Adj Close'][name].iloc[dateOffset]):
            dateOffset -= 1
        prevClose = dataDf['Adj Close'][name].iloc[dateOffset]
        dateOffset = 3
        while math.isnan(dataDf['Adj Close']['AUD=X'].iloc[dateOffset]):
            dateOffset -= 1
        usdToAUD = dataDf['Adj Close']['AUD=X'].iloc[dateOffset]
        if name.endswith("AX"):
            initValueAUD = units * priceBought
            currValueAUD = units * prevClose
        else:
            initValueAUD = units * priceBought * usdToAUD
            currValueAUD = units * prevClose * usdToAUD
        percChange = currValueAUD / initValueAUD * 100 - 100
        stonks[name][0] = units
        stonks[name][1] = priceBought
        stonks[name][2] = prevClose
        stonks[name][3] = initValueAUD
        stonks[name][4] = currValueAUD
        stonks[name][5] = percChange

    initPortValue = 0
    currPortValue = 0
    for key in stonks:
        initPortValue += stonks[key][3]
        currPortValue += stonks[key][4]
    percPortChange = currPortValue / initPortValue * 100 - 100

    print("Initial Portfolio Value is: " + str(initPortValue))
    print("Current Portfolio Value is: " + str(currPortValue))
    print("Percentage Portfolio Performance: " + str(percPortChange))

    if portValDf.iloc[len(portValDf) - 1][0] != dt.today().strftime('%d/%m/%Y'):
        df2 = pd.DataFrame([[dt.today().strftime('%d/%m/%Y'), currPortValue, percPortChange]],
                           columns=['Date', 'Value', 'Percentage'])
        portValDf = portValDf.append(df2, ignore_index=True)
    else:
        portValDf.iloc[len(portValDf) - 1, 1] = str(float("{:.2f}".format(currPortValue)))
        portValDf.iloc[len(portValDf) - 1, 2] = str(float("{:.2f}".format(percPortChange)))

    portValDf.to_csv(r'E:\Users\Sajib Ahmed (Shovon)\Dropbox\Dropbox\Portfolio Value Tracking.csv', index=False)
    plt.figure(figsize=(16, 9))
    plt.plot_date(portValDf['Date'], portValDf['Value'], xdate=True)
    plt.title("Portfolio Performance over time")
    plt.ylabel("Portfolio Value ($)")
    plt.xlabel("Date")
    plt.show()

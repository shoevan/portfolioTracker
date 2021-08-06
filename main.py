import pandas as pd
import yfinance as yf
import math
import matplotlib.pyplot as plt
import sys
import getopt
from datetime import datetime as dt


def add_values_in_dict(sample_dict, keys, list_of_values):
    """Append multiple values to a key in the given dictionary"""
    if keys not in sample_dict:
        sample_dict[keys] = list()
        sample_dict[keys].extend(list_of_values)
    return sample_dict

def dollarCostAveragingHandler(stonks, name, units, priceBought, valueAUD, purchaseValueAUD):
    initUnits = stonks[name][0]
    initPriceBought = stonks[name][1]
    initValueAUD = stonks[name][3]
    initPurchaseValueAUD = stonks[name][4]

    print("Values here ", initUnits, units, initPriceBought, priceBought, initValueAUD, valueAUD, initPurchaseValueAUD, purchaseValueAUD)
    #[Units, Initial price, Latest closing price, Initial AUD asset value, Current AUD asset value, % returns]
    stonks[name][0] = float(initUnits) + units
    stonks[name][1] = (initPriceBought * initUnits + priceBought * units) / stonks[name][0]
    stonks[name][3] = initValueAUD + valueAUD
    stonks[name][4] = initPurchaseValueAUD + purchaseValueAUD
    stonks[name][5] = stonks[name][4] / stonks[name][3] * 100 - 100

    print("Final values: ", stonks[name][0], stonks[name][1], stonks[name][3], stonks[name][4], stonks[name][5])
    return stonks

def main(argv):
    portfolioDir = ''
    portValueDir = ''
    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["ifile=", "ofile="])
    except getopt.GetoptError:
        print
        'main.py -i <portfolio path> -o <portfolio output directory>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print
            'test.py -i <portfolio path> -o <portfolio output directory>'
            sys.exit()
        elif opt in ("-i", "--ifile"):
            portfolioDir = arg
        elif opt in ("-o", "--ofile"):
            portValueDir = arg
    print('Input file is "', portfolioDir)
    print('Output file is "', portValueDir)
    portfolio = pd.read_excel(portfolioDir, usecols="B:D")
    portValue = pd.read_csv(portValueDir)
    #Import initial portfolio investment and output csv as a DataFrame
    stocks = pd.DataFrame(portfolio)
    portValDf = pd.DataFrame(portValue)
    print(stocks)
    #Drops any empty values
    stocks = stocks.dropna()
    stonks = {}
    #Require this
    nameTickers = "AUD=X"
    for ticker in stocks.itertuples():
        if ticker.Ticker not in stonks:
            nameTickers += " " + ticker.Ticker
            #stonks: {Ticker: [Units, Initial price, Latest closing price, Initial AUD asset value, Current AUD asset value, % returns]}
            stonks = add_values_in_dict(stonks, ticker.Ticker, ['', '', '', '', '', ''])

    dataDf = pd.DataFrame(yf.download(nameTickers, period="3d", prepost=True, threads=1))
    stuff = yf.Tickers(nameTickers)
    #Get latest USD/AUD exchange rate
    #Start from todays current date which is the 3rd row, iterate back until value is not null
    dateOffset = 2
    print(dataDf['Adj Close']['AUD=X'])
    while math.isnan(dataDf['Adj Close']['AUD=X'].iloc[dateOffset]):
        dateOffset -= 1
    usdToAUD = dataDf['Adj Close']['AUD=X'].iloc[dateOffset]
    #Loop through each ticker
    for ticker in stocks.itertuples():
        name = ticker.Ticker
        units = float(ticker.Units)
        priceBought = float(ticker.Price)
        dateOffset = 2
        while math.isnan(dataDf['Adj Close'][name].iloc[dateOffset]):
            dateOffset -= 1
        prevClose = dataDf['Adj Close'][name].iloc[dateOffset]
        #If the ticker is for ASX
        if name.endswith("AX"):
            initValueAUD = units * priceBought
            currValueAUD = units * prevClose
            priceBoughtAUD = priceBought
        #If ticker is is measured in USD
        else:
            initValueAUD = units * priceBought * usdToAUD
            currValueAUD = units * prevClose * usdToAUD
            priceBoughtAUD = priceBought * usdToAUD
        if stonks[name][0]:
            print(name, " in stonks")
            stonks = dollarCostAveragingHandler(stonks, name, units, priceBought, initValueAUD, currValueAUD)
        else:
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

    print(stonks)
    print("Initial Portfolio Value is: " + str(initPortValue))
    print("Current Portfolio Value is: " + str(currPortValue))
    print("Percentage Portfolio Performance: " + str(percPortChange))

    #Find if .csv already has a value for todays date
    if portValDf.iloc[len(portValDf) - 1][0] != dt.today().strftime('%d/%m/%Y'):
        df2 = pd.DataFrame([[dt.today().strftime('%d/%m/%Y'), currPortValue, percPortChange]],
                           columns=['Date', 'Value', 'Percentage'])
        portValDf = portValDf.append(df2, ignore_index=True)
    else:
        portValDf.iloc[len(portValDf) - 1, 1] = str(float("{:.2f}".format(currPortValue)))
        portValDf.iloc[len(portValDf) - 1, 2] = str(float("{:.2f}".format(percPortChange)))

    # portValDf.to_csv(r'E:\Users\Sajib Ahmed (Shovon)\Dropbox\Dropbox\Portfolio Value Tracking.csv', index=False)
    portValDf.to_csv(portValueDir, index=False)
    plt.figure(figsize=(16, 9))
    plt.plot_date(portValDf['Date'], portValDf['Value'], xdate=True)
    plt.title("Portfolio Performance over time")
    plt.ylabel("Portfolio Value ($)")
    plt.xlabel("Date")
    plt.show()

if __name__ == '__main__':
    main(sys.argv[1:])


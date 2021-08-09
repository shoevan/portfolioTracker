import pandas as pd
import yfinance as yf
import math
import matplotlib.pyplot as plt
import sys
import getopt
import logging
from datetime import datetime as dt

class Security:
    def __init__(self, ticker, units, dcaPrice, prevClose, AUD_exchange_rate):
        self.ticker = ticker
        self.units = units
        self.dcaPrice = dcaPrice
        self.currPrice = prevClose
        self.AUD_exchange_rate = AUD_exchange_rate

        if self.ticker.endswith("AX"):
            self.AUD_exchange_rate = 1

        self.initValueAUD = self.setValueAUD(self.dcaPrice)
        self.currValueAUD = self.setValueAUD(self.currPrice)
        self.percentReturns = self.calculatePercentReturns()

    def dollarCostAveragingHandler(self, units, priceBought, AUD_exchange_rate):
        initUnits = self.units
        initPriceBought = self.dcaPrice
        currPrice = self.currPrice
        initValueAUD = self.initValueAUD
        currValueAUD = self.currValueAUD

#        print("Values here ", self.ticker, initUnits, units, initPriceBought, priceBought, currPrice, initValueAUD, currValueAUD, AUD_exchange_rate)
        # [Units, Initial price, Latest closing price, Initial AUD asset value, Current AUD asset value, % returns]
        self.units  = initUnits + units
        self.dcaPrice = (initPriceBought * initUnits + priceBought * units) / self.units
        self.initValueAUD = initValueAUD + units * priceBought * AUD_exchange_rate
        self.currValueAUD = currValueAUD + units * currPrice * AUD_exchange_rate
        self.percentReturns = self.calculatePercentReturns()


#        print("Final values: ", self.ticker, self.units, self.dcaPrice, self.currPrice, self.initValueAUD, self.currValueAUD, self.percentReturns)

    def getTicker(self):
        return self.ticker

    def getUnits(self):
        return self.units

    def getInitPrice(self):
        return self.dcaPrice

    def getCurrPrice(self):
        return self.currPrice

    def getInitValue(self):
        return self.initValueAUD

    def getCurrValue(self):
        return self.currValueAUD

    def getPercentReturns(self):
        return self.percentReturns

    def setValueAUD(self, price):
        return self.units * price * self.AUD_exchange_rate

    def calculatePercentReturns(self):
        return self.currValueAUD / self.initValueAUD * 100 - 100

def plotPieChart(labels, value):
    fig1, ax1 = plt.subplots()
    ax1.pie(value, labels=labels, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')
    plt.show()

def main(argv):

    logging.basicConfig(filename="portfolioTracker.log", encoding="utf-8", filemode="w", format="%(asctime)s - %(levelname)s: %(message)s", level=logging.DEBUG)
    portfolioDir = ''
    portValueDir = ''
    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["ifile=", "ofile="])
    except getopt.GetoptError:
        print('main.py -i <portfolio path> -o <portfolio output directory>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('test.py -i <portfolio path> -o <portfolio output directory>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            portfolioDir = arg
        elif opt in ("-o", "--ofile"):
            portValueDir = arg
    logging.info("Input file is: %s", portfolioDir)
    logging.info("Output file is: %s", portValueDir)
    portfolio = pd.read_excel(portfolioDir, usecols="B:D")
    portValue = pd.read_csv(portValueDir)
    #Import initial portfolio investment and output csv as a DataFrame
    stocks = pd.DataFrame(portfolio)
    portValDf = pd.DataFrame(portValue)
    #Drops any empty values
    stocks = stocks.dropna()
    logging.debug("Stock portfolio input file: %s", stocks)
    stonks = {}
    #Build a list of unique ticker names to query Yahoo Finance with - need the current USD/AUD exhange rate so prefilled
    # logging.debug("Stock portfolio input file: %s", stocks)
    nameTickers = "AUD=X"
    for ticker in stocks.itertuples():
        if ticker.Ticker not in nameTickers:
            nameTickers += " " + ticker.Ticker
            #stonks: {Ticker: [Units, Initial price, Latest closing price, Initial AUD asset value, Current AUD asset value, % returns]}
            #stonks = add_values_in_dict(stonks, ticker.Ticker, ['', '', '', '', '', ''])

    dataDf = pd.DataFrame(yf.download(nameTickers, period="3d", prepost=True, threads=1))
    logging.debug(dataDf.to_string())
    #Get latest USD/AUD exchange rate
    #Start from todays current date which is the 3rd row, iterate back until value is not null
    dateOffset = 2
    while math.isnan(dataDf['Adj Close']['AUD=X'].iloc[dateOffset]):
        dateOffset -= 1
    usdToAUD = dataDf['Adj Close']['AUD=X'].iloc[dateOffset]
    #Loop through each ticker
    for ticker in stocks.itertuples():
        if ticker.Ticker in stonks:
            stonks[ticker.Ticker].dollarCostAveragingHandler(ticker.Units, ticker.Price, usdToAUD)
        else:
            dateOffset = 2
            while math.isnan(dataDf['Adj Close'][ticker.Ticker].iloc[dateOffset]):
                dateOffset -= 1
            prevClose = dataDf['Adj Close'][ticker.Ticker].iloc[dateOffset]
            stonks[ticker.Ticker] = Security(ticker.Ticker, ticker.Units, ticker.Price, prevClose, usdToAUD)
    initPortValue = 0
    currPortValue = 0

    portfolioDf = {"Ticker": [], "Units Purchased": [], "Initial Price": [], "Latest Close": [], "Initial AUD Asset Value": [], "Current AUD Asset Value": [], "Percentage Returns": []}
    for key in sorted(stonks):
        portfolioDf["Ticker"].append(stonks[key].getTicker())
        portfolioDf["Units Purchased"].append(stonks[key].getUnits())
        portfolioDf["Initial Price"].append(stonks[key].getInitPrice())
        portfolioDf["Latest Close"].append(stonks[key].getCurrPrice())
        portfolioDf["Initial AUD Asset Value"].append(stonks[key].getInitValue())
        portfolioDf["Current AUD Asset Value"].append(stonks[key].getCurrValue())
        portfolioDf["Percentage Returns"].append(stonks[key].getPercentReturns())
        initPortValue += stonks[key].getInitValue()
        currPortValue += stonks[key].getCurrValue()
    percPortChange = currPortValue / initPortValue * 100 - 100

    print(pd.DataFrame(portfolioDf).to_string())
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

    tickerList = []
    tickerValue = []
    for key in stonks:
        tickerList.append(key)
        tickerValue.append(stonks[key].getCurrValue())
    plotPieChart(tickerList, tickerValue)
    portValDf.to_csv(portValueDir, index=False)
    plt.figure(figsize=(16, 9))
    plt.plot_date(portValDf['Date'], portValDf['Value'], xdate=True)
    plt.title("Portfolio Performance over time")
    plt.ylabel("Portfolio Value ($)")
    plt.xlabel("Date")
    plt.show()

if __name__ == '__main__':
    main(sys.argv[1:])


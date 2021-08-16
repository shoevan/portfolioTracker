import pandas as pd
import yfinance as yf
import math
import matplotlib.pyplot as plt
import sys
import getopt
import logging
from datetime import datetime as dt

WRITE_TO_FILE=1

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

    def dollarCostAveragingHandler(self, units, priceBought):
        initUnits = self.units
        initPriceBought = self.dcaPrice
        currPrice = self.currPrice
        initValueAUD = self.initValueAUD
        currValueAUD = self.currValueAUD

        self.units  = initUnits + units
        self.dcaPrice = (initPriceBought * initUnits + priceBought * units) / self.units
        self.initValueAUD = initValueAUD + units * priceBought * self.AUD_exchange_rate
        self.currValueAUD = currValueAUD + units * currPrice * self.AUD_exchange_rate
        self.percentReturns = self.calculatePercentReturns()

    def sellEventHandler(self, units, priceSold):
        if(self.units < units):
            print(f"Error: Units sold for {self.getTicker()} cannot be greater than units pre-existing in portfolio. "
                  f"Please update the portfolio spreadsheet with corrected units")
            sys.exit()
        else:
            print("Units ", units)
            self.units = self.units - units
            self.initValueAUD = self.setValueAUD(self.dcaPrice)
            self.currValueAUD = self.setValueAUD(self.currPrice)
        if priceSold:
            return (priceSold - self.dcaPrice) * self.units

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
    stonks = {}
    nameTickers = "AUD=X"
    initPortValue = 0
    currPortValue = 0
    realisedProfitLoss = 0
    tickerList = []
    tickerValue = []
    csvFound = True

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

    # Import initial portfolio investment and output csv as a DataFrame
    try:
        portfolio = pd.read_excel(portfolioDir, usecols="B:E")
        stocks = pd.DataFrame(portfolio)
        # Drops any empty values
        stocks = stocks.dropna()
        logging.debug("Stock portfolio input file: %s", stocks)
    except FileNotFoundError:
        print(f"{portfolio} not found. Require an excel spreadsheet listing transactions. Please see script usage page")
        sys.exit()
    try:
        portValue = pd.read_csv(portValueDir)
        portValDf = pd.DataFrame(portValue)
    except FileNotFoundError:
        userResponse = input(f"{portValueDir} not found. Should a new csv be created? [y/n]: ")
        if userResponse == "y":
            print("Creating new csv...")
            csvFound = False
        elif userResponse == "n":
            print("Not creating a new csv, please review arguments, exiting...")
            sys.exit()
        else:
            print("Correct input of [y/n] not detected, exiting...")
            sys.exit()


    #Build a list of unique ticker names to query Yahoo Finance with - need the current USD/AUD exhange rate so prefilled
    # logging.debug("Stock portfolio input file: %s", stocks)
    for ticker in stocks.itertuples():
        if ticker.Ticker not in nameTickers:
            nameTickers += " " + ticker.Ticker

    dataDf = pd.DataFrame(yf.download(nameTickers, period="3d", prepost=True, threads=1))
    logging.debug(dataDf.to_string())
    #Get latest USD/AUD exchange rate
    #Start from the last row available, iterate back until value is not null to get latest closing value
    dateOffset = len(dataDf['Adj Close']['AUD=X'].index) - 1
    while math.isnan(dataDf['Adj Close']['AUD=X'].iloc[dateOffset]):
        dateOffset -= 1
    usdToAUD = dataDf['Adj Close']['AUD=X'].iloc[dateOffset]
    #Loop through each ticker
    for ticker in stocks.itertuples():
        print(ticker.Action)
        if ticker.Action == "BUY":
            if ticker.Ticker in stonks:
                stonks[ticker.Ticker].dollarCostAveragingHandler(ticker.Units, ticker.Price)
            else:
                dateOffset = len(dataDf['Adj Close'][ticker.Ticker].index) - 1
                while math.isnan(dataDf['Adj Close'][ticker.Ticker].iloc[dateOffset]):
                    dateOffset -= 1
                prevClose = dataDf['Adj Close'][ticker.Ticker].iloc[dateOffset]
                stonks[ticker.Ticker] = Security(ticker.Ticker, ticker.Units, ticker.Price, prevClose, usdToAUD)
        elif ticker.Action == "SELL" or ticker.Action == "TRANSACTION":
            if ticker.Ticker in stonks:
                if ticker.Action == "SELL":
                    realisedProfitLoss += stonks[ticker.Ticker].sellEventHandler(ticker.Units, ticker.Price)
                else:
                    stonks[ticker.Ticker].sellEventHandler(ticker.Units, None)
            else:
                print(f"{ticker.Ticker} has not been bought prior to the sell event, please review the portfolio "
                      f"spreadsheet")
                sys.exit()

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
    print(f"Realised Profit/Loss: ${realisedProfitLoss}AUD")

    #Find if .csv already has a value for todays date
    if csvFound:
        if portValDf.iloc[len(portValDf) - 1][0] != dt.today().strftime('%d/%m/%Y'):
            df2 = pd.DataFrame([[dt.today().strftime('%d/%m/%Y'), currPortValue, percPortChange]],
                               columns=['Date', 'Value', 'Percentage'])
            portValDf = portValDf.append(df2, ignore_index=True)
        else:
            portValDf.iloc[len(portValDf) - 1, 1] = str(float("{:.2f}".format(currPortValue)))
            portValDf.iloc[len(portValDf) - 1, 2] = str(float("{:.2f}".format(percPortChange)))
    else:
        portValDf = pd.DataFrame([[dt.today().strftime('%d/%m/%Y'), currPortValue, percPortChange]], columns=["Date", "Value", "Percentage"])
        portValDf.to_csv(portValueDir)

    if WRITE_TO_FILE:
        portValDf.to_csv(portValueDir, index=False)

    for key in stonks:
        tickerList.append(key)
        tickerValue.append(stonks[key].getCurrValue())
    plotPieChart(tickerList, tickerValue)
    plt.figure(figsize=(16, 9))
    plt.plot_date(portValDf['Date'], portValDf['Value'], xdate=True)
    plt.title("Portfolio Performance over time")
    plt.ylabel("Portfolio Value ($)")
    plt.xlabel("Date")
    plt.tight_layout
    plt.show()

if __name__ == '__main__':
    main(sys.argv[1:])


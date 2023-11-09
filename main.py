import pandas as pd
import yfinance as yf
import math
import matplotlib.pyplot as plt
import sys
import getopt
import logging
import openpyxl
from datetime import datetime as dt
import ausdex
WRITE_TO_FILE=1

class Security:
    def __init__(self, ticker, units, dcaPrice, prevClose, init_buy_date, init_AUD_exchange_rate = 1, current_AUD_exchange_rate = 1):
        self.ticker = ticker
        self.units = units
        self.dcaPrice = dcaPrice
        self.currPrice = prevClose
        self.init_AUD_exchange_rate = init_AUD_exchange_rate
        self.current_AUD_exchange_rate = current_AUD_exchange_rate

        if self.ticker.endswith("AX"):
            self.assetType = "AUS Market"
            self.current_AUD_exchange_rate = 1
        elif self.ticker.endswith("USD"):
            self.assetType = "Cryptocurrency"
        else:
            self.assetType = "US Market"

        self.initValueAUD = self.setValueAUD(self.dcaPrice, "initial")
        self.initValueCPIAdjustedAUD = ausdex.calc_inflation(value=self.initValueAUD, original_date=init_buy_date, location="Brisbane")
        self.currValueAUD = self.setValueAUD(self.currPrice, "current")
        self.percentReturns = self.calculatePercentReturns()

    def dollarCostAveragingHandler(self, units, priceBought, AUD_exchange_rate, buy_date):
        initUnits = self.units
        initPriceBought = self.dcaPrice
        currPrice = self.currPrice
        initValueAUD = self.initValueAUD
        currValueAUD = self.currValueAUD

        self.units  = initUnits + units
        self.dcaPrice = (initPriceBought * initUnits + priceBought * units) / self.units
        self.initValueAUD = initValueAUD + units * priceBought * AUD_exchange_rate
        self.initValueCPIAdjustedAUD = self.initValueCPIAdjustedAUD + ausdex.calc_inflation(value=units * priceBought * AUD_exchange_rate, original_date=buy_date, location="Brisbane")
        self.currValueAUD = currValueAUD + units * currPrice * self.current_AUD_exchange_rate
        self.percentReturns = self.calculatePercentReturns()

    def sellEventHandler(self, units, priceSold):
        if(self.units < units):
            print(f"Error: Units sold for {self.getTicker()} cannot be greater than units pre-existing in portfolio. "
                  f"Please update the portfolio spreadsheet with corrected units")
            sys.exit()
        else:
            self.units = self.units - units
            self.initValueAUD = self.setValueAUD(self.dcaPrice, "initial")
            self.currValueAUD = self.setValueAUD(self.currPrice, "current")
        self.percentReturns = self.calculatePercentReturns()
        if priceSold:
            return (priceSold - self.dcaPrice) * self.units

    def dividend_addition(self, units):
        self.units = self.units + units
        self.currValueAUD = self.units * self.currPrice * self.current_AUD_exchange_rate
        self.percentReturns = self.calculatePercentReturns()

        return units * self.currPrice * self.current_AUD_exchange_rate

    def getTicker(self):
        return self.ticker

    def getAssetType(self):
        return self.assetType
    
    def getUnits(self):
        return self.units

    def getInitPrice(self):
        return self.dcaPrice

    def getCurrPrice(self):
        return self.currPrice

    def getInitValue(self):
        return self.initValueAUD
    
    def getInitCPIAdjustedValue(self):
        return self.initValueCPIAdjustedAUD

    def getCurrValue(self):
        return self.currValueAUD

    def getPercentReturns(self):
        return self.percentReturns
    
    def getPercentReturnsCPIAdj(self):
        return self.currValueAUD / self.initValueCPIAdjustedAUD * 100 - 100

    def setValueAUD(self, price, mode):
        if mode == "initial":
            return self.units * price * self.init_AUD_exchange_rate
        else:
            return self.units * price * self.current_AUD_exchange_rate

    def calculatePercentReturns(self):
        return self.currValueAUD / self.initValueAUD * 100 - 100

def plotPieChart(labels, value):
    fig1, ax1 = plt.subplots()
    ax1.pie(value, labels=labels, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')
    plt.show()

def return_date_ISO_format(date):
    dmy = []
    start_index = 0
    for _ in range(3):
        index = date.index("/", start_index) + 1
        dmy.append(date[start_index : index])
    print(dmy)


def main(argv):

    logging.basicConfig(filename="portfolioTracker.log", encoding="utf-8", filemode="w", format="%(asctime)s - %(levelname)s: %(message)s", level=logging.DEBUG)
    portfolioDir = ''
    portValueDir = ''
    stonks = {}
    nameTickers = "AUD=X"
    initPortValue = {"All": 0, "All CPI Adj.": 0, "AUS Market": 0, "Cryptocurrency": 0, "US Market": 0}
    currPortValue = {"All": 0, "All CPI Adj.": 0, "AUS Market": 0, "Cryptocurrency": 0, "US Market": 0}
    percPortChange = {"All": 0, "All CPI Adj.": 0, "AUS Market": 0, "Cryptocurrency": 0, "US Market": 0}
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
        portfolio = pd.read_excel(portfolioDir, usecols="A:H")
        stocks = pd.DataFrame(portfolio)
        # Drops any empty values
        # stocks = stocks.dropna()
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
        if ticker.Action == "BUY":
            if ticker.Ticker in stonks:
                stonks[ticker.Ticker].dollarCostAveragingHandler(ticker.Units, ticker.Price, ticker._8, ticker.Date)
            else:
                dateOffset = len(dataDf['Adj Close'][ticker.Ticker].index) - 1
                while math.isnan(dataDf['Adj Close'][ticker.Ticker].iloc[dateOffset]):
                    dateOffset -= 1
                prevClose = dataDf['Adj Close'][ticker.Ticker].iloc[dateOffset]
                stonks[ticker.Ticker] = Security(ticker.Ticker, ticker.Units, ticker.Price, prevClose, ticker.Date, ticker._8, usdToAUD)
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
        elif ticker.Action == "DIVIDEND":
            realisedProfitLoss += stonks[ticker.Ticker].dividend_addition(ticker.Units)



    portfolioDf = {"Ticker": [], "Units Purchased": [], "Initial Price": [], "Latest Close": [], "Initial AUD Asset Value": [], "Initial AUD CPI Adj. Value" : [], "Current AUD Asset Value": [], "Percentage Returns": [], "Percentage Returns CPI Adj.": []}
    for key in sorted(stonks):
        portfolioDf["Ticker"].append(stonks[key].getTicker())
        portfolioDf["Units Purchased"].append(f"{stonks[key].getUnits():.2f}")
        portfolioDf["Initial Price"].append(f"{stonks[key].getInitPrice():.2f}")
        portfolioDf["Latest Close"].append(f"{stonks[key].getCurrPrice():.2f}")
        portfolioDf["Initial AUD Asset Value"].append(f"{stonks[key].getInitValue():.2f}")
        portfolioDf["Initial AUD CPI Adj. Value"].append(f"{stonks[key].getInitCPIAdjustedValue():.2f}")
        portfolioDf["Current AUD Asset Value"].append(f"{stonks[key].getCurrValue():.2f}")
        portfolioDf["Percentage Returns"].append(f"{stonks[key].getPercentReturns():.2f}")
        portfolioDf["Percentage Returns CPI Adj."].append(f"{stonks[key].getPercentReturnsCPIAdj():.2f}")
        initPortValue["All"] += stonks[key].getInitValue()
        initPortValue["All CPI Adj."] += stonks[key].getInitCPIAdjustedValue()
        initPortValue[stonks[key].getAssetType()] += stonks[key].getInitValue()
        currPortValue["All"] += stonks[key].getCurrValue()
        currPortValue[stonks[key].getAssetType()] += stonks[key].getCurrValue()
    percPortChange["All"] = currPortValue["All"] / initPortValue["All"] * 100 - 100
    percPortChange["All CPI Adj."] = currPortValue["All"] / initPortValue["All CPI Adj."] * 100 - 100
    percPortChange["AUS Market"] = currPortValue["AUS Market"] / initPortValue["AUS Market"] * 100 - 100
    percPortChange["Cryptocurrency"] = currPortValue["Cryptocurrency"] / initPortValue["Cryptocurrency"] * 100 - 100
    percPortChange["US Market"] = currPortValue["US Market"] / initPortValue["US Market"] * 100 - 100

    print(pd.DataFrame(portfolioDf).to_string())
    print(f"Initial Portfolio Value is: ${initPortValue['All']:.2f}")
    print(f"Initial Portfolio Value CPI Adj. is: ${initPortValue['All CPI Adj.']:.2f}")
    print(f"Current Portfolio Value is: ${currPortValue['All']:.2f}")
    print(f"Percentage Portfolio Performance: {percPortChange['All']:.2f}")
    print(f"Percentage Portfolio Performance CPI Adj.: {percPortChange['All CPI Adj.']:.2f}")
    print(f"Realised Profit/Loss: ${realisedProfitLoss:.2f}AUD\n")

    print(f"Initial Aus Market Portfolio Value is: ${initPortValue['AUS Market']:.2f}")
    print(f"Current Aus Market Portfolio Value is: ${currPortValue['AUS Market']:.2f}")
    print(f"Aus Market Percentage Portfolio Performance: {percPortChange['AUS Market']:.2f}%\n")

    print(f"Initial Cryptocurrency Portfolio Value is: ${initPortValue['Cryptocurrency']:.2f}")
    print(f"Current Cryptocurrency Portfolio Value is: ${currPortValue['Cryptocurrency']:.2f}")
    print(f"Cryptocurrency Percentage Portfolio Performance: {percPortChange['Cryptocurrency']:.2f}%\n")

    print(f"US Market Initial Portfolio Value is: ${initPortValue['US Market']:.2f}")
    print(f"US Market Current Portfolio Value is: ${currPortValue['US Market']:.2f}")
    print(f"US Market Percentage Portfolio Performance: {percPortChange['US Market']:.2f}%")

    #Find if .csv already has a value for todays date
    if csvFound:
        if portValDf.iloc[len(portValDf) - 1][0] != dt.today().strftime('%d/%m/%Y'):
            df2 = pd.DataFrame([[dt.today().strftime('%d/%m/%Y'), currPortValue["All"], percPortChange["All"]]],
                               columns=['Date', 'Value', 'Percentage'])
            # portValDf = portValDf.concat([portValDf,df2], ignore_index=True)
            portValDf = pd.concat([portValDf, df2], ignore_index=True)
        else:
            portValDf.iloc[len(portValDf) - 1, 1] = str(float("{:.2f}".format(currPortValue["All"])))
            portValDf.iloc[len(portValDf) - 1, 2] = str(float("{:.2f}".format(percPortChange["All"])))
    else:
        portValDf = pd.DataFrame([[dt.today().strftime('%d/%m/%Y'), currPortValue["All"], percPortChange["All"]]], columns=["Date", "Value", "Percentage"])
        portValDf.to_csv(portValueDir)

    if WRITE_TO_FILE:
        portValDf.to_csv(portValueDir, index=False)

    for key in stonks:
        tickerList.append(key)
        tickerValue.append(stonks[key].getCurrValue())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(32, 9))
    plt.title("Portfolio Allocation")
    ax1.pie(tickerValue, labels=tickerList, autopct='%1.1f%%')
    plt.title("Portfolio Allocation")
    ax2.pie([currPortValue["AUS Market"], currPortValue["Cryptocurrency"], currPortValue["US Market"]], labels=["Aus Market", "Cryptocurrency", "US Market"], autopct='%1.1f%%')
#    ax2.title("Portfolio Asset Class Allocation")
    plt.show()

    plt.plot_date(portValDf['Date'], portValDf['Value'], xdate=True)
    plt.title("Portfolio Performance over time")
    plt.ylabel("Portfolio Value ($)")
    plt.xlabel("Date")
    plt.tight_layout
    plt.show()

if __name__ == '__main__':
    main(sys.argv[1:])


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
    def __init__(self, ticker, units, dca_price, prevClose, init_buy_date, init_AUD_exchange_rate = 1, current_AUD_exchange_rate = 1):
        self.ticker = ticker
        self.units = units
        self.init_units = units
        self.sold_units = 0
        self.init_price = dca_price
        self.dca_price = dca_price
        self.sold_dca_price = 0
        self.curr_price = prevClose
        self.dividend_fiat_returns = 0
        self.dividend_returns = 0
        self.init_AUD_exchange_rate = init_AUD_exchange_rate
        self.current_AUD_exchange_rate = current_AUD_exchange_rate

        if self.ticker.endswith("AX"):
            self.asset_type = "AUS Market"
            self.current_AUD_exchange_rate = 1
        elif self.ticker.endswith("USD"):
            self.asset_type = "Cryptocurrency"
        else:
            self.asset_type = "US Market"

        self.init_value_AUD = self.setValueAUD(self.dca_price, "initial")
        self.init_value_CPI_Adjusted_AUD = ausdex.calc_inflation(value=self.init_value_AUD, original_date=init_buy_date, location="Brisbane")
        self.curr_value_AUD = self.setValueAUD(self.curr_price, "current")
        self.sold_value_AUD = 0
        self.percent_returns = self.calculatePercentReturns()

    def dollarCostAveragingHandler(self, units, priceBought, AUD_exchange_rate, buy_date):
        initUnits = self.units
        initPriceBought = self.dca_price
        currPrice = self.curr_price
        initValueAUD = self.init_value_AUD
        currValueAUD = self.curr_value_AUD

        self.units  = initUnits + units
        self.dca_price = (initPriceBought * initUnits + priceBought * units) / self.units
        self.init_value_AUD = initValueAUD + units * priceBought * AUD_exchange_rate
        self.init_value_CPI_Adjusted_AUD = self.init_value_CPI_Adjusted_AUD + ausdex.calc_inflation(value=units * priceBought * AUD_exchange_rate, original_date=buy_date, location="Brisbane")
        self.curr_value_AUD = currValueAUD + units * currPrice * self.current_AUD_exchange_rate
        self.percent_returns = self.calculatePercentReturns()

    def sellEventHandler(self, units, price_sold):
        if(self.units < units):
            print(f"Error: Units sold for {self.getTicker()} cannot be greater than units pre-existing in portfolio. "
                  f"Please update the portfolio spreadsheet with corrected units")
            sys.exit()
        else:
            self.units = self.units - units
            self.sold_dca_price = (self.sold_dca_price * self.sold_units + units * price_sold) / (self.sold_units + units)
            self.sold_units += units
            #TODO: Need to get aud at time of sale
            self.sold_value_AUD = self.sold_units * self.sold_dca_price * self.current_AUD_exchange_rate
            self.init_value_AUD = self.units * self.dca_price * self.init_AUD_exchange_rate
            if self.units == 0.0:
                self.init_value_AUD = self.init_units * self.init_price * self.init_AUD_exchange_rate
                self.curr_value_AUD = 0
            else:
                self.curr_value_AUD = self.units * self.curr_price * self.current_AUD_exchange_rate
        self.percent_returns = self.calculatePercentReturns()
        if price_sold:
            return (price_sold - self.dca_price) * self.units

    def dividend_addition(self, units):
        self.units = self.units + units
        self.dividend_returns += units
        self.curr_value_AUD = self.units * self.curr_price * self.current_AUD_exchange_rate
        self.percent_returns = self.calculatePercentReturns()

        return units * self.curr_price * self.current_AUD_exchange_rate

    def getTicker(self):
        return self.ticker

    def getAssetType(self):
        return self.asset_type
    
    def getUnits(self):
        return self.units

    def getInitPrice(self):
        return self.dca_price

    def getCurrPrice(self):
        return self.curr_price

    def getInitValue(self):
        return self.init_value_AUD
    
    def getInitCPIAdjustedValue(self):
        return self.init_value_CPI_Adjusted_AUD

    def getCurrValue(self):
        return self.curr_value_AUD
    
    def getDividendFiatReturns(self):
        return self.dividend_fiat_returns * self.current_AUD_exchange_rate
    
    def getDividendReturns(self):
        return self.dividend_returns * self.curr_price * self.current_AUD_exchange_rate

    def getPercentReturns(self):
        return self.percent_returns
    
    def getPercentReturnsCPIAdj(self):
        value = self.curr_value_AUD + self.sold_value_AUD + self.dividend_fiat_returns
        return value / self.init_value_CPI_Adjusted_AUD * 100 - 100

    def setValueAUD(self, price, mode):
        if mode == "initial":
            return self.units * price * self.init_AUD_exchange_rate + self.dividend_fiat_returns
        else:
            return self.units * price * self.current_AUD_exchange_rate + self.dividend_fiat_returns
    
    def setDividendFiatReturns(self, addition, usd_to_aud):
        if self.asset_type != "AUS Market":
            addition *= usd_to_aud
        self.dividend_fiat_returns += addition
        self.curr_value_AUD += addition
        self.percent_returns = self.calculatePercentReturns()

    def calculatePercentReturns(self):
        value = self.curr_value_AUD + self.sold_value_AUD + self.dividend_fiat_returns
        return value / self.init_value_AUD * 100 - 100

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

    dataDf = pd.DataFrame(yf.download(nameTickers, period="5d", prepost=True, threads=1))
    logging.debug(dataDf.to_string())
    #Get latest USD/AUD exchange rate
    #Start from the last row available, iterate back until value is not null to get latest closing value
    dateOffset = len(dataDf['Close']['AUD=X'].index) - 1
    while math.isnan(dataDf['Close']['AUD=X'].iloc[dateOffset]):
        dateOffset -= 1
    usdToAUD = dataDf['Close']['AUD=X'].iloc[dateOffset]
    #Loop through each ticker
    for ticker in stocks.itertuples():
        if ticker.Action == "BUY":
            if ticker.Ticker in stonks:
                stonks[ticker.Ticker].dollarCostAveragingHandler(ticker.Units, ticker.Price, ticker._8, ticker.Date)
            else:
                dateOffset = len(dataDf['Close'][ticker.Ticker].index) - 1
                while math.isnan(dataDf['Close'][ticker.Ticker].iloc[dateOffset]):
                    dateOffset -= 1
                prevClose = dataDf['Close'][ticker.Ticker].iloc[dateOffset]
                stonks[ticker.Ticker] = Security(ticker.Ticker, ticker.Units, ticker.Price, prevClose, ticker.Date, ticker._8, usdToAUD)
        elif ticker.Action in ("SELL", "TRANSACTION"):
            if ticker.Ticker in stonks:
                if ticker.Action == "SELL":
                    realisedProfitLoss += stonks[ticker.Ticker].sellEventHandler(ticker.Units, ticker.Price)
                else:
                    stonks[ticker.Ticker].sellEventHandler(ticker.Units, stonks[ticker.Ticker].curr_price)
            else:
                print(f"{ticker.Ticker} has not been bought prior to the sell event, please review the portfolio "
                      f"spreadsheet")
                sys.exit()
        elif ticker.Action == "DIVIDEND":
            stonks[ticker.Ticker].dividend_addition(ticker.Units)
        elif ticker.Action == "DIVIDEND-FIAT":
            stonks[ticker.Ticker].setDividendFiatReturns(ticker.Price, usdToAUD)
            realisedProfitLoss += stonks[ticker.Ticker].dividend_fiat_returns



    portfolioDf = {"Ticker": [], "Units": [], "Init. Price": [], "Close": [], "Init. AUD Value": [], "Initial AUD CPI Adj." : [], "Sold AUD Value": [], "Current AUD Value": [], "Dividends Val.": [], "Dividend Fiat": [], "% Returns": [], "% CPI Adj.": []}
    for key in sorted(stonks):
        portfolioDf["Ticker"].append(stonks[key].getTicker())
        portfolioDf["Units"].append(f"{stonks[key].getUnits():.2f}")
        portfolioDf["Init. Price"].append(f"{stonks[key].getInitPrice():.2f}")
        portfolioDf["Close"].append(f"{stonks[key].getCurrPrice():.2f}")
        portfolioDf["Init. AUD Value"].append(f"{stonks[key].getInitValue():.2f}")
        portfolioDf["Initial AUD CPI Adj."].append(f"{stonks[key].getInitCPIAdjustedValue():.2f}")
        portfolioDf["Sold AUD Value"].append(f"{stonks[key].sold_value_AUD:.2f}")
        portfolioDf["Current AUD Value"].append(f"{stonks[key].getCurrValue():.2f}")
        portfolioDf["Dividends Val."].append(f"{stonks[key].getDividendReturns():.2f}")
        portfolioDf["Dividend Fiat"].append(f"{stonks[key].getDividendFiatReturns():.2f}")
        portfolioDf["% Returns"].append(f"{stonks[key].getPercentReturns():.2f}")
        portfolioDf["% CPI Adj."].append(f"{stonks[key].getPercentReturnsCPIAdj():.2f}")
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


import pandas as pd
import yfinance as yf
import math
import matplotlib.pyplot as plt
import sys
import getopt
import logging
import openpyxl
from datetime import datetime as dt
from typing import Dict, List, Tuple, Optional, Any
import ausdex

WRITE_TO_FILE = True


class Security:
    """Represents a security/stock in the portfolio with tracking capabilities."""

    def __init__(self, ticker: str, units: float, dca_price: float, prev_close: float,
                 init_buy_date: str, init_aud_exchange_rate: float = 1.0,
                 current_aud_exchange_rate: float = 1.0) -> None:
        """
        Initialize a Security object.

        Args:
            ticker: Stock ticker symbol
            units: Number of units held
            dca_price: Dollar cost average price
            prev_close: Previous closing price
            init_buy_date: Initial buy date
            init_aud_exchange_rate: Initial AUD exchange rate
            current_aud_exchange_rate: Current AUD exchange rate
        """
        self.ticker = ticker
        self._units = units
        self.init_units = units
        self.sold_units = 0.0
        self._init_price = dca_price
        self.dca_price = dca_price
        self.sold_dca_price = 0.0
        self._curr_price = prev_close
        self._dividend_fiat_returns = 0.0
        self._dividend_returns = 0.0
        self.init_aud_exchange_rate = init_aud_exchange_rate
        self.current_aud_exchange_rate = current_aud_exchange_rate

        # Determine asset type based on ticker suffix
        if self.ticker.endswith("AX"):
            self._asset_type = "AUS Market"
            self.current_aud_exchange_rate = 1.0
        elif self.ticker.endswith("USD"):
            self._asset_type = "Cryptocurrency"
        else:
            self._asset_type = "US Market"

        self.init_value_aud = self._set_value_aud(self.dca_price, "initial")
        self.init_value_cpi_adjusted_aud = ausdex.calc_inflation(
            value=self.init_value_aud,
            original_date=init_buy_date,
            location="Brisbane"
        )
        self.curr_value_aud = self._set_value_aud(self._curr_price, "current")
        self.sold_value_aud = 0.0
        self._percent_returns = self._calculate_percent_returns()

    def dollar_cost_averaging_handler(self, units: float, price_bought: float,
                                      aud_exchange_rate: float, buy_date: str) -> None:
        """
        Handle dollar cost averaging by updating portfolio with new purchase.

        Args:
            units: Number of units purchased
            price_bought: Price per unit
            aud_exchange_rate: AUD exchange rate at time of purchase
            buy_date: Date of purchase
        """
        init_units = self.units
        init_price_bought = self.dca_price
        curr_price = self.curr_price
        init_value_aud = self.init_value_aud
        curr_value_aud = self.curr_value_aud

        self.units = init_units + units
        self.dca_price = (init_price_bought * init_units +
                          price_bought * units) / self.units
        self.init_value_aud = init_value_aud + units * price_bought * aud_exchange_rate
        self.init_value_cpi_adjusted_aud += ausdex.calc_inflation(
            value=units * price_bought * aud_exchange_rate,
            original_date=buy_date,
            location="Brisbane"
        )
        self.curr_value_aud = curr_value_aud + units * \
            curr_price * self.current_aud_exchange_rate
        self.percent_returns = self._calculate_percent_returns()

    def sell_event_handler(self, units: float, price_sold: float) -> Optional[float]:
        """
        Handle selling of units.

        Args:
            units: Number of units to sell
            price_sold: Price per unit sold

        Returns:
            Profit/loss from the sale, or None if error

        Raises:
            SystemExit: If trying to sell more units than owned
        """
        if self.units < units:
            print(f"Error: Units sold for {self.get_ticker()} cannot be greater than units "
                  f"pre-existing in portfolio. Please update the portfolio spreadsheet with corrected units")
            sys.exit(1)

        self.units = self.units - units
        self.sold_dca_price = (self.sold_dca_price * self.sold_units +
                               units * price_sold) / (self.sold_units + units)
        self.sold_units += units
        # TODO: Need to get AUD at time of sale
        self.sold_value_aud = self.sold_units * \
            self.sold_dca_price * self.current_aud_exchange_rate
        self.init_value_aud = self.units * self.dca_price * self.init_aud_exchange_rate

        if self.units == 0.0:
            self.init_value_aud = self.init_units * \
                self.init_price * self.init_aud_exchange_rate
            self.curr_value_aud = 0.0
        else:
            self.curr_value_aud = self.units * self.curr_price * self.current_aud_exchange_rate

        self.percent_returns = self._calculate_percent_returns()

        if price_sold:
            return (price_sold - self.dca_price) * self.units
        return None

    def dividend_addition(self, units: float) -> float:
        """
        Add dividend units to the security.

        Args:
            units: Number of dividend units received

        Returns:
            Value of dividend units in AUD
        """
        self.units = self.units + units
        self._dividend_returns += units
        self.curr_value_aud = self.units * self.curr_price * self.current_aud_exchange_rate
        self.percent_returns = self._calculate_percent_returns()

        return units * self.curr_price * self.current_aud_exchange_rate

    @property
    def ticker_symbol(self) -> str:
        """Get the ticker symbol."""
        return self.ticker

    @property
    def asset_type(self) -> str:
        """Get the asset type."""
        return self._asset_type

    @property
    def units(self) -> float:
        """Get the number of units held."""
        return self._units

    @units.setter
    def units(self, value: float) -> None:
        """Set the number of units held."""
        self._units = value

    @property
    def init_price(self) -> float:
        """Get the initial price."""
        return self._init_price

    @property
    def curr_price(self) -> float:
        """Get the current price."""
        return self._curr_price

    @property
    def init_value(self) -> float:
        """Get the initial value in AUD."""
        return self.init_value_aud

    @property
    def init_cpi_adjusted_value(self) -> float:
        """Get the CPI-adjusted initial value in AUD."""
        return self.init_value_cpi_adjusted_aud

    @property
    def curr_value(self) -> float:
        """Get the current value in AUD."""
        return self.curr_value_aud

    @property
    def dividend_fiat_returns_aud(self) -> float:
        """Get dividend fiat returns in AUD."""
        return self._dividend_fiat_returns * self.current_aud_exchange_rate

    @property
    def dividend_returns_aud(self) -> float:
        """Get dividend returns in AUD."""
        return self._dividend_returns * self._curr_price * self.current_aud_exchange_rate

    @property
    def percent_returns(self) -> float:
        """Get percentage returns."""
        return self._percent_returns

    @percent_returns.setter
    def percent_returns(self, value: float) -> None:
        """Set percentage returns."""
        self._percent_returns = value

    @property
    def percent_returns_cpi_adj(self) -> float:
        """Get CPI-adjusted percentage returns."""
        value = (self.curr_value_aud + self.sold_value_aud +
                 self._dividend_fiat_returns)
        return value / self.init_value_cpi_adjusted_aud * 100 - 100

    def _set_value_aud(self, price: float, mode: str) -> float:
        """Set value in AUD based on mode."""
        if mode == "initial":
            return (self.units * price * self.init_aud_exchange_rate +
                    self._dividend_fiat_returns)
        else:
            return (self.units * price * self.current_aud_exchange_rate +
                    self._dividend_fiat_returns)

    def set_dividend_fiat_returns(self, addition: float, usd_to_aud: float) -> None:
        """
        Set dividend fiat returns.

        Args:
            addition: Amount to add
            usd_to_aud: USD to AUD exchange rate
        """
        if self.asset_type != "AUS Market":
            addition *= usd_to_aud
        self._dividend_fiat_returns += addition
        self.curr_value_aud += addition
        self.percent_returns = self._calculate_percent_returns()

    def _calculate_percent_returns(self) -> float:
        """Calculate percentage returns."""
        value = (self.curr_value_aud + self.sold_value_aud +
                 self._dividend_fiat_returns)
        return value / self.init_value_aud * 100 - 100


def plot_pie_chart(labels: List[str], values: List[float]) -> None:
    """Create and display a pie chart."""
    fig1, ax1 = plt.subplots()
    ax1.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')
    plt.show()


def return_date_iso_format(date: str) -> List[str]:
    """Convert date to ISO format."""
    dmy = []
    start_index = 0
    for _ in range(3):
        index = date.index("/", start_index) + 1
        dmy.append(date[start_index:index])
    print(dmy)
    return dmy


def parse_command_line_args(argv: List[str]) -> Tuple[str, str]:
    """
    Parse command line arguments.

    Args:
        argv: Command line arguments

    Returns:
        Tuple of (portfolio_dir, port_value_dir)

    Raises:
        SystemExit: If arguments are invalid
    """
    portfolio_dir = ''
    port_value_dir = ''

    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["ifile=", "ofile="])
    except getopt.GetoptError:
        print('main.py -i <portfolio path> -o <portfolio output directory>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('main.py -i <portfolio path> -o <portfolio output directory>')
            sys.exit(0)
        elif opt in ("-i", "--ifile"):
            portfolio_dir = arg
        elif opt in ("-o", "--ofile"):
            port_value_dir = arg

    if not portfolio_dir or not port_value_dir:
        print('main.py -i <portfolio path> -o <portfolio output directory>')
        sys.exit(2)

    return portfolio_dir, port_value_dir


def load_portfolio_data(portfolio_dir: str) -> pd.DataFrame:
    """
    Load portfolio data from Excel file.

    Args:
        portfolio_dir: Path to portfolio Excel file

    Returns:
        DataFrame containing portfolio data

    Raises:
        SystemExit: If file not found
    """
    try:
        portfolio = pd.read_excel(portfolio_dir, usecols="A:H")
        stocks = pd.DataFrame(portfolio)
        logging.debug("Stock portfolio input file: %s", stocks)
        return stocks
    except FileNotFoundError:
        print(f"{portfolio_dir} not found. Require an excel spreadsheet listing transactions. "
              f"Please see script usage page")
        sys.exit(1)


def load_portfolio_value_data(port_value_dir: str) -> Tuple[pd.DataFrame, bool]:
    """
    Load portfolio value data from CSV file.

    Args:
        port_value_dir: Path to portfolio value CSV file

    Returns:
        Tuple of (DataFrame, csv_found_flag)
    """
    try:
        port_value = pd.read_csv(port_value_dir)
        port_val_df = pd.DataFrame(port_value)
        return port_val_df, True
    except FileNotFoundError:
        user_response = input(
            f"{port_value_dir} not found. Should a new csv be created? [y/n]: ")
        if user_response.lower() == "y":
            print("Creating new csv...")
            return pd.DataFrame(), False
        elif user_response.lower() == "n":
            print("Not creating a new csv, please review arguments, exiting...")
            sys.exit(1)
        else:
            print("Correct input of [y/n] not detected, exiting...")
            sys.exit(1)


def get_market_data(tickers: str) -> pd.DataFrame:
    """
    Download market data from Yahoo Finance.

    Args:
        tickers: Space-separated ticker symbols

    Returns:
        DataFrame containing market data

    Raises:
        SystemExit: If no data downloaded
    """
    data_df = pd.DataFrame(yf.download(
        tickers, period="5d", prepost=True, threads=True))
    if data_df.empty:
        logging.error("No data downloaded from yahoo finance, try again later")
        sys.exit(1)
    logging.debug(data_df.to_string())
    return data_df


def get_latest_price(data_df: pd.DataFrame, ticker: str) -> float:
    """
    Get the latest closing price for a ticker.

    Args:
        data_df: Market data DataFrame
        ticker: Ticker symbol

    Returns:
        Latest closing price
    """
    date_offset = len(data_df['Close'][ticker].index) - 1
    while math.isnan(data_df['Close'][ticker].iloc[date_offset]):
        date_offset -= 1
    return data_df['Close'][ticker].iloc[date_offset]


def process_portfolio_transactions(stocks: pd.DataFrame, data_df: pd.DataFrame,
                                   usd_to_aud: float) -> Tuple[Dict[str, Security], float]:
    """
    Process portfolio transactions and build security objects.

    Args:
        stocks: Portfolio data DataFrame
        data_df: Market data DataFrame
        usd_to_aud: USD to AUD exchange rate

    Returns:
        Tuple of (securities_dict, realised_profit_loss)
    """
    stonks: list[str, Security] = {}
    realised_profit_loss = 0.0

    for ticker in stocks.itertuples():
        if ticker.Action == "BUY":
            if ticker.Ticker in stonks:
                stonks[ticker.Ticker].dollar_cost_averaging_handler(
                    ticker.Units, ticker.Price, ticker._8, ticker.Date
                )
            else:
                prev_close = get_latest_price(data_df, ticker.Ticker)
                stonks[ticker.Ticker] = Security(
                    ticker.Ticker, ticker.Units, ticker.Price, prev_close,
                    ticker.Date, ticker._8, usd_to_aud
                )
        elif ticker.Action in ("SELL", "TRANSACTION"):
            if ticker.Ticker in stonks:
                if ticker.Action == "SELL":
                    profit_loss = stonks[ticker.Ticker].sell_event_handler(
                        ticker.Units, ticker.Price)
                    if profit_loss is not None:
                        realised_profit_loss += profit_loss
                else:
                    stonks[ticker.Ticker].sell_event_handler(
                        ticker.Units, stonks[ticker.Ticker].curr_price)
            else:
                print(f"{ticker.Ticker} has not been bought prior to the sell event, "
                      f"please review the portfolio spreadsheet")
                sys.exit(1)
        elif ticker.Action == "DIVIDEND":
            stonks[ticker.Ticker].dividend_addition(ticker.Units)
        elif ticker.Action == "DIVIDEND-FIAT":
            stonks[ticker.Ticker].set_dividend_fiat_returns(
                ticker.Price, usd_to_aud)
            realised_profit_loss += stonks[ticker.Ticker].dividend_fiat_returns_aud

    return stonks, realised_profit_loss


def calculate_portfolio_metrics(stonks: Dict[str, Security]) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    """
    Calculate portfolio metrics.

    Args:
        stonks: Dictionary of security objects

    Returns:
        Tuple of (init_port_value, curr_port_value, perc_port_change)
    """
    init_port_value = {"All": 0.0, "All CPI Adj.": 0.0, "AUS Market": 0.0,
                       "Cryptocurrency": 0.0, "US Market": 0.0}
    curr_port_value = {"All": 0.0, "All CPI Adj.": 0.0, "AUS Market": 0.0,
                       "Cryptocurrency": 0.0, "US Market": 0.0}
    perc_port_change = {"All": 0.0, "All CPI Adj.": 0.0, "AUS Market": 0.0,
                        "Cryptocurrency": 0.0, "US Market": 0.0}

    for key in sorted(stonks):
        security = stonks[key]
        init_port_value["All"] += security.init_value
        init_port_value["All CPI Adj."] += security.init_cpi_adjusted_value
        init_port_value[security.asset_type] += security.init_value
        curr_port_value["All"] += security.curr_value
        curr_port_value[security.asset_type] += security.curr_value

    # Calculate percentage changes
    perc_port_change["All"] = curr_port_value["All"] / \
        init_port_value["All"] * 100 - 100
    perc_port_change["All CPI Adj."] = curr_port_value["All"] / \
        init_port_value["All CPI Adj."] * 100 - 100
    perc_port_change["AUS Market"] = curr_port_value["AUS Market"] / \
        init_port_value["AUS Market"] * 100 - 100
    perc_port_change["Cryptocurrency"] = curr_port_value["Cryptocurrency"] / \
        init_port_value["Cryptocurrency"] * 100 - 100
    perc_port_change["US Market"] = curr_port_value["US Market"] / \
        init_port_value["US Market"] * 100 - 100

    return init_port_value, curr_port_value, perc_port_change


def create_portfolio_dataframe(stonks: Dict[str, Security]) -> pd.DataFrame:
    """
    Create portfolio summary DataFrame.

    Args:
        stonks: Dictionary of security objects

    Returns:
        DataFrame with portfolio summary
    """
    portfolio_data = {
        "Ticker": [], "Units": [], "Init. Price": [], "Close": [],
        "Init. AUD Value": [], "Initial AUD CPI Adj.": [], "Sold AUD Value": [],
        "Current AUD Value": [], "Dividends Val.": [], "Dividend Fiat": [],
        "% Returns": [], "% CPI Adj.": []
    }

    for key in sorted(stonks):
        security = stonks[key]
        portfolio_data["Ticker"].append(security.ticker_symbol)
        portfolio_data["Units"].append(f"{security.units:.2f}")
        portfolio_data["Init. Price"].append(f"{security.init_price:.2f}")
        portfolio_data["Close"].append(f"{security.curr_price:.2f}")
        portfolio_data["Init. AUD Value"].append(f"{security.init_value:.2f}")
        portfolio_data["Initial AUD CPI Adj."].append(
            f"{security.init_cpi_adjusted_value:.2f}")
        portfolio_data["Sold AUD Value"].append(
            f"{security.sold_value_aud:.2f}")
        portfolio_data["Current AUD Value"].append(
            f"{security.curr_value:.2f}")
        portfolio_data["Dividends Val."].append(
            f"{security.dividend_returns_aud:.2f}")
        portfolio_data["Dividend Fiat"].append(
            f"{security.dividend_fiat_returns_aud:.2f}")
        portfolio_data["% Returns"].append(f"{security.percent_returns:.2f}")
        portfolio_data["% CPI Adj."].append(
            f"{security.percent_returns_cpi_adj:.2f}")

    return pd.DataFrame(portfolio_data)


def update_portfolio_value_csv(port_val_df: pd.DataFrame, csv_found: bool,
                               curr_port_value: Dict[str, float],
                               perc_port_change: Dict[str, float],
                               port_value_dir: str) -> pd.DataFrame:
    """
    Update portfolio value CSV with current data.

    Args:
        port_val_df: Portfolio value DataFrame
        csv_found: Whether CSV was found
        curr_port_value: Current portfolio values
        perc_port_change: Portfolio percentage changes
        port_value_dir: Path to portfolio value CSV

    Returns:
        Updated DataFrame
    """
    today = dt.today().strftime('%d/%m/%Y')

    if csv_found:
        if port_val_df.iloc[len(port_val_df) - 1][0] != today:
            df2 = pd.DataFrame([[today, curr_port_value["All"], perc_port_change["All"]]],
                               columns=['Date', 'Value', 'Percentage'])
            port_val_df = pd.concat([port_val_df, df2], ignore_index=True)
        else:
            port_val_df.iloc[len(port_val_df) - 1,
                             1] = str(float(f"{curr_port_value['All']:.2f}"))
            port_val_df.iloc[len(port_val_df) - 1,
                             2] = str(float(f"{perc_port_change['All']:.2f}"))
    else:
        port_val_df = pd.DataFrame([[today, curr_port_value["All"], perc_port_change["All"]]],
                                   columns=["Date", "Value", "Percentage"])
        port_val_df.to_csv(port_value_dir)

    if WRITE_TO_FILE:
        port_val_df.to_csv(port_value_dir, index=False)

    return port_val_df


def create_visualizations(stonks: Dict[str, Security], curr_port_value: Dict[str, float],
                          port_val_df: pd.DataFrame) -> None:
    """
    Create and display portfolio visualizations.

    Args:
        stonks: Dictionary of security objects
        curr_port_value: Current portfolio values
        port_val_df: Portfolio value DataFrame
    """
    ticker_list = []
    ticker_value = []

    for key in stonks:
        ticker_list.append(key)
        ticker_value.append(stonks[key].curr_value)

    # Create pie charts
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(32, 9))
    fig.suptitle("Portfolio Allocation", fontsize=16)

    ax1.pie(ticker_value, labels=ticker_list, autopct='%1.1f%%')
    ax1.set_title("Individual Securities")

    ax2.pie([curr_port_value["AUS Market"], curr_port_value["Cryptocurrency"],
             curr_port_value["US Market"]],
            labels=["Aus Market", "Cryptocurrency", "US Market"], autopct='%1.1f%%')
    ax2.set_title("Asset Class Allocation")

    plt.tight_layout()
    plt.show()

    # Create performance chart
    plt.figure(figsize=(12, 6))
    plt.plot_date(port_val_df['Date'], port_val_df['Value'], xdate=True)
    plt.title("Portfolio Performance over time")
    plt.ylabel("Portfolio Value ($)")
    plt.xlabel("Date")
    plt.tight_layout()
    plt.show()


def print_portfolio_summary(portfolio_df: pd.DataFrame, init_port_value: Dict[str, float],
                            curr_port_value: Dict[str, float], perc_port_change: Dict[str, float],
                            realised_profit_loss: float) -> None:
    """
    Print portfolio summary to console.

    Args:
        portfolio_df: Portfolio DataFrame
        init_port_value: Initial portfolio values
        curr_port_value: Current portfolio values
        perc_port_change: Portfolio percentage changes
        realised_profit_loss: Realised profit/loss
    """
    print(portfolio_df.to_string())
    print(f"Initial Portfolio Value is: ${init_port_value['All']:.2f}")
    print(
        f"Initial Portfolio Value CPI Adj. is: ${init_port_value['All CPI Adj.']:.2f}")
    print(f"Current Portfolio Value is: ${curr_port_value['All']:.2f}")
    print(f"Percentage Portfolio Performance: {perc_port_change['All']:.2f}%")
    print(
        f"Percentage Portfolio Performance CPI Adj.: {perc_port_change['All CPI Adj.']:.2f}%")
    print(f"Realised Profit/Loss: ${realised_profit_loss:.2f} AUD\n")

    print(
        f"Initial Aus Market Portfolio Value is: ${init_port_value['AUS Market']:.2f}")
    print(
        f"Current Aus Market Portfolio Value is: ${curr_port_value['AUS Market']:.2f}")
    print(
        f"Aus Market Percentage Portfolio Performance: {perc_port_change['AUS Market']:.2f}%\n")

    print(
        f"Initial Cryptocurrency Portfolio Value is: ${init_port_value['Cryptocurrency']:.2f}")
    print(
        f"Current Cryptocurrency Portfolio Value is: ${curr_port_value['Cryptocurrency']:.2f}")
    print(
        f"Cryptocurrency Percentage Portfolio Performance: {perc_port_change['Cryptocurrency']:.2f}%\n")

    print(
        f"US Market Initial Portfolio Value is: ${init_port_value['US Market']:.2f}")
    print(
        f"US Market Current Portfolio Value is: ${curr_port_value['US Market']:.2f}")
    print(
        f"US Market Percentage Portfolio Performance: {perc_port_change['US Market']:.2f}%")


def main(argv: List[str]) -> None:
    """
    Main function to run the portfolio tracker.

    Args:
        argv: Command line arguments
    """
    # Setup logging
    logging.basicConfig(
        filename="portfolioTracker.log",
        encoding="utf-8",
        filemode="w",
        format="%(asctime)s - %(levelname)s: %(message)s",
        level=logging.DEBUG
    )

    # Parse command line arguments
    portfolio_dir, port_value_dir = parse_command_line_args(argv)
    logging.info("Input file is: %s", portfolio_dir)
    logging.info("Output file is: %s", port_value_dir)

    # Load data
    stocks = load_portfolio_data(portfolio_dir)
    port_val_df, csv_found = load_portfolio_value_data(port_value_dir)

    # Build ticker list for Yahoo Finance
    name_tickers = "AUD=X"
    for ticker in stocks.itertuples():
        if ticker.Ticker not in name_tickers:
            name_tickers += " " + ticker.Ticker

    # Get market data
    data_df = get_market_data(name_tickers)

    # Get latest USD/AUD exchange rate
    usd_to_aud = get_latest_price(data_df, 'AUD=X')

    # Process transactions
    stonks, realised_profit_loss = process_portfolio_transactions(
        stocks, data_df, usd_to_aud)

    # Calculate metrics
    init_port_value, curr_port_value, perc_port_change = calculate_portfolio_metrics(
        stonks)

    # Create portfolio summary
    portfolio_df = create_portfolio_dataframe(stonks)

    # Print summary
    print_portfolio_summary(portfolio_df, init_port_value, curr_port_value,
                            perc_port_change, realised_profit_loss)

    # Update CSV
    port_val_df = update_portfolio_value_csv(port_val_df, csv_found, curr_port_value,
                                             perc_port_change, port_value_dir)

    # Create visualizations
    create_visualizations(stonks, curr_port_value, port_val_df)


if __name__ == '__main__':
    main(sys.argv[1:])

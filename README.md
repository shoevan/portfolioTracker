# Portfolio Tracker

A comprehensive Python application for tracking investment portfolio performance with support for multiple asset classes, dividend tracking, and inflation-adjusted returns.

## Features

- **Multi-Asset Support**: Track Australian (AX), US, and cryptocurrency investments
- **Dollar Cost Averaging**: Automatic calculation of average purchase prices
- **Dividend Tracking**: Support for both dividend reinvestment and cash dividends
- **Inflation Adjustment**: CPI-adjusted returns using Brisbane inflation data
- **Real-time Data**: Live market data from Yahoo Finance
- **Visualization**: Interactive charts showing portfolio allocation and performance
- **Transaction History**: Excel-based transaction logging
- **Performance Tracking**: CSV-based historical performance tracking

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd portfolioTracker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python main.py -i <portfolio_file.xlsx> -o <output_file.csv>
```

### Example

```bash
python main.py -i "Stock Portfolio.xlsx" -o "Portfolio Value Tracking.csv"
```

### Command Line Arguments

- `-i, --ifile`: Path to the Excel file containing portfolio transactions
- `-o, --ofile`: Path to the CSV file for storing portfolio value history
- `-h, --help`: Display help information

## Portfolio Excel File Format

The Excel file should contain the following columns (A-H):

| Column | Description | Example |
|--------|-------------|---------|
| A | Date | 01/01/2023 |
| B | Action | BUY, SELL, DIVIDEND, DIVIDEND-FIAT, TRANSACTION |
| C | Ticker | AAPL, BHP.AX, BTC-USD |
| D | Units | 10.5 |
| E | Price | 150.25 |
| F | AUD Exchange Rate | 1.0 (for AU stocks) or 0.65 (for US stocks) |

### Action Types

- **BUY**: Purchase of securities
- **SELL**: Sale of securities at specified price
- **TRANSACTION**: Sale of securities at current market price
- **DIVIDEND**: Dividend reinvestment (units added)
- **DIVIDEND-FIAT**: Cash dividend received

### Ticker Conventions

- **Australian Stocks**: End with `.AX` (e.g., `BHP.AX`)
- **US Stocks**: Standard ticker (e.g., `AAPL`, `MSFT`)
- **Cryptocurrencies**: End with `-USD` (e.g., `BTC-USD`, `ETH-USD`)

## Output

### Console Output

The application displays:
- Detailed portfolio summary table
- Total portfolio values (initial, current, CPI-adjusted)
- Performance metrics by asset class
- Realised profit/loss

### CSV Output

The output CSV contains:
- Date
- Portfolio Value
- Percentage Change

### Visualizations

1. **Portfolio Allocation Pie Charts**:
   - Individual securities allocation
   - Asset class allocation (AU Market, US Market, Cryptocurrency)

2. **Performance Chart**:
   - Portfolio value over time

## Code Structure

### Main Components

- **Security Class**: Represents individual securities with tracking capabilities
- **Data Loading**: Excel and CSV file handling
- **Market Data**: Yahoo Finance integration
- **Calculations**: Portfolio metrics and performance calculations
- **Visualization**: Matplotlib-based charts
- **File Management**: CSV updates and logging

### Key Functions

- `parse_command_line_args()`: Command line argument parsing
- `load_portfolio_data()`: Excel file loading
- `get_market_data()`: Yahoo Finance data retrieval
- `process_portfolio_transactions()`: Transaction processing
- `calculate_portfolio_metrics()`: Performance calculations
- `create_visualizations()`: Chart generation

## Dependencies

- **pandas**: Data manipulation and analysis
- **yfinance**: Yahoo Finance data access
- **matplotlib**: Data visualization
- **openpyxl**: Excel file reading
- **ausdex**: Australian inflation data
- **numpy**: Numerical computations

## Logging

The application creates a `portfolioTracker.log` file with detailed execution information including:
- Input/output file paths
- Market data retrieval status
- Transaction processing details
- Error messages

## Error Handling

The application includes comprehensive error handling for:
- Missing input files
- Invalid command line arguments
- Market data retrieval failures
- Transaction validation errors
- File I/O operations

## Development

### Code Quality Improvements

The code has been improved with:
- Type hints for better IDE support and error detection
- Comprehensive docstrings for all functions
- Modular function design for better maintainability
- Consistent naming conventions (snake_case)
- Better error handling and logging
- Improved code organization and readability

### Future Enhancements

Potential improvements include:
- Web interface
- Real-time notifications
- Advanced analytics (Sharpe ratio, beta, etc.)
- Tax reporting features
- Multiple currency support
- API integration with other data sources

## License

This project is for educational and personal use. Please ensure compliance with relevant financial regulations and terms of service for data providers.

## Disclaimer

This software is for informational purposes only and should not be considered as financial advice. Always consult with a qualified financial advisor before making investment decisions. 
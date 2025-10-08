# core/data_feed.py
import pandas as pd
import yfinance as yf

class DataFeed:
    """Handles loading market data from different sources."""

    def __init__(self):
        self.data = None

    def load_from_csv(self, file_path: str):
        """Load historical data from a CSV file."""
        self.data = pd.read_csv(file_path, parse_dates=['Date'], index_col='Date')
        return self.data

    def load_from_yfinance(self, symbol: str, start=None, end=None, interval='1d'):
        """Fetch data from Yahoo Finance."""
        self.data = yf.download(symbol, start=start, end=end, interval=interval)
        return self.data

    def get_latest_price(self):
        """Return the most recent close price."""
        if self.data is not None:
            return self.data['Close'].iloc[-1]
        return None

    def get_data(self):
        """Return the full dataset."""
        return self.data

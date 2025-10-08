# core/indicators.py
import pandas as pd

class Indicators:
    """Handles calculation of common technical indicators."""

    @staticmethod
    def moving_average(data: pd.Series, period: int = 14):
        """Simple Moving Average (SMA)."""
        return data.rolling(window=period).mean()

    @staticmethod
    def exponential_moving_average(data: pd.Series, period: int = 14):
        """Exponential Moving Average (EMA)."""
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14):
        """Relative Strength Index (RSI)."""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(data: pd.Series, fast_period=12, slow_period=26, signal_period=9):
        """Moving Average Convergence Divergence (MACD)."""
        fast_ema = Indicators.exponential_moving_average(data, fast_period)
        slow_ema = Indicators.exponential_moving_average(data, slow_period)
        macd_line = fast_ema - slow_ema
        signal_line = Indicators.exponential_moving_average(macd_line, signal_period)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

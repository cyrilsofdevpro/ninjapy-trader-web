import pandas as pd
import numpy as np


def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """
    Calculates the Sharpe Ratio.
    :param returns: Series of percentage returns (e.g., daily %)
    :param risk_free_rate: Risk-free rate (default = 0)
    """
    excess_return = returns - risk_free_rate
    sharpe = np.sqrt(252) * (excess_return.mean() / excess_return.std())
    return round(sharpe, 3)


def calculate_drawdown(equity_curve):
    """
    Calculates the maximum drawdown from equity curve.
    :param equity_curve: Series of portfolio values over time
    """
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    return round(max_drawdown * 100, 2)  # in %


def calculate_win_rate(trades):
    """
    Calculates the win rate from a list of trade PnLs.
    :param trades: list or series of trade profit/loss values
    """
    if len(trades) == 0:
        return 0
    wins = [t for t in trades if t > 0]
    return round(len(wins) / len(trades) * 100, 2)


def summarize_performance(df):
    """
    Takes a dataframe of equity curve and trade PnLs and prints summary.
    Expected columns: ['equity', 'returns', 'trade_pnl']
    """
    sharpe = calculate_sharpe_ratio(df['returns'])
    drawdown = calculate_drawdown(df['equity'])
    win_rate = calculate_win_rate(df['trade_pnl'])

    print("\n📊 --- Performance Summary ---")
    print(f"Sharpe Ratio: {sharpe}")
    print(f"Max Drawdown: {drawdown}%")
    print(f"Win Rate: {win_rate}%")

    return {
        "Sharpe Ratio": sharpe,
        "Max Drawdown (%)": drawdown,
        "Win Rate (%)": win_rate
    }

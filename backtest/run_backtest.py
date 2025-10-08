import backtrader as bt
import pandas as pd
from core.ema_cross_strategy import EMACrossStrategy
from backtest.results.metrics import summarize_performance


def run_backtest(data_path, cash=10000, commission=0.001, strategy_kwargs=None, do_plot=False):
    """Run a backtest and return a small results dict.

    strategy_kwargs: dict passed to cerebro.addstrategy
    do_plot: if True, call cerebro.plot() (may block)
    """
    strategy_kwargs = strategy_kwargs or {}
    df = pd.read_csv(data_path, parse_dates=True, index_col='datetime')

    # Guard: ensure we have enough bars for the indicator periods used by the strategy
    try:
        required_bars = int(EMACrossStrategy.params.get('ema_period', 9))
    except Exception:
        required_bars = 9
    if len(df) < required_bars:
        print(f"Insufficient data: {len(df)} bars found but strategy requires at least {required_bars} bars for EMA({required_bars}).")
        print("Provide a longer dataset or reduce the strategy's EMA period.")
        return

    cerebro = bt.Cerebro()
    cerebro.broker.set_cash(cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.addstrategy(EMACrossStrategy, **strategy_kwargs)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    strategies = cerebro.run()
    final_value = cerebro.broker.getvalue()
    print(f"Final Portfolio Value: {final_value:.2f}")

    # Example: Simulate an equity curve for metrics (you can replace this with real backtest results)
    # If real trade-level equity is not available, synthesize a deterministic equity series
    # so the dashboard always has something to plot.
    if 'equity' not in df.columns:
        start_value = float(cash)
        # create a synthetic equity using cumulative returns of price changes scaled to cash
        pct = df['close'].pct_change().fillna(0)
        df['equity'] = start_value * (1 + pct.cumsum())
    if 'returns' not in df.columns:
        df['returns'] = df['equity'].pct_change().fillna(0)
    if 'trade_pnl' not in df.columns:
        df['trade_pnl'] = df['returns'] * float(cash)

    # 🧠 Call your metrics summary here
    results = summarize_performance(df)
    # include an equity time series (timestamp, equity) for plotting in the dashboard
    # Build a JSON-serializable equity time series (list of {datetime,equity})
    equity_series = []
    try:
        if 'equity' in df.columns:
            for idx, val in df['equity'].dropna().items():
                # idx may be Timestamp or string
                equity_series.append({'datetime': str(idx), 'equity': float(val)})
    except Exception:
        equity_series = []

    # Return a compact result dict for programmatic consumption
    ret = dict(final_value=float(final_value), metrics=results, equity=equity_series)

    if do_plot:
        try:
            cerebro.plot(style='candlestick')
        except Exception:
            pass

    return ret


if __name__ == "__main__":
    out = run_backtest("data/processed/sample_data.csv")
    print(out)

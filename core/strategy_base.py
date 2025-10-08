import backtrader as bt

class StrategyBase(bt.Strategy):
    """
    Base Strategy — handles logging, order notifications,
    and trade results so child strategies stay clean.
    """

    def log(self, txt, dt=None):
        """Unified logger."""
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt.isoformat()} — {txt}')

    def notify_order(self, order):
        """Order status notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED @ {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED @ {order.executed.price:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected')

        # Reset the current order flag
        self.order = None

    def notify_trade(self, trade):
        """Trade completion notification."""
        if not trade.isclosed:
            return
        self.log(f'PROFIT: Gross {trade.pnl:.2f}, Net {trade.pnlcomm:.2f}')

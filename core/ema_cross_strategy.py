import backtrader as bt
from core.time_range import is_in_range
from core.risk_manager import RiskManager


class EMACrossStrategy(bt.Strategy):
    """
    9 EMA breakout strategy based on time range high/low.
    Enters long when price breaks above EMA & session high.
    Enters short when price breaks below EMA & session low.
    """

    params = dict(
        ema_period=9,
        profit_target=500,
        stop_loss=-450,
        start_time="09:30",
        end_time="10:00"
    )

    def __init__(self):
        self.ema = bt.indicators.ExponentialMovingAverage(
            self.data.close, period=self.p.ema_period
        )
        self.high_level = None
        self.low_level = None
        self.risk = RiskManager(self.p.profit_target, self.p.stop_loss)
        self.in_position = False
        self.order = None

    def next(self):
        # Wait for enough data
        if len(self.data) < self.p.ema_period:
            return

        current_time = self.data.datetime.time()

        # Step 1: Capture high/low of time window
        if is_in_range(current_time, self.p.start_time, self.p.end_time):
            if self.high_level is None or self.low_level is None:
                self.high_level = self.data.high[0]
                self.low_level = self.data.low[0]
            else:
                self.high_level = max(self.high_level, self.data.high[0])
                self.low_level = min(self.low_level, self.data.low[0])

        # Step 2: Entry conditions
        if not self.position:  # only enter if no open trade
            if self.ema[0] > self.high_level:
                self.order = self.buy()
                self.in_position = True
                print(f"📈 LONG ENTRY @ {self.data.close[0]:.2f}")
            elif self.ema[0] < self.low_level:
                self.order = self.sell()
                self.in_position = True
                print(f"📉 SHORT ENTRY @ {self.data.close[0]:.2f}")

        # Step 3: Risk Management check
        if self.position:
            pnl = (self.data.close[0] - self.position.price) * self.position.size
            self.risk.check(pnl, self)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"✅ BUY EXECUTED @ {order.executed.price:.2f}")
            elif order.issell():
                print(f"✅ SELL EXECUTED @ {order.executed.price:.2f}")
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print("⚠️ Order Canceled/Margin/Rejected")

    def notify_trade(self, trade):
        if trade.isclosed:
            print(f"💰 PROFIT: {trade.pnl:.2f}")

    def stop(self):
        print("\n✅ Strategy completed.")
        print(f"Final Portfolio Value: {self.broker.getvalue():.2f}")

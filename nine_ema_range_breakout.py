"""
Backtrader strategy: Nine EMA Range Breakout
- Captures high/low of candles between a configurable time range (default 09:30-10:00)
- Enters long when EMA(9) crosses above range high; short when EMA(9) crosses below range low
- Uses currency-based stop and profit targets (defaults: stop 450, profit 500)
- If a trade hits a loss of -InitialStopLossAmount, the strategy will reverse once per day/session
- If unrealized profit >= ProfitTargetAmount, the stop is moved to BreakEvenPlus

Notes:
- This implementation assumes currency per price unit (contract_value) defaults to 1.0.
  For instruments like futures with a multiplier, set contract_value accordingly so currency->price conversions work.
- This is a backtest/signal generator; it is not a NinjaTrader strategy. Use it to validate logic or to generate signals for external execution.
"""

import argparse
import datetime as dt
import json
import urllib.request
import urllib.error
import backtrader as bt


class NineEMARangeBreakout(bt.Strategy):
    params = dict(
        range_start='09:30',
        range_end='10:00',
        profit_target=500.0,     # currency
        initial_stop_loss=450.0, # currency
        breakeven_plus=150.0,    # currency
        qty=1,
        contract_value=1.0,      # currency per price unit (set to contract multiplier if needed)
        stop_mode='currency',    # 'currency' or 'ticks'
        tick_size=0.01,
        export_signals=None,     # path to CSV to export signals
            signal_url=None,         # optional HTTP endpoint to POST signals as JSON
        allow_reversal=True,     # whether to allow one reversal
    )

    def __init__(self):
        self.ema9 = bt.ind.EMA(self.data.close, period=9)

        # parsed time of day
        h, m = [int(x) for x in self.params.range_start.split(':')]
        self.rstart = dt.time(h, m)
        h, m = [int(x) for x in self.params.range_end.split(':')]
        self.rend = dt.time(h, m)

        # per-day range
        self.range_high = None
        self.range_low = None
        self.range_captured = False
        self.current_date = None

        # order tracking
        self.entry_price = None
        self.entry_size = 0
        self.stop_order = None
        self.profit_order = None
        self.reversal_used = False
        self.stop_moved = False

    def next(self):
        dt0 = self.data.datetime.datetime(0)
        tod = dt0.time()

        # reset per-day variables on new day
        if self.current_date != dt0.date():
            self.current_date = dt0.date()
            self.range_high = None
            self.range_low = None
            self.range_captured = False
            self.reversal_used = False
            self.stop_moved = False
            self.entry_price = None
            self.entry_size = 0

        # Wait for EMA to warm up
        if len(self.data) < 9:
            return

        # accumulate range during the defined interval
        if tod >= self.rstart and tod <= self.rend:
            self.range_high = self.data.high[0] if self.range_high is None else max(self.range_high, self.data.high[0])
            self.range_low = self.data.low[0] if self.range_low is None else min(self.range_low, self.data.low[0])

        # after end time, mark captured
        if not self.range_captured and tod > self.rend:
            self.range_captured = True
            # if no bars in range, we won't trade today
            if self.range_high is None or self.range_low is None:
                return

        # only evaluate entries after range captured
        if not self.range_captured:
            return

        # if flat, look for entries
        pos = self.position
        ema_now = self.ema9[0]
        # guard previous EMA access (ensure enough bars)
        ema_prev = self.ema9[-1] if len(self.ema9) > 1 else ema_now

        # helper to convert currency amount to price delta
        def price_delta_from_currency(amount):
            # amount -> price units depending on stop_mode
            if self.params.stop_mode == 'currency':
                return amount / (self.params.contract_value * abs(self.params.qty) if self.params.qty != 0 else 1.0)
            else:
                # treat amount as ticks
                return amount * self.params.tick_size

        # signal exporter helper
        def export_signal(evt_time, event, side, price, size, reason=''):
            if not self.params.export_signals:
                # still allow HTTP POST even if CSV not configured
                pass
            else:
                try:
                    with open(self.params.export_signals, 'a', encoding='utf8') as sf:
                        sf.write(f"{evt_time.isoformat()},{event},{side},{price},{size},{reason}\n")
                except Exception as e:
                    print('Failed to write signal: ' + str(e))

            # if signal_url configured, POST JSON payload
            if self.params.signal_url:
                payload = {
                    'datetime': evt_time.isoformat(),
                    'event': event,
                    'side': side,
                    'price': price,
                    'size': size,
                    'reason': reason,
                }
                try:
                    data = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(self.params.signal_url, data=data, headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        # read response for debug purposes
                        resp_body = resp.read().decode('utf-8', errors='ignore')
                        # a simple success indicator
                        # print minimal info to not clutter output
                        print(f"Posted signal to {self.params.signal_url}: {event} {side} @ {price} -> {resp.getcode()}")
                except urllib.error.HTTPError as he:
                    print(f"HTTP error posting signal: {he.code} {he.reason}")
                except Exception as e:
                    print(f"Failed to POST signal: {e}")

        if pos.size == 0:
            # set initial orders only when entering
            # long entry
            if ema_prev <= (self.range_high or 0) and ema_now > (self.range_high or 0):
                self.buy(size=self.params.qty)
                export_signal(dt0, 'ENTRY', 'LONG', self.data.close[0], self.params.qty, 'EMA_above_range_high')

            # short entry
            elif ema_prev >= (self.range_low or 0) and ema_now < (self.range_low or 0):
                self.sell(size=self.params.qty)
                export_signal(dt0, 'ENTRY', 'SHORT', self.data.close[0], self.params.qty, 'EMA_below_range_low')

        else:
            # We have an open position; manage stop-move and reversal
            # compute unrealized PnL in currency
            # For long: (current_price - entry_price) * size * contract_value
            current_price = self.data.close[0]
            pnl = (current_price - self.entry_price) * self.entry_size * self.params.contract_value if self.entry_price is not None else 0

            # If profit target reached, move stop to BreakEvenPlus
            if not self.stop_moved and pnl >= self.params.profit_target:
                # move stop to break-even + breakeven_plus
                if self.entry_size > 0:
                    new_stop_price = self.entry_price + price_delta_from_currency(self.params.breakeven_plus)
                    # cancel old stop and place a new stop
                    if self.stop_order is not None:
                        try:
                            self.cancel(self.stop_order)
                        except Exception:
                            pass
                    self.stop_order = self.sell(exectype=bt.Order.Stop, price=new_stop_price, size=self.entry_size) if self.entry_size > 0 else None
                    export_signal(dt0, 'STOP_MOVE', 'LONG' if self.entry_size>0 else 'SHORT', new_stop_price, abs(self.entry_size), 'ProfitTargetReached')
                else:
                    new_stop_price = self.entry_price - price_delta_from_currency(self.params.breakeven_plus)
                    if self.stop_order is not None:
                        try:
                            self.cancel(self.stop_order)
                        except Exception:
                            pass
                    self.stop_order = self.buy(exectype=bt.Order.Stop, price=new_stop_price, size=abs(self.entry_size)) if self.entry_size < 0 else None
                    export_signal(dt0, 'STOP_MOVE', 'SHORT' if self.entry_size<0 else 'LONG', new_stop_price, abs(self.entry_size), 'ProfitTargetReached')
                self.stop_moved = True

            # If unrealized <= -initial_stop_loss -> reverse once
            if self.params.allow_reversal and not self.reversal_used and pnl <= -abs(self.params.initial_stop_loss):
                self.reversal_used = True
                # close current position
                if pos.size > 0:
                    self.close()
                    export_signal(dt0, 'EXIT', 'LONG', self.data.close[0], self.entry_size, 'ReversalStopExit')
                    # enter short
                    self.sell(size=self.params.qty)
                    export_signal(dt0, 'ENTRY', 'SHORT', self.data.close[0], self.params.qty, 'Reversal')
                else:
                    self.close()
                    export_signal(dt0, 'EXIT', 'SHORT', self.data.close[0], abs(self.entry_size), 'ReversalStopExit')
                    # enter long
                    self.buy(size=self.params.qty)
                    export_signal(dt0, 'ENTRY', 'LONG', self.data.close[0], self.params.qty, 'Reversal')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        # Completed
        if order.status in [order.Completed]:
            if order.isbuy() and self.entry_price is None and order.exectype == bt.Order.Market:
                # market buy entry
                self.entry_price = order.executed.price
                self.entry_size = order.executed.size
                # place stop and profit orders
                stop_price = self.entry_price - (self.params.initial_stop_loss / self.params.contract_value)
                profit_price = self.entry_price + (self.params.profit_target / self.params.contract_value)
                # stop order (for long)
                self.stop_order = self.sell(exectype=bt.Order.Stop, price=stop_price, size=self.entry_size)
                self.profit_order = self.sell(exectype=bt.Order.Limit, price=profit_price, size=self.entry_size)

            elif order.issell() and self.entry_price is None and order.exectype == bt.Order.Market:
                # market sell entry (short)
                self.entry_price = order.executed.price
                self.entry_size = -abs(order.executed.size)
                # place stop and profit orders for short
                stop_price = self.entry_price + (self.params.initial_stop_loss / self.params.contract_value)
                profit_price = self.entry_price - (self.params.profit_target / self.params.contract_value)
                self.stop_order = self.buy(exectype=bt.Order.Stop, price=stop_price, size=abs(self.entry_size))
                self.profit_order = self.buy(exectype=bt.Order.Limit, price=profit_price, size=abs(self.entry_size))

        # Canceled or Rejected
        elif order.status in [order.Canceled, order.Rejected, order.Margin]:
            # clear tracking if exit orders were canceled
            pass

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        # When a trade fully closes, clear tracking
        self.entry_price = None
        self.entry_size = 0
        # cancel any working orders
        try:
            if self.stop_order is not None:
                self.cancel(self.stop_order)
        except Exception:
            pass
        try:
            if self.profit_order is not None:
                self.cancel(self.profit_order)
        except Exception:
            pass
        self.stop_order = None
        self.profit_order = None


def run_backtest(csvfile, fromdate=None, todate=None):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(NineEMARangeBreakout)

    # CSV datetime format: 2025-10-07 09:31:00
    data = bt.feeds.GenericCSVData(
        dataname=csvfile,
        dtformat='%Y-%m-%d %H:%M:%S',
        datetime=0,
        time=-1,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        timeframe=bt.TimeFrame.Minutes,
        compression=1,
        openinterest=-1
    )

    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', help='CSV file with intraday bars (datetime,open,high,low,close,volume)')
    parser.add_argument('--range-start', default='09:30', help='Range start time (HH:MM)')
    parser.add_argument('--range-end', default='10:00', help='Range end time (HH:MM)')
    parser.add_argument('--profit-target', type=float, default=500.0, help='Profit target in currency')
    parser.add_argument('--initial-stop', type=float, default=450.0, help='Initial stop loss in currency')
    parser.add_argument('--breakeven-plus', type=float, default=150.0, help='Stop to move to when profit target reached')
    parser.add_argument('--contract-value', type=float, default=1.0, help='Currency value per price unit (contract multiplier)')
    parser.add_argument('--qty', type=int, default=1, help='Quantity per trade')
    parser.add_argument('--stop-mode', choices=['currency', 'ticks'], default='currency', help='Interpret stop/target amounts as currency or ticks')
    parser.add_argument('--tick-size', type=float, default=0.01, help='Price per tick when using ticks mode')
    parser.add_argument('--export-signals', type=str, default=None, help='Path to CSV file to append signals')
    parser.add_argument('--signal-url', type=str, default=None, help='Optional HTTP URL to POST signals as JSON')
    args = parser.parse_args()
    # Pass parameters via strategy params
    # rebuild cerebro with params
    cerebro = bt.Cerebro()
    cerebro.addstrategy(NineEMARangeBreakout,
                        range_start=args.range_start,
                        range_end=args.range_end,
                        profit_target=args.profit_target,
                        initial_stop_loss=args.initial_stop,
                        breakeven_plus=args.breakeven_plus,
                        contract_value=args.contract_value,
                        qty=args.qty,
                        stop_mode=args.stop_mode,
                        tick_size=args.tick_size,
                        export_signals=args.export_signals,
                        signal_url=args.signal_url)

    # prepare data feed
    # If the CSV contains a header line like 'datetime,open,...' GenericCSVData will try to parse it
    # and fail. Detect a header and write a temp CSV without header for the feed.
    data_path = args.csv
    try:
        # try multiple encodings (handles BOMs and UTF-16)
        try_encodings = ['utf-8-sig', 'utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1']
        first = None
        rest = None
        used_enc = None
        for enc in try_encodings:
            try:
                with open(args.csv, 'r', encoding=enc) as f:
                    first = f.readline()
                    rest = f.read()
                used_enc = enc
                break
            except Exception:
                first = None
                rest = None
                used_enc = None

        if first is None:
            raise ValueError('Unable to read CSV with supported encodings')

        # detect header if first field is non-numeric / contains letters
        first_field = first.split(',')[0].strip()
        if any(c.isalpha() for c in first_field):
            import tempfile
            tf = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', encoding='utf8')
            # write the rest of the file without the header
            tf.write(rest)
            tf.flush()
            data_path = tf.name
        else:
            # use the original path
            data_path = args.csv
    except Exception as e:
        print(f"Error preparing CSV: {e}")
        raise

    data = bt.feeds.GenericCSVData(
        dataname=data_path,
        dtformat='%Y-%m-%d %H:%M:%S',
        datetime=0,
        time=-1,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        timeframe=bt.TimeFrame.Minutes,
        compression=1,
        openinterest=-1
    )

    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

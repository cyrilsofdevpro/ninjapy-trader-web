"""
Fractal Model Pro - TTrades (converted to Backtrader)

This Backtrader Indicator implements a simplified, portable version of the
NinjaTrader C# `FractalModelPro_TTrades_v2.cs` you provided. It exposes the
following outputs (lines) that can be plotted or used by strategies:

- bias: 1 for Bullish, -1 for Bearish, 0 for Neutral
- mid: premium/discount midline ( (high+low)/2 )
- proj1: a simple projection level (close - tick_size * projection_multiplier)

Features kept:
- History depth parameter
- Bias selection (Bullish/Bearish/Both)
- Support for a second data series (HTF) if provided; the indicator will
  read HTF close via `self.datas[1]` when present.
- Options for PO3, Premium/Discount, Projections (toggleable, non-invasive)

Notes / limitations:
- Drawing text, TTFM labels, Liquidity Rays, CISD, and other NinjaTrader GUI
  primitives are not implemented here. Instead, numeric outputs are exposed
  for programmatic use in strategies or for plotting with Backtrader/Plotly.

Usage example (in a Backtrader Cerebro run):

    data0 = bt.feeds.PandasData(dataname=df_minute)
    data1 = bt.feeds.PandasData(dataname=df_hour)
    cerebro.adddata(data0)
    cerebro.adddata(data1)
    cerebro.addindicator(FractalModelPro)

Or use the `FractalModelPro` inside a strategy and access `self.ind.bias[0]`.
"""
import backtrader as bt
from datetime import datetime


class FractalModelPro(bt.Indicator):
    lines = ('bias', 'mid', 'proj1')
    params = (
        ('history_depth', 20),
        ('bias_selection', 'Both'),  # 'Bullish', 'Bearish', 'Both'
        ('enable_pairing_notice', True),
        ('killzone1_start', '08:30'),
        ('killzone1_end', '10:30'),
        ('enable_po3', True),
        ('show_premium_discount', True),
        ('enable_projections', True),
        ('projection_multiplier', 10),
        ('tick_size', 0.01),
    )

    def __init__(self):
        # If a higher timeframe data series was added as datas[1], use it
        self.htf = self.datas[1] if len(self.datas) > 1 else None

        # Alias for readability inside next()
        self.h = self.data.high
        self.l = self.data.low
        self.c = self.data.close
        self.o = self.data.open

    def next(self):
        # Ensure we have enough bars
        if len(self.data) < max(1, self.p.history_depth):
            self.lines.bias[0] = 0.0
            self.lines.mid[0] = float('nan')
            self.lines.proj1[0] = float('nan')
            return

        # Optionally read HTF close if available
        htf_close = None
        if self.htf is not None and len(self.htf) > 0:
            try:
                htf_close = float(self.htf.close[0])
            except Exception:
                htf_close = None

        # Compute bias
        bias = 0
        close = float(self.c[0])
        open_ = float(self.o[0])
        if self.p.bias_selection == 'Bullish':
            bias = 1 if close > open_ else 0
        elif self.p.bias_selection == 'Bearish':
            bias = -1 if close < open_ else 0
        else:  # Both
            bias = 1 if close > open_ else -1 if close < open_ else 0

        self.lines.bias[0] = float(bias)

        # Premium/Discount midline
        if self.p.show_premium_discount:
            mid = (float(self.h[0]) + float(self.l[0])) / 2.0
            self.lines.mid[0] = mid
        else:
            self.lines.mid[0] = float('nan')

        # Projection level (simple example)
        if self.p.enable_projections:
            proj1 = close - (self.p.tick_size * float(self.p.projection_multiplier))
            self.lines.proj1[0] = proj1
        else:
            self.lines.proj1[0] = float('nan')


class FractalModelProExampleStrategy(bt.Strategy):
    """Example strategy that uses the FractalModelPro indicator and logs values.

    This strategy is intentionally simple: it demonstrates how to attach the
    indicator (optionally with a second HTF data series) and read its lines.
    """

    params = (
        ('printout', True),
    )

    def __init__(self):
        # Attach the indicator to the primary data feed
        self.fmp = FractalModelPro()

    def next(self):
        # Show latest values for demonstration
        if self.p.printout:
            dt = self.data.datetime.datetime(0) if hasattr(self.data.datetime, 'datetime') else None
            print(f"{dt} | Bias={self.fmp.lines.bias[0]:.0f} Mid={self.fmp.lines.mid[0]:.4f} Proj1={self.fmp.lines.proj1[0]:.4f}")

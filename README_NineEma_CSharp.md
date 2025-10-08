NineEmaRangeBreakoutStrategy (NinjaTrader 8)

Overview
- C# NinjaScript strategy implementing 9 EMA breakout entries based on the high/low of a configurable time range.
- Supports currency or tick-based stops, profit target, break-even stop move, and optional single reversal on stop.

File
- NineEmaRangeBreakoutStrategy.cs — place this file into NinjaTrader's `bin\Custom\Strategies` folder or paste into the NinjaScript Editor.

How to install
1. Open NinjaTrader 8
2. Open NinjaScript Editor (New -> Strategy) and paste the contents of `NineEmaRangeBreakoutStrategy.cs`.
3. Compile (Compile button). Fix any references if required.
4. The strategy will appear in the Strategies window. Add it to a chart or enable it in the Strategies window.

Parameters
- RangeStart, RangeEnd (HH:mm) — time window to capture the day's high/low (default 09:30-10:00).
- ProfitTargetAmount, InitialStopLossAmount, BreakEvenPlus — currency values (or ticks when UseStopsInTicks=true).
- UseStopsInTicks — when true, stop/target amounts are interpreted as ticks (integer).
- TickSize — price per tick (used for converting ticks to price in custom logic; NinjaTrader typically handles tick-based stops directly).
- AllowReversal — allow a single reversal after a stop is filled.
- ResetReversalOnNewSession — reset reversal allowance each session.

Notes
- This is a starting point. For live trading, test thoroughly in simulation and add robust OCO order tagging and partial-fill handling.
- If you want, I can finish the strategy with more robust OCO logic, or port back any further improvements you make in the Python backtest.

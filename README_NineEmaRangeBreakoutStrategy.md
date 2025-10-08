NineEmaRangeBreakoutStrategy

Purpose
- NinjaTrader 8 strategy that uses the high and low of candles formed between a configurable time range (default 09:30–10:00). Entries occur when the 9 EMA crosses above the range high (long) or below the range low (short).
- Implements stop & reverse once on a loss of the configured initial stop (default 450 currency units).
- If the position reaches the configured profit target (default 500 currency units), the stop is moved to a protective BreakEven+ (default +150 currency units).

Files
- NineEmaRangeBreakoutStrategy.cs — the strategy source file.

Parameters
- RangeStart (string): start time for the range (e.g. "09:30").
- RangeEnd (string): end time for the range (e.g. "10:00").
- ProfitTargetAmount (double): profit target in currency units (default 500).
- InitialStopLossAmount (double): initial stop loss size in currency units (default 450).
- BreakEvenPlus (double): stop level (currency) when profit target reached (default 150).
- Quantity (int): number of contracts/shares per entry (default 1).

How to use
1. Copy `NineEmaRangeBreakoutStrategy.cs` into your NinjaTrader 8 `bin\Custom\Strategies` folder or add it via the NinjaScript Editor (File -> New -> Strategy) and paste the content.
2. Compile the NinjaScript (Compile button in NinjaScript Editor).
3. Open a chart or the Strategies window, add `NineEmaRangeBreakoutStrategy`, set parameters, and enable the strategy.

Notes & caveats
- The strategy uses currency-based StopLoss and ProfitTarget so it will scale to instrument price/contract multipliers differently depending on instrument and account currency.
- Reversal is allowed only once per session (single reversalUsed flag). Modify `reversalUsed` logic if you want per-day or per-instrument persistence.
- This is a starting point. For live trading, thoroughly backtest and add error handling, order tagging, and more robust stop-detection (for OCO, working orders, and partial fills).

Contact
- If you want I can refine the strategy: add tick-level stops, use price-based stops (ticks/pips), or implement ATR-based sizing.

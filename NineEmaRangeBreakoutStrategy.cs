using System;
using System.ComponentModel;
using NinjaTrader.Cbi;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class NineEmaRangeBreakoutStrategy : Strategy
    {
        // --- User inputs ---
        [NinjaScriptProperty]
        [Display(Name = "RangeStart", Order = 1, GroupName = "Parameters")]
        public string RangeStart { get; set; } = "09:30";

        [NinjaScriptProperty]
        [Display(Name = "RangeEnd", Order = 2, GroupName = "Parameters")]
        public string RangeEnd { get; set; } = "10:00";

        [NinjaScriptProperty]
        [Display(Name = "ProfitTargetAmount (currency)", Order = 3, GroupName = "Parameters")]
        public double ProfitTargetAmount { get; set; } = 500;

        [NinjaScriptProperty]
        [Display(Name = "InitialStopLossAmount (currency)", Order = 4, GroupName = "Parameters")]
        public double InitialStopLossAmount { get; set; } = 450;

        [NinjaScriptProperty]
        [Display(Name = "BreakEvenPlus (currency)", Order = 5, GroupName = "Parameters")]
        public double BreakEvenPlus { get; set; } = 150;

        [NinjaScriptProperty]
        [Display(Name = "Quantity", Order = 6, GroupName = "Parameters")]
        public int Quantity { get; set; } = 1;

    [NinjaScriptProperty]
    [Display(Name = "UseStopsInTicks", Order = 7, GroupName = "Parameters")]
    public bool UseStopsInTicks { get; set; } = false;

    [NinjaScriptProperty]
    [Display(Name = "ResetReversalOnNewSession", Order = 8, GroupName = "Parameters")]
    public bool ResetReversalOnNewSession { get; set; } = true;

    [NinjaScriptProperty]
    [Display(Name = "AllowReversal", Order = 9, GroupName = "Parameters")]
    public bool AllowReversal { get; set; } = true;

    [NinjaScriptProperty]
    [Display(Name = "TickSize", Order = 10, GroupName = "Parameters")]
    public double TickSize { get; set; } = 0.01;

        // --- Internal state ---
        private EMA ema9;
        private double rangeHigh = double.MinValue;
        private double rangeLow = double.MaxValue;
        private TimeSpan rangeStartTS;
        private TimeSpan rangeEndTS;
        private bool rangeCapturedToday = false;
        private bool reversalUsed = false;
        private bool stopMoved = false;
        private DateTime currentSessionDate = Core.Globals.MinDate;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "9 EMA cross above/below the high/low of a custom time-range with reversal on -450 and stop move on +profit";
                Name = "NineEmaRangeBreakoutStrategy";
                Calculate = Calculate.OnBarClose; // safer for breakout logic
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
            }
            else if (State == State.Configure)
            {
                // nothing to configure beyond defaults
            }
            else if (State == State.DataLoaded)
            {
                ema9 = EMA(9);

                // parse times; fall back to defaults on parse errors
                if (!TimeSpan.TryParse(RangeStart, out rangeStartTS))
                    rangeStartTS = TimeSpan.FromHours(9) + TimeSpan.FromMinutes(30);
                if (!TimeSpan.TryParse(RangeEnd, out rangeEndTS))
                    rangeEndTS = TimeSpan.FromHours(10);
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 20) return; // wait for indicators to initialize

            // Reset per-session state at first bar of session
            if (Bars.IsFirstBarOfSession || Time[0].Date != currentSessionDate)
            {
                rangeHigh = double.MinValue;
                rangeLow = double.MaxValue;
                rangeCapturedToday = false;
                if (ResetReversalOnNewSession)
                    reversalUsed = false;
                stopMoved = false;
                currentSessionDate = Time[0].Date;
            }

            // If we're inside the configured time window, accumulate high/low
            var barTime = Time[0].TimeOfDay;
            if (barTime >= rangeStartTS && barTime <= rangeEndTS)
            {
                rangeHigh = Math.Max(rangeHigh, High[0]);
                rangeLow = Math.Min(rangeLow, Low[0]);
            }

            // Once past the end time, mark that range is captured for the day
            if (!rangeCapturedToday && barTime > rangeEndTS)
            {
                // if rangeHigh/Low weren't updated (no bars in range), skip
                if (rangeHigh == double.MinValue || rangeLow == double.MaxValue)
                {
                    rangeCapturedToday = true; // nothing to trade today
                    return;
                }

                rangeCapturedToday = true;
            }

            // Only evaluate entries after the range is captured
            if (!rangeCapturedToday) return;

            // Entry logic: EMA cross above high => go long; EMA cross below low => go short
            double emaNow = ema9[0];
            double emaPrev = ema9[1];

            // If flat, look for entries
            if (Position.MarketPosition == MarketPosition.Flat)
            {
                // set initial stop and profit target
                if (UseStopsInTicks)
                {
                    // convert currency-like amounts to ticks (user supplies values as ticks when UseStopsInTicks=true)
                    SetStopLoss(CalculationMode.Ticks, (int)Math.Max(1, Math.Round(InitialStopLossAmount)));
                    SetProfitTarget(CalculationMode.Ticks, (int)Math.Max(1, Math.Round(ProfitTargetAmount)));
                }
                else
                {
                    SetStopLoss(CalculationMode.Currency, InitialStopLossAmount);
                    SetProfitTarget(CalculationMode.Currency, ProfitTargetAmount);
                }

                if (emaPrev <= rangeHigh && emaNow > rangeHigh)
                {
                    EnterLong(Quantity, "LongBreakout");
                }
                else if (emaPrev >= rangeLow && emaNow < rangeLow)
                {
                    EnterShort(Quantity, "ShortBreakout");
                }
            }

            // Manage open position: check unrealized PnL for stop-move to BreakEvenPlus
            if (Position.MarketPosition != MarketPosition.Flat && !stopMoved)
            {
                // Unrealized PnL in currency using current close price
                double unrealized = Position.GetProfitLoss(Close[0], PerformanceUnit.Currency);
                if (unrealized >= ProfitTargetAmount)
                {
                    // Move stop to BreakEvenPlus
                    if (UseStopsInTicks)
                        SetStopLoss(CalculationMode.Ticks, (int)Math.Max(1, Math.Round(BreakEvenPlus)));
                    else
                        SetStopLoss(CalculationMode.Currency, BreakEvenPlus);
                    stopMoved = true;
                }
            }

            // Immediate stop & reverse logic: if unrealized loss reaches initial stop, reverse once
            if (Position.MarketPosition != MarketPosition.Flat && AllowReversal && !reversalUsed)
            {
                double unrealizedNow = Position.GetProfitLoss(Close[0], PerformanceUnit.Currency);
                if (unrealizedNow <= -Math.Abs(InitialStopLossAmount))
                {
                    // mark reversal used
                    reversalUsed = true;

                    // Reverse: enter opposite side
                    if (Position.MarketPosition == MarketPosition.Long)
                    {
                        // Enter short to reverse
                        EnterShort(Quantity, "ReversalShort");
                    }
                    else if (Position.MarketPosition == MarketPosition.Short)
                    {
                        EnterLong(Quantity, "ReversalLong");
                    }
                }
            }
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity, MarketPosition orderMarketPosition, string orderId, DateTime time)
        {
            // Detect stop-loss fills to implement single reversal
            try
            {
                if (order == null) return;

                // Only consider filled orders
                if (order.OrderState != OrderState.Filled) return;

                // If a stop market/stop-limit order filled and it was our stop, attempt reversal
                if (AllowReversal && (order.OrderType == OrderType.StopMarket || order.OrderType == OrderType.StopLimit) && !reversalUsed)
                {
                    // Ensure this stop was associated with an exit
                    if (order.Name != null && order.Name.ToLower().Contains("stop"))
                    {
                        reversalUsed = true;

                        // Reverse position once
                        // If we are flat after the stop fill, reverse to the opposite side
                        if (Position.MarketPosition == MarketPosition.Flat)
                        {
                            // Determine last known side from order's market position
                            if (orderMarketPosition == MarketPosition.Long)
                            {
                                // We were long and got stopped -> enter short
                                EnterShort(Quantity, "ReversalShort");
                            }
                            else if (orderMarketPosition == MarketPosition.Short)
                            {
                                // We were short and got stopped -> enter long
                                EnterLong(Quantity, "ReversalLong");
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Print("OnOrderUpdate exception: " + ex.Message);
            }
        }

        protected override void OnExecution(ExecutionEventArgs e)
        {
            // optional: log executions for debug
            // Print($"Execution: {e.Order.Name} Qty={e.Quantity} Price={e.Price} {e.Order.OrderState}");
        }

        public override string ToString()
        {
            return Name;
        }
    }
}

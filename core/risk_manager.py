class RiskManager:
    """
    Handles stop-loss, profit target, and breakeven logic.
    Designed for flexible use across any strategy.
    """

    def __init__(self, stop_loss=-450, profit_target=500, breakeven_profit=150):
        self.stop_loss = stop_loss
        self.profit_target = profit_target
        self.breakeven_profit = breakeven_profit
        self.reversed_once = False
        self.entry_price = None
        self.stop_price = None

    def register_entry(self, entry_price):
        """Store entry price when a new trade is opened."""
        self.entry_price = entry_price
        self.reversed_once = False
        self.stop_price = None

    def check_stop_reverse(self, current_price, position_size):
        """
        Check if we should reverse position.
        Returns:
          - "reverse" if loss exceeds stop_loss and reversal is allowed
          - None otherwise
        """
        if self.entry_price is None:
            return None

        pnl = (current_price - self.entry_price) * (1 if position_size > 0 else -1)

        if pnl <= self.stop_loss and not self.reversed_once:
            self.reversed_once = True
            return "reverse"

        return None

    def check_breakeven_shift(self, current_price, position_size):
        """
        Checks if trade reached profit target,
        and if so, moves stop-loss to breakeven + buffer.
        Returns the new stop price or None.
        """
        if self.entry_price is None:
            return None

        pnl = (current_price - self.entry_price) * (1 if position_size > 0 else -1)

        if pnl >= self.profit_target:
            new_stop = self.entry_price + (
                self.breakeven_profit if position_size > 0 else -self.breakeven_profit
            )
            if self.stop_price is None or new_stop != self.stop_price:
                self.stop_price = new_stop
                return new_stop

        return None

    def reset(self):
        """Reset between trades."""
        self.reversed_once = False
        self.entry_price = None
        self.stop_price = None

    def check(self, pnl, strategy):
        """
        High-level check called by a strategy.
        - If pnl <= stop_loss and a reversal hasn't been used, closes current position and opens the opposite side.
        - If pnl >= profit_target, sets an internal stop_price to a breakeven+ buffer and returns that marker.

        Returns:
          'reversed' if a reversal was executed,
          'breakeven' if stop was moved,
          None otherwise.
        """
        # determine current position size if available
        try:
            pos_size = getattr(strategy.position, 'size', 0)
        except Exception:
            pos_size = 0

        # reversal on loss
        if pnl is not None and pnl <= self.stop_loss and not self.reversed_once:
            self.reversed_once = True
            # attempt to close existing position then open the opposite
            try:
                strategy.close()
            except Exception:
                pass
            try:
                if pos_size > 0:
                    strategy.sell()
                elif pos_size < 0:
                    strategy.buy()
            except Exception:
                pass
            return 'reversed'

        # breakeven move on profit
        if pnl is not None and pnl >= self.profit_target:
            # calculate new stop price (approximate, strategy may place the actual stop order)
            try:
                if pos_size > 0:
                    new_stop = self.entry_price + self.breakeven_profit
                else:
                    new_stop = self.entry_price - self.breakeven_profit
                self.stop_price = new_stop
                return 'breakeven'
            except Exception:
                return None

        return None

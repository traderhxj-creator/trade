import pandas as pd

from trade.strategies.base import Strategy


class MovingAverageCrossStrategy(Strategy):
    def __init__(self, short_window: int = 20, long_window: int = 60) -> None:
        if short_window <= 0 or long_window <= 0:
            raise ValueError("Windows must be positive integers.")
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window.")

        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, prices: pd.DataFrame) -> pd.Series:
        close = prices["close"]
        short_ma = close.rolling(self.short_window).mean()
        long_ma = close.rolling(self.long_window).mean()

        signals = pd.Series(0, index=prices.index, name="signal")
        signals[short_ma > long_ma] = 1
        return signals

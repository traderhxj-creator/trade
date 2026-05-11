import unittest

import pandas as pd

from trade.backtester import Backtester
from trade.models import BacktestConfig
from trade.strategies import MovingAverageCrossStrategy


class BacktesterTest(unittest.TestCase):
    def test_backtester_returns_equity_curve(self) -> None:
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        prices = pd.DataFrame(
            {
                "open": range(100, 200),
                "high": range(101, 201),
                "low": range(99, 199),
                "close": range(100, 200),
                "volume": [1000] * 100,
            },
            index=dates,
        )

        strategy = MovingAverageCrossStrategy(short_window=5, long_window=20)
        frame, result = Backtester(BacktestConfig(initial_cash=10_000)).run(prices, strategy)

        self.assertIn("equity", frame.columns)
        self.assertGreater(result.final_equity, 0)
        self.assertGreaterEqual(result.trades, 1)


if __name__ == "__main__":
    unittest.main()

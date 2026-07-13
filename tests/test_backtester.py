import unittest
from unittest import mock

import pandas as pd

from trade.backtester import Backtester
from trade.data import CsvPriceProvider
from trade.models import BacktestConfig
from trade.strategies import MovingAverageCrossStrategy, build_strategy, strategy_names
from trade.web import dataset_profile, list_backtest_history, list_strategy_specs, run_backtest_from_params


class BacktesterTest(unittest.TestCase):
    def make_prices(self) -> pd.DataFrame:
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        return pd.DataFrame(
            {
                "open": range(100, 200),
                "high": range(101, 201),
                "low": range(99, 199),
                "close": range(100, 200),
                "volume": [1000] * 100,
            },
            index=dates,
        )

    def test_backtester_returns_equity_curve(self) -> None:
        prices = self.make_prices()
        strategy = MovingAverageCrossStrategy(short_window=5, long_window=20)
        frame, result = Backtester(BacktestConfig(initial_cash=10_000)).run(prices, strategy)

        self.assertIn("equity", frame.columns)
        self.assertGreater(result.final_equity, 0)
        self.assertGreaterEqual(result.trades, 1)

    def test_backtester_rejects_empty_prices(self) -> None:
        strategy = MovingAverageCrossStrategy(short_window=5, long_window=20)

        with self.assertRaisesRegex(ValueError, "at least one row"):
            Backtester().run(pd.DataFrame(), strategy)

    def test_backtester_rejects_missing_close(self) -> None:
        prices = self.make_prices().drop(columns=["close"])
        strategy = MovingAverageCrossStrategy(short_window=5, long_window=20)

        with self.assertRaisesRegex(ValueError, "close column"):
            Backtester().run(prices, strategy)

    def test_config_rejects_invalid_costs(self) -> None:
        with self.assertRaisesRegex(ValueError, "commission_rate"):
            BacktestConfig(commission_rate=-0.01)

        with self.assertRaisesRegex(ValueError, "slippage_rate"):
            BacktestConfig(slippage_rate=-0.01)

    def test_config_rejects_invalid_cash(self) -> None:
        with self.assertRaisesRegex(ValueError, "initial_cash"):
            BacktestConfig(initial_cash=0)

    def test_csv_provider_filters_date_range(self) -> None:
        prices = CsvPriceProvider("data/sample_prices.csv").load(
            start="2024-01-10",
            end="2024-01-12",
        )

        self.assertEqual(len(prices), 3)
        self.assertEqual(str(prices.index.min().date()), "2024-01-10")
        self.assertEqual(str(prices.index.max().date()), "2024-01-12")

    def test_strategy_registry_builds_moving_average_strategy(self) -> None:
        strategy = build_strategy("moving_average", short_window=5, long_window=20)

        self.assertIsInstance(strategy, MovingAverageCrossStrategy)
        self.assertIn("moving_average", strategy_names())

    def test_strategy_registry_rejects_unknown_strategy(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown strategy"):
            build_strategy("missing")

    def test_web_strategy_specs_include_registered_strategy(self) -> None:
        specs = list_strategy_specs()

        self.assertEqual(specs[0]["name"], "moving_average")
        self.assertIn("label", specs[0])

    def test_web_backtest_params_support_strategy_and_date_range(self) -> None:
        with mock.patch("trade.web._append_history"):
            payload = run_backtest_from_params(
                {
                    "data": ["data/sample_prices.csv"],
                    "strategy": ["moving_average"],
                    "start": ["2024-01-10"],
                    "end": ["2024-01-12"],
                    "short_window": ["1"],
                    "long_window": ["2"],
                }
            )

        self.assertEqual(payload["meta"]["strategy"], "moving_average")
        self.assertEqual(payload["meta"]["start"], "2024-01-10")
        self.assertEqual(payload["meta"]["end"], "2024-01-12")
        self.assertEqual(payload["meta"]["rows"], 3)
        self.assertIn("report_markdown", payload)
        self.assertIn("series_csv", payload)

    def test_web_backtest_rejects_invalid_moving_average_windows(self) -> None:
        with mock.patch("trade.web._append_history"), self.assertRaisesRegex(ValueError, "short_window"):
            run_backtest_from_params(
                {
                    "data": ["data/sample_prices.csv"],
                    "short_window": ["20"],
                    "long_window": ["20"],
                }
            )

    def test_dataset_profile_summarizes_csv_data(self) -> None:
        profile = dataset_profile("data/sample_prices.csv")

        self.assertEqual(profile["data"], "data/sample_prices.csv")
        self.assertGreater(profile["rows"], 0)
        self.assertIn("buy_and_hold_return", profile)

    def test_backtest_history_reads_newest_first(self) -> None:
        fake_history = (
            '{"id": "old", "generated_at": "2024-01-01"}\n'
            '{"id": "new", "generated_at": "2024-01-02"}\n'
        )

        mocked_path = mock.MagicMock()
        mocked_path.exists.return_value = True
        mocked_path.open.return_value.__enter__.return_value = fake_history.splitlines()

        with mock.patch("trade.web.HISTORY_PATH", mocked_path):
            history = list_backtest_history(limit=2)

        self.assertEqual([item["id"] for item in history], ["new", "old"])


if __name__ == "__main__":
    unittest.main()

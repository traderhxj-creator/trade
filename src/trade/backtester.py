from typing import Optional

import pandas as pd

from trade.metrics import annual_return, max_drawdown, sharpe_ratio, total_return
from trade.models import BacktestConfig, BacktestResult
from trade.strategies.base import Strategy


class Backtester:
    def __init__(self, config: Optional[BacktestConfig] = None) -> None:
        self.config = config or BacktestConfig()

    def run(self, prices: pd.DataFrame, strategy: Strategy) -> tuple[pd.DataFrame, BacktestResult]:
        if prices.empty:
            raise ValueError("prices must contain at least one row.")
        if "close" not in prices.columns:
            raise ValueError("prices must include a close column.")

        signals = strategy.generate_signals(prices)

        frame = prices.copy()
        frame["signal"] = signals.reindex(frame.index).fillna(0).astype(int)
        frame["position"] = frame["signal"].shift(1).fillna(0)
        frame["asset_return"] = frame["close"].pct_change().fillna(0)

        position_change = frame["position"].diff().abs().fillna(frame["position"].abs())
        trading_cost = position_change * (
            self.config.commission_rate + self.config.slippage_rate
        )

        frame["strategy_return"] = frame["position"] * frame["asset_return"] - trading_cost
        frame["equity"] = self.config.initial_cash * (1 + frame["strategy_return"]).cumprod()
        frame["drawdown"] = frame["equity"] / frame["equity"].cummax() - 1

        result = BacktestResult(
            final_equity=float(frame["equity"].iloc[-1]),
            total_return=total_return(frame["equity"]),
            annual_return=annual_return(frame["equity"], self.config.annualization),
            max_drawdown=max_drawdown(frame["equity"]),
            sharpe_ratio=sharpe_ratio(frame["strategy_return"], self.config.annualization),
            trades=int(position_change.sum()),
        )
        return frame, result

from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0002
    annualization: int = 252


@dataclass(frozen=True)
class BacktestResult:
    final_equity: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: int

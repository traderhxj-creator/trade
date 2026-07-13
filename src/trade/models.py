from dataclasses import dataclass


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0002
    annualization: int = 252

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be greater than 0.")
        if self.commission_rate < 0:
            raise ValueError("commission_rate must be greater than or equal to 0.")
        if self.slippage_rate < 0:
            raise ValueError("slippage_rate must be greater than or equal to 0.")
        if self.annualization <= 0:
            raise ValueError("annualization must be greater than 0.")


@dataclass(frozen=True)
class BacktestResult:
    final_equity: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: int

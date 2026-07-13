from trade.strategies.moving_average import MovingAverageCrossStrategy
from trade.strategies.registry import (
    STRATEGY_REGISTRY,
    StrategySpec,
    available_strategies,
    build_strategy,
    strategy_names,
)

__all__ = [
    "MovingAverageCrossStrategy",
    "STRATEGY_REGISTRY",
    "StrategySpec",
    "available_strategies",
    "build_strategy",
    "strategy_names",
]

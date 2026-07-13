from dataclasses import dataclass
from typing import Callable

from trade.strategies.base import Strategy
from trade.strategies.moving_average import MovingAverageCrossStrategy


@dataclass(frozen=True)
class StrategySpec:
    name: str
    label: str
    description: str
    factory: Callable[..., Strategy]


STRATEGY_REGISTRY: dict[str, StrategySpec] = {
    "moving_average": StrategySpec(
        name="moving_average",
        label="双均线",
        description="Use short and long moving averages to switch between long and flat.",
        factory=MovingAverageCrossStrategy,
    )
}


def available_strategies() -> list[StrategySpec]:
    return list(STRATEGY_REGISTRY.values())


def strategy_names() -> list[str]:
    return list(STRATEGY_REGISTRY)


def build_strategy(name: str, **params: object) -> Strategy:
    try:
        spec = STRATEGY_REGISTRY[name]
    except KeyError as exc:
        choices = ", ".join(strategy_names())
        raise ValueError(f"Unknown strategy: {name}. Available strategies: {choices}") from exc
    return spec.factory(**params)

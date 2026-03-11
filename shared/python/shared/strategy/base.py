from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class StrategyContext:
    token_id: str
    market_price: float
    best_bid: float = 0.0
    best_ask: float = 0.0
    recent_prices: list[float] = field(default_factory=list)
    recent_sizes: list[float] = field(default_factory=list)


@dataclass
class StrategySignal:
    token_id: str
    side: str
    strength: float
    strategy: str
    estimated_prob: float
    market_price: float
    ev: float


class BaseStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def evaluate(self, context: StrategyContext) -> StrategySignal | None:
        """Return a signal if the strategy wants to trade."""

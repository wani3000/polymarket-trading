from shared.strategy.base import BaseStrategy, StrategyContext, StrategySignal


class MarketFollowStrategy(BaseStrategy):
    name = "market_follow"

    def evaluate(self, context: StrategyContext) -> StrategySignal | None:
        # Strategy logic will be implemented after the runtime and data plumbing
        # are in place. For now this marks the intended strategy boundary.
        return None

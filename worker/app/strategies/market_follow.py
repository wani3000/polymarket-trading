from shared.strategy.base import BaseStrategy, StrategyContext, StrategySignal


class MarketFollowStrategy(BaseStrategy):
    name = "market_follow"

    def evaluate(self, context: StrategyContext) -> StrategySignal | None:
        prices = context.recent_prices
        if len(prices) < 5 or context.market_price <= 0:
            return None

        short_window = prices[-3:]
        long_window = prices[-5:]
        short_avg = sum(short_window) / len(short_window)
        long_avg = sum(long_window) / len(long_window)
        trend_gap = short_avg - long_avg

        if trend_gap > 0.006:
            strength = min(trend_gap * 40, 1.0)
            estimated_prob = min(context.market_price + trend_gap * 1.6, 0.99)
            return StrategySignal(
                token_id=context.token_id,
                side="BUY",
                strength=strength,
                strategy=self.name,
                estimated_prob=estimated_prob,
                market_price=context.market_price,
                ev=max(estimated_prob - context.market_price, 0.0),
            )

        if trend_gap < -0.006:
            strength = min(abs(trend_gap) * 40, 1.0)
            estimated_prob = max(context.market_price + trend_gap * 1.2, 0.01)
            return StrategySignal(
                token_id=context.token_id,
                side="SELL",
                strength=strength,
                strategy=self.name,
                estimated_prob=estimated_prob,
                market_price=context.market_price,
                ev=max(context.market_price - estimated_prob, 0.0),
            )

        return None

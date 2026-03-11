from __future__ import annotations

from dataclasses import dataclass, field

from worker.app.market.history import PriceHistory
from worker.app.market.store import MarketStore


@dataclass
class SimulatedMarketFeed:
    """Generates deterministic price paths for local paper runtime development."""

    token_id: str = "sim-yes"
    question: str = "Will the synthetic trend continue?"
    condition_id: str = "sim-condition"
    outcome: str = "Yes"
    _tick: int = 0
    _seed_prices: list[float] = field(
        default_factory=lambda: [0.46, 0.47, 0.485, 0.501, 0.517, 0.528, 0.521, 0.514, 0.536, 0.552]
    )

    def bootstrap(self, store: MarketStore, history: PriceHistory) -> None:
        store.register_market(
            token_id=self.token_id,
            condition_id=self.condition_id,
            question=self.question,
            outcome=self.outcome,
            initial_price=self._seed_prices[0],
        )
        for price in self._seed_prices[:5]:
            store.update_best_bid_ask(self.token_id, max(price - 0.01, 0.01), min(price + 0.01, 0.99))
            history.record(self.token_id, price, 100.0)
            self._tick += 1

    def tick(self, store: MarketStore, history: PriceHistory) -> None:
        price = self._seed_prices[self._tick % len(self._seed_prices)]
        best_bid = max(round(price - 0.01, 4), 0.01)
        best_ask = min(round(price + 0.01, 4), 0.99)
        store.update_best_bid_ask(self.token_id, best_bid, best_ask)
        history.record(self.token_id, price, 100.0 + self._tick)
        self._tick += 1

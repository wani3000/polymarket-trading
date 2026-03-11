import time
from dataclasses import dataclass, field


@dataclass
class OrderBook:
    bids: list[dict] = field(default_factory=list)
    asks: list[dict] = field(default_factory=list)
    best_bid: float = 0.0
    best_ask: float = 0.0
    spread: float = 0.0


@dataclass
class MarketData:
    token_id: str = ""
    condition_id: str = ""
    question: str = ""
    outcome: str = ""
    price: float = 0.0
    last_trade_price: float = 0.0
    price_updated_at: float = 0.0
    order_book: OrderBook = field(default_factory=OrderBook)


class MarketStore:
    """In-memory cache of worker market state."""

    def __init__(self) -> None:
        self._markets: dict[str, MarketData] = {}

    def register_market(
        self,
        token_id: str,
        condition_id: str,
        question: str,
        outcome: str,
        *,
        initial_price: float = 0.5,
    ) -> None:
        self._markets[token_id] = MarketData(
            token_id=token_id,
            condition_id=condition_id,
            question=question,
            outcome=outcome,
            price=initial_price,
            last_trade_price=initial_price,
            price_updated_at=time.time(),
        )
        self.update_best_bid_ask(token_id, max(initial_price - 0.01, 0.01), min(initial_price + 0.01, 0.99))

    def get(self, token_id: str) -> MarketData | None:
        return self._markets.get(token_id)

    def all_token_ids(self) -> list[str]:
        return list(self._markets.keys())

    def update_best_bid_ask(self, token_id: str, best_bid: float, best_ask: float) -> None:
        data = self._markets.get(token_id)
        if not data:
            return
        data.order_book.best_bid = best_bid
        data.order_book.best_ask = best_ask
        data.order_book.spread = max(best_ask - best_bid, 0.0)
        data.price = round((best_bid + best_ask) / 2, 4)
        data.last_trade_price = data.price
        data.price_updated_at = time.time()

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Event

from api.app.services import bot_service
from worker.app.execution.paper_executor import PaperExecutor
from worker.app.market.history import PriceHistory
from worker.app.market.simulator import SimulatedMarketFeed
from worker.app.market.store import MarketStore
from worker.app.strategies.market_follow import MarketFollowStrategy
from shared.strategy.base import StrategyContext


@dataclass
class BotRuntime:
    bot_id: str
    run_id: str
    user_id: str
    config: dict
    strategy: MarketFollowStrategy = field(default_factory=MarketFollowStrategy)
    executor: PaperExecutor = field(init=False)
    stop_event: Event = field(default_factory=Event)
    tick_count: int = 0
    store: MarketStore = field(default_factory=MarketStore)
    history: PriceHistory = field(default_factory=PriceHistory)
    feed: SimulatedMarketFeed = field(default_factory=SimulatedMarketFeed)

    def __post_init__(self) -> None:
        self.executor = PaperExecutor(bankroll=float(self.config.get("bankroll_limit", 1000.0)))
        self.feed.bootstrap(self.store, self.history)

    def tick(self) -> None:
        """Run one evaluation cycle for this bot."""
        self.tick_count += 1
        self.feed.tick(self.store, self.history)
        self._evaluate_signals()
        now = datetime.now(UTC).isoformat()
        bot_service.update_run(
            self.run_id,
            self.user_id,
            status="running",
            last_heartbeat_at=now,
        )
        bot_service.create_event_log(
            self.run_id,
            self.user_id,
            level="INFO",
            event_type="runtime_tick",
            message=f"Runtime heartbeat {self.tick_count}",
            payload={
                "bot_id": self.bot_id,
                "strategy": self.strategy.name,
                "market_price": self.current_price,
                "paper_summary": self.executor.summary(),
            },
        )

    @property
    def current_price(self) -> float:
        data = self.store.get(self.feed.token_id)
        return data.price if data else 0.0

    def _evaluate_signals(self) -> None:
        token_id = self.feed.token_id
        market = self.store.get(token_id)
        if market is None:
            return

        self.executor.update_position_price(token_id, market.price)
        context = StrategyContext(
            token_id=token_id,
            market_price=market.price,
            best_bid=market.order_book.best_bid,
            best_ask=market.order_book.best_ask,
            recent_prices=self.history.get_prices(token_id),
            recent_sizes=self.history.get_volumes(token_id),
        )
        signal = self.strategy.evaluate(context)
        if signal is None:
            return

        if signal.side == "BUY" and token_id not in self.executor.positions:
            size = 10.0
            trade = self.executor.execute_buy(
                token_id=token_id,
                price=market.order_book.best_ask or market.price,
                size=size,
                strategy=signal.strategy,
                ev=signal.ev,
            )
            bot_service.create_event_log(
                self.run_id,
                self.user_id,
                level="INFO",
                event_type="paper_buy",
                message=f"Opened paper position on {token_id}",
                payload={
                    "price": trade.price,
                    "size": trade.size,
                    "ev": trade.ev,
                    "bankroll": self.executor.bankroll,
                },
            )
            return

        if signal.side == "SELL" and token_id in self.executor.positions:
            pnl = self.executor.execute_sell(
                token_id=token_id,
                price=market.order_book.best_bid or market.price,
            )
            bot_service.create_event_log(
                self.run_id,
                self.user_id,
                level="INFO",
                event_type="paper_sell",
                message=f"Closed paper position on {token_id}",
                payload={
                    "price": market.order_book.best_bid or market.price,
                    "pnl": round(pnl, 4),
                    "bankroll": self.executor.bankroll,
                },
            )

    def mark_started(self) -> None:
        bot_service.update_run(
            self.run_id,
            self.user_id,
            status="running",
            last_heartbeat_at=datetime.now(UTC).isoformat(),
        )
        bot_service.create_event_log(
            self.run_id,
            self.user_id,
            level="INFO",
            event_type="runtime_started",
            message="Worker runtime started",
            payload={"bot_id": self.bot_id, "strategy": self.strategy.name},
        )

    def mark_stopped(self) -> None:
        now = datetime.now(UTC).isoformat()
        bot_service.update_run(
            self.run_id,
            self.user_id,
            status="stopped",
            stopped_at=now,
            last_heartbeat_at=now,
        )
        bot_service.create_event_log(
            self.run_id,
            self.user_id,
            level="INFO",
            event_type="runtime_stopped",
            message="Worker runtime stopped",
            payload={"bot_id": self.bot_id, "ticks": self.tick_count},
        )

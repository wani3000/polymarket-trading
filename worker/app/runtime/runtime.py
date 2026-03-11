from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Event

from api.app.services import bot_service
from worker.app.execution.paper_executor import PaperExecutor
from worker.app.strategies.market_follow import MarketFollowStrategy


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

    def __post_init__(self) -> None:
        self.executor = PaperExecutor(bankroll=float(self.config.get("bankroll_limit", 1000.0)))

    def tick(self) -> None:
        """Run one evaluation cycle for this bot."""
        self.tick_count += 1
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
                "paper_summary": self.executor.summary(),
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

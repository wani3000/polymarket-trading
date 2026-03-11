from dataclasses import dataclass, field

from worker.app.strategies.market_follow import MarketFollowStrategy


@dataclass
class BotRuntime:
    bot_id: str
    strategy: MarketFollowStrategy = field(default_factory=MarketFollowStrategy)

    def tick(self) -> None:
        """Run one evaluation cycle for this bot."""
        return None

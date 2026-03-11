from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperPosition:
    token_id: str
    side: str
    size: float
    entry_price: float
    current_price: float


@dataclass
class PaperExecutor:
    bankroll: float
    positions: dict[str, PaperPosition] = field(default_factory=dict)

    def summary(self) -> dict[str, float | int]:
        unrealized = sum(
            (position.current_price - position.entry_price) * position.size
            for position in self.positions.values()
        )
        return {
            "bankroll": round(self.bankroll, 2),
            "open_positions": len(self.positions),
            "unrealized_pnl": round(unrealized, 2),
        }

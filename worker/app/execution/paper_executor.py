from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PaperTrade:
    token_id: str
    side: str
    price: float
    size: float
    strategy: str
    ev: float
    status: str = "open"
    pnl: float = 0.0


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
    trades: list[PaperTrade] = field(default_factory=list)

    def execute_buy(
        self,
        token_id: str,
        price: float,
        size: float,
        strategy: str,
        ev: float,
    ) -> PaperTrade:
        cost = price * size
        self.bankroll -= cost
        trade = PaperTrade(
            token_id=token_id,
            side="BUY",
            price=price,
            size=size,
            strategy=strategy,
            ev=ev,
        )
        self.trades.append(trade)
        self.positions[token_id] = PaperPosition(
            token_id=token_id,
            side="BUY",
            size=size,
            entry_price=price,
            current_price=price,
        )
        return trade

    def execute_sell(self, token_id: str, price: float) -> float:
        position = self.positions.pop(token_id, None)
        if position is None:
            return 0.0
        proceeds = price * position.size
        pnl = proceeds - (position.entry_price * position.size)
        self.bankroll += proceeds
        trade = PaperTrade(
            token_id=token_id,
            side="SELL",
            price=price,
            size=position.size,
            strategy="market_follow",
            ev=0.0,
            status="closed",
            pnl=pnl,
        )
        self.trades.append(trade)
        return pnl

    def update_position_price(self, token_id: str, price: float) -> None:
        position = self.positions.get(token_id)
        if position is None:
            return
        position.current_price = price

    def summary(self) -> dict[str, float | int]:
        unrealized = sum(
            (position.current_price - position.entry_price) * position.size
            for position in self.positions.values()
        )
        return {
            "bankroll": round(self.bankroll, 2),
            "open_positions": len(self.positions),
            "trades": len(self.trades),
            "unrealized_pnl": round(unrealized, 2),
        }

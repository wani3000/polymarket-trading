from pydantic import BaseModel, Field


class BotConfigModel(BaseModel):
    id: str | None = None
    name: str
    mode: str = "paper"
    strategy_type: str = "market_follow"
    bankroll_limit: float = 1000.0
    max_position_pct: float = 0.1
    max_open_positions: int = 5
    daily_loss_limit: float = 100.0


class BotRunModel(BaseModel):
    id: str
    bot_id: str
    status: str = "starting"


class PositionModel(BaseModel):
    token_id: str
    condition_id: str | None = None
    side: str
    size: float
    entry_price: float
    current_price: float = 0.0


class EventModel(BaseModel):
    type: str
    message: str
    payload: dict = Field(default_factory=dict)

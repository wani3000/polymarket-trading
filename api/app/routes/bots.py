from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.app.dependencies import current_session
from api.app.services import bot_service
from worker.app.runtime.service import get_runtime_manager

router = APIRouter()


class BotConfigRequest(BaseModel):
    name: str
    mode: str = "paper"
    strategy_type: str = "market_follow"
    bankroll_limit: float = 1000.0
    max_position_pct: float = 0.1
    max_open_positions: int = 5
    daily_loss_limit: float = 100.0


class BotConfigPatch(BaseModel):
    name: str | None = None
    mode: str | None = None
    strategy_type: str | None = None
    bankroll_limit: float | None = None
    max_position_pct: float | None = None
    max_open_positions: int | None = None
    daily_loss_limit: float | None = None
    status: str | None = None


@router.get("")
def list_bots(session: dict[str, str] = Depends(current_session)) -> dict[str, list]:
    return {"items": bot_service.list_bots(session["user_id"])}


@router.post("")
def create_bot(
    request: BotConfigRequest,
    session: dict[str, str] = Depends(current_session),
) -> dict:
    return bot_service.create_bot(session["user_id"], request.model_dump())


@router.get("/{bot_id}")
def get_bot(bot_id: str, session: dict[str, str] = Depends(current_session)) -> dict:
    bot = bot_service.get_bot(bot_id, session["user_id"])
    if bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    return bot


@router.patch("/{bot_id}")
def update_bot(
    bot_id: str,
    request: BotConfigPatch,
    session: dict[str, str] = Depends(current_session),
) -> dict:
    bot = bot_service.update_bot(
        bot_id,
        session["user_id"],
        request.model_dump(exclude_none=True),
    )
    if bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    return bot


@router.post("/{bot_id}/start")
def start_bot(bot_id: str, session: dict[str, str] = Depends(current_session)) -> dict:
    bot = bot_service.get_bot(bot_id, session["user_id"])
    if bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    runtime_manager = get_runtime_manager()
    existing_runtime = runtime_manager.get_runtime(bot_id)
    if existing_runtime:
        latest_run = bot_service.get_run(existing_runtime["run_id"], session["user_id"])
        return {
            "bot_id": bot_id,
            "status": "already_running",
            "run": latest_run or existing_runtime,
        }

    bot_service.update_bot(bot_id, session["user_id"], {"status": "active"})
    run = bot_service.create_run(bot_id, session["user_id"], "starting")
    runtime_result = runtime_manager.start_runtime(
        bot_id=bot_id,
        run_id=run["id"],
        user_id=session["user_id"],
        config=bot,
    )
    return {"bot_id": bot_id, "status": runtime_result["status"], "run": run}


@router.post("/{bot_id}/stop")
def stop_bot(bot_id: str, session: dict[str, str] = Depends(current_session)) -> dict:
    bot = bot_service.get_bot(bot_id, session["user_id"])
    if bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    bot_service.update_bot(bot_id, session["user_id"], {"status": "paused"})
    runtime_result = get_runtime_manager().stop_runtime(bot_id)
    latest_run = bot_service.get_latest_run_for_bot(bot_id, session["user_id"])
    if latest_run and runtime_result["status"] != "not_running":
        bot_service.update_run(latest_run["id"], session["user_id"], status="stopping")
        latest_run = bot_service.get_run(latest_run["id"], session["user_id"])
    return {"bot_id": bot_id, "status": runtime_result["status"], "run": latest_run}

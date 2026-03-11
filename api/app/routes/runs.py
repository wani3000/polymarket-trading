from fastapi import APIRouter, Depends, HTTPException, status

from api.app.dependencies import current_session
from api.app.services import bot_service

router = APIRouter()

@router.get("")
def list_runs(session: dict[str, str] = Depends(current_session)) -> dict[str, list]:
    return {"items": bot_service.list_runs(session["user_id"])}


@router.get("/{run_id}")
def get_run(run_id: str, session: dict[str, str] = Depends(current_session)) -> dict:
    run = bot_service.get_run(run_id, session["user_id"])
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return run


@router.get("/{run_id}/events")
def get_run_events(run_id: str, session: dict[str, str] = Depends(current_session)) -> dict[str, list]:
    run = bot_service.get_run(run_id, session["user_id"])
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return {"items": bot_service.list_events(run_id, session["user_id"])}

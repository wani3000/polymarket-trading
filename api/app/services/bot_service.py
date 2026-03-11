from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from api.app.db.session import connection_scope


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def list_bots(user_id: str) -> list[dict]:
    with connection_scope() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, name, mode, strategy_type, bankroll_limit,
                   max_position_pct, max_open_positions, daily_loss_limit,
                   status, created_at, updated_at
            FROM bot_configs
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_bot(bot_id: str, user_id: str) -> dict | None:
    with connection_scope() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, name, mode, strategy_type, bankroll_limit,
                   max_position_pct, max_open_positions, daily_loss_limit,
                   status, created_at, updated_at
            FROM bot_configs
            WHERE id = ? AND user_id = ?
            """,
            (bot_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def create_bot(user_id: str, payload: dict) -> dict:
    bot_id = str(uuid.uuid4())
    now = _utcnow_iso()
    data = {
        "id": bot_id,
        "user_id": user_id,
        "name": payload["name"],
        "mode": payload["mode"],
        "strategy_type": payload["strategy_type"],
        "bankroll_limit": payload["bankroll_limit"],
        "max_position_pct": payload["max_position_pct"],
        "max_open_positions": payload["max_open_positions"],
        "daily_loss_limit": payload["daily_loss_limit"],
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }

    with connection_scope() as conn:
        conn.execute(
            """
            INSERT INTO bot_configs (
                id, user_id, name, mode, strategy_type, bankroll_limit,
                max_position_pct, max_open_positions, daily_loss_limit,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["user_id"],
                data["name"],
                data["mode"],
                data["strategy_type"],
                data["bankroll_limit"],
                data["max_position_pct"],
                data["max_open_positions"],
                data["daily_loss_limit"],
                data["status"],
                data["created_at"],
                data["updated_at"],
            ),
        )

    return data


def update_bot(bot_id: str, user_id: str, payload: dict) -> dict | None:
    current = get_bot(bot_id, user_id)
    if current is None:
        return None

    merged = {**current, **payload, "updated_at": _utcnow_iso()}
    with connection_scope() as conn:
        conn.execute(
            """
            UPDATE bot_configs
            SET name = ?, mode = ?, strategy_type = ?, bankroll_limit = ?,
                max_position_pct = ?, max_open_positions = ?, daily_loss_limit = ?,
                status = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                merged["name"],
                merged["mode"],
                merged["strategy_type"],
                merged["bankroll_limit"],
                merged["max_position_pct"],
                merged["max_open_positions"],
                merged["daily_loss_limit"],
                merged["status"],
                merged["updated_at"],
                bot_id,
                user_id,
            ),
        )
    return get_bot(bot_id, user_id)


def create_run(bot_id: str, user_id: str, status: str) -> dict:
    run_id = str(uuid.uuid4())
    started_at = _utcnow_iso()
    with connection_scope() as conn:
        conn.execute(
            """
            INSERT INTO bot_runs (id, bot_id, user_id, status, started_at, stopped_at, last_heartbeat_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?)
            """,
            (run_id, bot_id, user_id, status, started_at, started_at),
        )
    return {
        "id": run_id,
        "bot_id": bot_id,
        "user_id": user_id,
        "status": status,
        "started_at": started_at,
        "stopped_at": None,
        "last_heartbeat_at": started_at,
    }


def list_runs(user_id: str) -> list[dict]:
    with connection_scope() as conn:
        rows = conn.execute(
            """
            SELECT id, bot_id, user_id, status, started_at, stopped_at, last_heartbeat_at
            FROM bot_runs
            WHERE user_id = ?
            ORDER BY started_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_run(run_id: str, user_id: str) -> dict | None:
    with connection_scope() as conn:
        row = conn.execute(
            """
            SELECT id, bot_id, user_id, status, started_at, stopped_at, last_heartbeat_at
            FROM bot_runs
            WHERE id = ? AND user_id = ?
            """,
            (run_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def update_run(
    run_id: str,
    user_id: str,
    *,
    status: str | None = None,
    stopped_at: str | None = None,
    last_heartbeat_at: str | None = None,
) -> dict | None:
    current = get_run(run_id, user_id)
    if current is None:
        return None

    merged = {
        **current,
        "status": status or current["status"],
        "stopped_at": stopped_at if stopped_at is not None else current["stopped_at"],
        "last_heartbeat_at": last_heartbeat_at or current["last_heartbeat_at"],
    }
    with connection_scope() as conn:
        conn.execute(
            """
            UPDATE bot_runs
            SET status = ?, stopped_at = ?, last_heartbeat_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                merged["status"],
                merged["stopped_at"],
                merged["last_heartbeat_at"],
                run_id,
                user_id,
            ),
        )
    return get_run(run_id, user_id)


def get_latest_run_for_bot(bot_id: str, user_id: str) -> dict | None:
    with connection_scope() as conn:
        row = conn.execute(
            """
            SELECT id, bot_id, user_id, status, started_at, stopped_at, last_heartbeat_at
            FROM bot_runs
            WHERE bot_id = ? AND user_id = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (bot_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def create_event_log(
    run_id: str,
    user_id: str,
    *,
    level: str,
    event_type: str,
    message: str,
    payload: dict | None = None,
) -> dict:
    event_id = str(uuid.uuid4())
    created_at = _utcnow_iso()
    row = {
        "id": event_id,
        "run_id": run_id,
        "user_id": user_id,
        "level": level,
        "type": event_type,
        "message": message,
        "payload_json": json.dumps(payload or {}),
        "created_at": created_at,
    }
    with connection_scope() as conn:
        conn.execute(
            """
            INSERT INTO event_logs (id, run_id, user_id, level, type, message, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["run_id"],
                row["user_id"],
                row["level"],
                row["type"],
                row["message"],
                row["payload_json"],
                row["created_at"],
            ),
        )
    return row


def list_events(run_id: str, user_id: str) -> list[dict]:
    with connection_scope() as conn:
        rows = conn.execute(
            """
            SELECT id, run_id, user_id, level, type, message, payload_json, created_at
            FROM event_logs
            WHERE run_id = ? AND user_id = ?
            ORDER BY created_at DESC
            """,
            (run_id, user_id),
        ).fetchall()
    return [dict(row) for row in rows]

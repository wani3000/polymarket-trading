from api.app.db.session import get_connection


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_nonces (
                wallet_address TEXT PRIMARY KEY,
                nonce TEXT NOT NULL,
                message TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bot_configs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                mode TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                bankroll_limit REAL NOT NULL,
                max_position_pct REAL NOT NULL,
                max_open_positions INTEGER NOT NULL,
                daily_loss_limit REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bot_runs (
                id TEXT PRIMARY KEY,
                bot_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                stopped_at TEXT
            );

            CREATE TABLE IF NOT EXISTS event_logs (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                level TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        _ensure_column(conn, "bot_runs", "last_heartbeat_at", "TEXT")
        conn.commit()
    finally:
        conn.close()


def _ensure_column(conn, table_name: str, column_name: str, column_type: str) -> None:
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {column[1] for column in columns}
    if column_name in existing:
        return
    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from api.app.config import settings


def get_connection() -> sqlite3.Connection:
    settings.database_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_file)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection_scope() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

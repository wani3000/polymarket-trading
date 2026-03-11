from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from eth_account import Account
from eth_account.messages import encode_defunct

from api.app.config import settings
from api.app.db.session import connection_scope


class AuthError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


def issue_nonce(wallet_address: str) -> dict[str, str]:
    normalized = wallet_address.lower()
    nonce = secrets.token_urlsafe(24)
    message = (
        "Polymarket Trader login\n"
        f"Wallet: {normalized}\n"
        f"Nonce: {nonce}"
    )
    now = _utcnow()
    expires_at = now + timedelta(minutes=10)

    with connection_scope() as conn:
        conn.execute(
            """
            INSERT INTO auth_nonces (wallet_address, nonce, message, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(wallet_address) DO UPDATE SET
                nonce=excluded.nonce,
                message=excluded.message,
                expires_at=excluded.expires_at,
                created_at=excluded.created_at
            """,
            (normalized, nonce, message, expires_at.isoformat(), now.isoformat()),
        )

    return {
        "wallet_address": normalized,
        "nonce": nonce,
        "message": message,
        "expires_at": expires_at.isoformat(),
    }


def verify_signature(wallet_address: str, signature: str, message: str) -> dict[str, str]:
    normalized = wallet_address.lower()
    now = _utcnow()

    with connection_scope() as conn:
        nonce_row = conn.execute(
            """
            SELECT wallet_address, nonce, message, expires_at
            FROM auth_nonces
            WHERE wallet_address = ?
            """,
            (normalized,),
        ).fetchone()

        if nonce_row is None:
            raise AuthError("No active nonce for wallet.")

        expires_at = datetime.fromisoformat(nonce_row["expires_at"])
        if expires_at < now:
            raise AuthError("Nonce expired.")

        if nonce_row["message"] != message:
            raise AuthError("Signed message does not match issued nonce.")

        recovered = Account.recover_message(
            encode_defunct(text=message),
            signature=signature,
        ).lower()
        if recovered != normalized:
            raise AuthError("Signature does not match wallet address.")

        user_row = conn.execute(
            "SELECT id, wallet_address FROM users WHERE wallet_address = ?",
            (normalized,),
        ).fetchone()
        if user_row is None:
            user_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO users (id, wallet_address, created_at)
                VALUES (?, ?, ?)
                """,
                (user_id, normalized, now.isoformat()),
            )
        else:
            user_id = user_row["id"]

        token = secrets.token_urlsafe(32)
        session_expires_at = now + timedelta(hours=settings.session_ttl_hours)
        conn.execute(
            """
            INSERT INTO sessions (token, user_id, wallet_address, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                token,
                user_id,
                normalized,
                session_expires_at.isoformat(),
                now.isoformat(),
            ),
        )
        conn.execute("DELETE FROM auth_nonces WHERE wallet_address = ?", (normalized,))

    return {
        "wallet_address": normalized,
        "session": token,
        "user_id": user_id,
        "expires_at": session_expires_at.isoformat(),
    }


def get_session(token: str) -> dict[str, str] | None:
    now = _utcnow()

    with connection_scope() as conn:
        row = conn.execute(
            """
            SELECT token, user_id, wallet_address, expires_at
            FROM sessions
            WHERE token = ?
            """,
            (token,),
        ).fetchone()
        if row is None:
            return None

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < now:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None

        return {
            "token": row["token"],
            "user_id": row["user_id"],
            "wallet_address": row["wallet_address"],
            "expires_at": row["expires_at"],
        }


def revoke_session(token: str) -> None:
    with connection_scope() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

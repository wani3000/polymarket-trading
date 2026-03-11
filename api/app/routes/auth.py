from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.app.dependencies import current_session
from api.app.services.auth_service import (
    AuthError,
    issue_nonce as issue_nonce_service,
    revoke_session,
    verify_signature as verify_signature_service,
)

router = APIRouter()


class NonceRequest(BaseModel):
    wallet_address: str


class VerifyRequest(BaseModel):
    wallet_address: str
    signature: str
    message: str


@router.post("/nonce")
def issue_nonce(request: NonceRequest) -> dict[str, str]:
    return issue_nonce_service(request.wallet_address)


@router.post("/verify")
def verify_signature(request: VerifyRequest) -> dict[str, str]:
    try:
        return verify_signature_service(
            request.wallet_address,
            request.signature,
            request.message,
        )
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.get("/me")
def me(session: dict[str, str] = Depends(current_session)) -> dict[str, str]:
    return session


@router.post("/logout")
def logout(session: dict[str, str] = Depends(current_session)) -> dict[str, str]:
    revoke_session(session["token"])
    return {"status": "ok"}

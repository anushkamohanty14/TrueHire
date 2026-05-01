from typing import Optional
from fastapi import Header, HTTPException


def require_token(authorization: Optional[str] = Header(None)) -> str:
    """FastAPI dependency — extracts and validates a Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization: Bearer <token> header required",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token is empty")
    return token

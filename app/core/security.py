from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from app.core.config import settings
from fastapi import HTTPException


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


async def sign_jwt(payload: dict[str, str]) -> str:
    """
    Sign a JWT with an expiration time based on settings.jwt_expiration_minutes.
    """
    deep_copy_payload = payload.copy()
    deep_copy_payload["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expiration_minutes
    )
    return jwt.encode(
        deep_copy_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


async def verify_jwt(token: str) -> dict:
    """
    Decode and verify a JWT, raising HTTP 401 on expiration or invalid token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

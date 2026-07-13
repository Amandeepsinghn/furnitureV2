from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.deps.database import get_db
from app.core.security import verify_jwt
from app.db.schemas import User

bearer_scheme = HTTPBearer()


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Dependency used to:
    - Declare HTTP Bearer auth in OpenAPI (so Swagger shows the Authorize button)
    - Validate the JWT and return its decoded payload.
    """
    token = credentials.credentials
    payload = await verify_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


async def get_current_user(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> User:
    user_id = payload.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    return user

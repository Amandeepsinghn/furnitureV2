from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_jwt

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

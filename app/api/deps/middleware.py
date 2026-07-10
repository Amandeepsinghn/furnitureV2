from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import verify_jwt


def _auth_error_response(status_code: int, detail: str | dict | list) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Global request middleware that:
    - Skips authentication for public paths (docs, health, login, etc.)
    - Requires a valid Bearer JWT on all other routes
    - Attaches the decoded token payload to request.state.payload
    - Returns a JSON error response when authentication fails
    """

    async def dispatch(self, request: Request, call_next):
        # Allow unauthenticated access to docs and other public endpoints
        public_paths = {
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
            "/applier/health",
            "/auth/login",
        }
        if request.url.path in public_paths:
            return await call_next(request)

        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return _auth_error_response(401, "Not authenticated")

        token = authorization.split(" ", 1)[1]
        try:
            payload = await verify_jwt(token)
        except HTTPException as exc:
            return _auth_error_response(exc.status_code, exc.detail)

        request.state.payload = payload
        return await call_next(request)

import logging
from collections.abc import Awaitable, Callable

import anyio
from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.firebase_token import verify_id_token

logger = logging.getLogger(__name__)


def _path_requires_auth(p: str) -> bool:
    if p == "/api/v1/users/me":
        return True
    if p == "/api/v1/graphs" or p.startswith("/api/v1/graphs/"):
        return True
    if p == "/api/v1/payment/create-order":
        return True
    if p == "/api/v1/evaluate":
        return True
    if p == "/api/v1/interview/start" or p == "/api/v1/interview/respond":
        return True
    if p == "/api/v1/simulate/incident":
        return True
    if p == "/api/v1/generate-system":
        return True
    return False


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    """
    - Paths that require auth: must send a valid Firebase ID token (Bearer).
    - Other paths: if Bearer is sent, it is verified; invalid token -> 401.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        p = path.rstrip("/") or "/"
        if p == "/api/v1/payment/webhook":
            return await call_next(request)

        auth_header = request.headers.get("authorization")
        token = _extract_bearer(auth_header)
        required = _path_requires_auth(p)

        if required and not token:
            return JSONResponse(
                {"detail": "Authentication required"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if token:
            try:
                decoded = await anyio.to_thread.run_sync(verify_id_token, token)
            except Exception as exc:
                logger.info("firebase.token_invalid", extra={"error": str(exc)})
                return JSONResponse(
                    {"detail": "Invalid or expired token"},
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            request.state.firebase_uid = decoded["uid"]
            request.state.firebase_claims = decoded

        return await call_next(request)

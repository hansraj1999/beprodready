import logging
from typing import Any

from firebase_admin import auth as firebase_auth

from app.core.config import settings

logger = logging.getLogger(__name__)


def verify_id_token(id_token: str) -> dict[str, Any]:
    """
    Verify a Firebase ID token (blocking). Call from a thread pool in async code.
    """
    return firebase_auth.verify_id_token(
        id_token,
        check_revoked=settings.FIREBASE_CHECK_REVOKED,
    )

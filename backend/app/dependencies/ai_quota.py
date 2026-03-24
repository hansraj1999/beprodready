"""FastAPI dependency: block free-tier users who exceeded monthly AI usage."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services import ai_quota_service


async def require_ai_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Paid (active pro / lifetime) users pass through.
    Free users must be under FREE_AI_CALLS_MONTHLY_LIMIT for the current UTC month.
    """
    if ai_quota_service.user_has_unlimited_ai(current_user):
        return current_user

    limit = settings.FREE_AI_CALLS_MONTHLY_LIMIT
    used = await ai_quota_service.count_ai_calls_this_utc_month(db, current_user.id)
    if used >= limit:
        nxt = ai_quota_service.utc_next_month_start()
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ai_quota_exceeded",
                "message": (
                    f"Free plan allows {limit} AI calls per calendar month (UTC). "
                    "Upgrade to Pro or Lifetime for unlimited AI."
                ),
                "limit": limit,
                "used": used,
                "resets_at": nxt.isoformat(),
            },
        )
    return current_user

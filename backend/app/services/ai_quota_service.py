"""
Plan-based AI usage: paid users (active pro, lifetime) are unlimited.
Free (and expired pro) users share a monthly cap counted in `usage_events`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.plan import Plan
from app.models.usage import Usage
from app.models.user import User
from app.services import usage_service

logger = logging.getLogger(__name__)

AI_USAGE_ACTION = "ai.call"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_month_start(reference: datetime | None = None) -> datetime:
    ref = reference or utc_now()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    else:
        ref = ref.astimezone(timezone.utc)
    return ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def utc_next_month_start(reference: datetime | None = None) -> datetime:
    start = utc_month_start(reference)
    if start.month == 12:
        return start.replace(year=start.year + 1, month=1)
    return start.replace(month=start.month + 1)


def user_has_unlimited_ai(user: User, now: datetime | None = None) -> bool:
    """Lifetime and non-expired Pro plans have unlimited AI features."""
    now = now or utc_now()
    if user.plan == Plan.lifetime.value:
        return True
    if user.plan != Plan.pro.value:
        return False
    vt = user.valid_till
    if vt is None:
        return True
    if vt.tzinfo is None:
        vt = vt.replace(tzinfo=timezone.utc)
    else:
        vt = vt.astimezone(timezone.utc)
    return vt > now


async def count_ai_calls_this_utc_month(
    db: AsyncSession,
    user_id: UUID,
    since: datetime | None = None,
) -> int:
    start = since or utc_month_start()
    result = await db.execute(
        select(func.count())
        .select_from(Usage)
        .where(
            Usage.user_id == user_id,
            Usage.action == AI_USAGE_ACTION,
            Usage.created_at >= start,
        )
    )
    return int(result.scalar_one())


async def record_ai_call(
    db: AsyncSession,
    *,
    user_id: UUID,
    feature: str,
    graph_id: UUID | None = None,
) -> None:
    await usage_service.record_usage(
        db,
        action=AI_USAGE_ACTION,
        user_id=user_id,
        graph_id=graph_id,
        metadata={"feature": feature},
    )
    await db.flush()
    logger.info(
        "ai_quota.recorded",
        extra={"user_id": str(user_id), "feature": feature},
    )

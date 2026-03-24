import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage import Usage

logger = logging.getLogger(__name__)


async def record_usage(
    db: AsyncSession,
    *,
    action: str,
    user_id: UUID | None = None,
    graph_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> Usage:
    row = Usage(
        user_id=user_id,
        graph_id=graph_id,
        action=action,
        extra=metadata,
    )
    db.add(row)
    await db.flush()
    logger.info(
        "usage.recorded",
        extra={
            "action": action,
            "user_id": str(user_id) if user_id else None,
            "graph_id": str(graph_id) if graph_id else None,
        },
    )
    return row

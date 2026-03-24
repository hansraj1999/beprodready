from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UsageCreate(BaseModel):
    user_id: UUID | None = None
    graph_id: UUID | None = None
    action: str = Field(..., min_length=1, max_length=128)
    metadata: dict[str, Any] | None = None


class UsageRead(BaseModel):
    id: UUID
    user_id: UUID | None
    graph_id: UUID | None
    action: str
    metadata: dict[str, Any] | None
    created_at: datetime

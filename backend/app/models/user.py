from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.graph import Graph
    from app.models.interview_session import InterviewSession
    from app.models.payment_ledger import PaymentLedger
    from app.models.usage import Usage


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[Optional[str]] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    firebase_uid: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, index=True
    )
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    valid_till: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    graphs: Mapped[List["Graph"]] = relationship(
        "Graph", back_populates="owner", cascade="all, delete-orphan"
    )
    usage_events: Mapped[List["Usage"]] = relationship(
        "Usage", back_populates="user"
    )
    payments: Mapped[List["PaymentLedger"]] = relationship(
        "PaymentLedger",
        back_populates="user",
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_firebase_uid(db: AsyncSession, firebase_uid: str) -> User | None:
    result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    return result.scalar_one_or_none()


async def get_or_create_firebase_user(
    db: AsyncSession, firebase_uid: str, claims: dict[str, Any]
) -> User:
    user = await get_user_by_firebase_uid(db, firebase_uid)
    email = claims.get("email")
    if isinstance(email, str):
        email = email.strip() or None
    name = claims.get("name")
    if isinstance(name, str):
        name = name.strip() or None

    if user is not None:
        changed = False
        if email is not None and user.email != email:
            user.email = email
            changed = True
        if name is not None and user.display_name != name:
            user.display_name = name
            changed = True
        if changed:
            await db.commit()
            await db.refresh(user)
        return user

    user = User(firebase_uid=firebase_uid, email=email, display_name=name)
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
        logger.info(
            "user.provisioned_firebase",
            extra={"user_id": str(user.id), "firebase_uid": firebase_uid},
        )
    except IntegrityError:
        await db.rollback()
        existing = await get_user_by_firebase_uid(db, firebase_uid)
        if existing is not None:
            return existing
        raise

    return user


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    user = User(
        email=str(payload.email) if payload.email else None,
        display_name=payload.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("user.created", extra={"user_id": str(user.id)})
    return user

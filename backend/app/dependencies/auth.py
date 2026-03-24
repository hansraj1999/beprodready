from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services import user_service


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    uid = getattr(request.state, "firebase_uid", None)
    if not uid:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    claims = getattr(request.state, "firebase_claims", None) or {}
    user = await user_service.get_or_create_firebase_user(db, uid, claims)
    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    uid = getattr(request.state, "firebase_uid", None)
    if not uid:
        return None
    claims = getattr(request.state, "firebase_claims", None) or {}
    return await user_service.get_or_create_firebase_user(db, uid, claims)

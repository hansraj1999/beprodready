from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.ai_quota import require_ai_quota
from app.models.user import User
from app.services import ai_quota_service
from app.schemas.interview import (
    InterviewRespondRequest,
    InterviewRespondResponse,
    InterviewStartResponse,
)
from app.services import interview_service

router = APIRouter()


@router.post("/start", response_model=InterviewStartResponse)
async def start_interview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ai_quota),
) -> InterviewStartResponse:
    try:
        out = await interview_service.start_interview(db, current_user.id)
    except interview_service.InterviewLLMError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Interview model error",
        )
    await ai_quota_service.record_ai_call(
        db, user_id=current_user.id, feature="interview_start"
    )
    await db.commit()
    return out


@router.post("/respond", response_model=InterviewRespondResponse)
async def respond_interview(
    body: InterviewRespondRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ai_quota),
) -> InterviewRespondResponse:
    try:
        out = await interview_service.respond_interview(
            db,
            current_user.id,
            body.session_id,
            body.answer,
        )
    except interview_service.InterviewNotFoundError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Interview session not found",
        )
    except interview_service.InterviewLLMError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Interview model error",
        )
    await ai_quota_service.record_ai_call(
        db, user_id=current_user.id, feature="interview_respond"
    )
    await db.commit()
    return out

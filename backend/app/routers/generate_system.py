import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.ai_quota import require_ai_quota
from app.models.user import User
from app.schemas.generate_system import GenerateSystemRequest, GenerateSystemResponse
from app.services import ai_quota_service
from app.services.generate_system_service import GenerateSystemError, generate_system_from_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=GenerateSystemResponse,
    summary="Generate system design graph from text",
)
async def generate_system(
    body: GenerateSystemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ai_quota),
) -> GenerateSystemResponse:
    logger.info(
        "generate_system.request",
        extra={"user_id": str(current_user.id), "prompt_len": len(body.prompt)},
    )
    try:
        out = await generate_system_from_prompt(body.prompt)
    except GenerateSystemError as exc:
        if exc.code == "llm_error":
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Upstream model error",
            ) from exc
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=exc.message or "Generation failed",
        ) from exc

    await ai_quota_service.record_ai_call(
        db, user_id=current_user.id, feature="generate_system"
    )
    await db.commit()
    return out

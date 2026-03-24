import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.ai_quota import require_ai_quota
from app.evaluation.exceptions import EvaluationFailed
from app.evaluation.providers.factory import get_llm_provider
from app.evaluation.providers.protocol import LLMProvider
from app.evaluation.service import evaluate_graph, safe_preview_for_logs
from app.models.user import User
from app.schemas.evaluation import EvaluateRequest, EvaluateResponse
from app.services import ai_quota_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _llm_provider_dep() -> LLMProvider:
    return get_llm_provider()


@router.post("", response_model=EvaluateResponse)
async def evaluate(
    body: EvaluateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ai_quota),
    provider: LLMProvider = Depends(_llm_provider_dep),
) -> EvaluateResponse:
    logger.info(
        "evaluate.request",
        extra={
            "user_id": str(current_user.id),
            "graph_preview": safe_preview_for_logs(body),
            "provider": provider.name,
        },
    )
    try:
        result = await evaluate_graph(body, provider)
    except EvaluationFailed as exc:
        if exc.code == "llm_provider_error":
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Upstream model error",
            ) from exc
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Evaluation failed",
        ) from exc

    await ai_quota_service.record_ai_call(
        db, user_id=current_user.id, feature="evaluate"
    )
    await db.commit()
    return result

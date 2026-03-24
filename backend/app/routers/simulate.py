import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.ai_quota import require_ai_quota
from app.models.user import User
from app.schemas.simulation import SimulateIncidentRequest, SimulateIncidentResponse
from app.services import ai_quota_service
from app.services import simulation_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/incident", response_model=SimulateIncidentResponse)
async def simulate_incident(
    body: SimulateIncidentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_ai_quota),
) -> SimulateIncidentResponse:
    logger.info(
        "simulate.incident.request",
        extra={
            "user_id": str(current_user.id),
            "nodes": len(body.nodes),
            "edges": len(body.edges),
        },
    )
    try:
        out = await simulation_service.simulate_incident(body.nodes, body.edges)
    except simulation_service.SimulationLLMError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Incident simulation model error",
        )
    await ai_quota_service.record_ai_call(
        db, user_id=current_user.id, feature="simulate_incident"
    )
    await db.commit()
    return out

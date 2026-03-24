import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.razorpay_signature import verify_webhook_signature
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.payment import CreateOrderRequest, CreateOrderResponse
from app.services import payment_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
) -> CreateOrderResponse:
    try:
        data = await payment_service.create_order(
            user_id=current_user.id,
            plan=body.plan,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "free_plan_not_purchasable":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="This plan is not purchasable",
            ) from exc
        if code == "unsupported_plan":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Unsupported plan",
            ) from exc
        if code == "razorpay_orders_not_configured":
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payments are not configured",
            ) from exc
        if code == "razorpay_order_failed":
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Could not create payment order",
            ) from exc
        raise
    return CreateOrderResponse(**data)


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if not settings.razorpay_webhook_configured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured",
        )

    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    if not signature:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature",
        )

    if not verify_webhook_signature(body, signature, settings.RAZORPAY_WEBHOOK_SECRET):
        logger.warning("payment.webhook.bad_signature")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    await payment_service.handle_webhook_body(db, body)
    return {"status": "ok"}

import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import anyio
import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payment_ledger import PaymentLedger
from app.models.plan import Plan
from app.models.user import User

logger = logging.getLogger(__name__)

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def _amount_paise_for_plan(plan: Plan) -> int:
    if plan == Plan.pro:
        return settings.RAZORPAY_PRO_AMOUNT_PAISE
    if plan == Plan.lifetime:
        return settings.RAZORPAY_LIFETIME_AMOUNT_PAISE
    raise ValueError("unsupported_plan")


async def create_order(*, user_id: uuid.UUID, plan: Plan) -> dict[str, Any]:
    if plan == Plan.free:
        raise ValueError("free_plan_not_purchasable")
    if not settings.razorpay_orders_configured:
        raise ValueError("razorpay_orders_not_configured")

    amount = _amount_paise_for_plan(plan)
    receipt = f"r{uuid.uuid4().hex}"[:40]
    notes = {
        "user_id": str(user_id),
        "plan": plan.value,
    }

    def _create() -> dict[str, Any]:
        basic = base64.b64encode(
            f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()
        ).decode("ascii")
        payload = {
            "amount": amount,
            "currency": settings.RAZORPAY_CURRENCY,
            "receipt": receipt,
            "notes": {k: str(v) for k, v in notes.items()},
        }
        with httpx.Client(
            base_url=RAZORPAY_API_BASE,
            timeout=30.0,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/json",
            },
        ) as client:
            response = client.post("/orders", json=payload)
            response.raise_for_status()
            return response.json()

    try:
        order = await anyio.to_thread.run_sync(_create)
    except httpx.HTTPStatusError as exc:
        logger.error(
            "payment.order_http_error",
            extra={
                "status": exc.response.status_code,
                "body": (exc.response.text or "")[:500],
            },
        )
        raise ValueError("razorpay_order_failed") from exc
    except httpx.RequestError as exc:
        logger.error("payment.order_network_error", extra={"error": str(exc)})
        raise ValueError("razorpay_order_failed") from exc

    return {
        "order_id": order["id"],
        "amount": int(order["amount"]),
        "currency": order["currency"],
        "key_id": settings.RAZORPAY_KEY_ID,
        "plan": plan.value,
    }


def _parse_payment_entity(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("event") != "payment.captured":
        return None
    payment_wrap = (payload.get("payload") or {}).get("payment") or {}
    entity = payment_wrap.get("entity")
    if not isinstance(entity, dict):
        return None
    if entity.get("status") != "captured":
        return None
    return entity


def _notes_from_payment(entity: dict[str, Any]) -> dict[str, str]:
    raw = entity.get("notes") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if v is None:
            continue
        out[str(k)] = str(v)
    return out


def _payment_timestamp(entity: dict[str, Any]) -> datetime:
    ts = entity.get("created_at")
    if ts is not None:
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    return datetime.now(timezone.utc)


def _apply_plan_to_user(user: User, plan: Plan, payment_time: datetime) -> None:
    if plan == Plan.lifetime:
        user.plan = Plan.lifetime.value
        user.valid_till = None
        return

    if plan != Plan.pro:
        return

    if user.plan == Plan.lifetime.value:
        return

    user.plan = Plan.pro.value
    base = payment_time
    current_end = user.valid_till
    if current_end is not None and current_end.tzinfo is None:
        current_end = current_end.replace(tzinfo=timezone.utc)
    if current_end and current_end > base:
        start_extend = current_end
    else:
        start_extend = base
    user.valid_till = start_extend + timedelta(days=settings.RAZORPAY_PRO_VALIDITY_DAYS)


async def handle_webhook_payload(db: AsyncSession, payload: dict[str, Any]) -> None:
    entity = _parse_payment_entity(payload)
    if entity is None:
        logger.debug(
            "payment.webhook.skipped",
            extra={"event": payload.get("event")},
        )
        return

    payment_id = entity.get("id")
    order_id = str(entity.get("order_id") or "")
    if not payment_id or not order_id:
        logger.warning("payment.webhook.missing_ids")
        return

    existing = await db.execute(
        select(PaymentLedger).where(
            PaymentLedger.razorpay_payment_id == str(payment_id)
        )
    )
    if existing.scalar_one_or_none() is not None:
        return

    notes = _notes_from_payment(entity)
    user_id_raw = notes.get("user_id")
    plan_raw = notes.get("plan")
    if not user_id_raw or not plan_raw:
        logger.warning("payment.webhook.missing_notes")
        return

    try:
        user_uuid = uuid.UUID(user_id_raw)
        target_plan = Plan(plan_raw)
    except ValueError:
        logger.warning("payment.webhook.invalid_notes")
        return

    if target_plan == Plan.free:
        return

    amount = int(entity.get("amount") or 0)
    currency = str(entity.get("currency") or "").upper()
    if currency != settings.RAZORPAY_CURRENCY.upper():
        logger.warning(
            "payment.webhook.currency_mismatch",
            extra={"currency": currency},
        )
        return

    expected = _amount_paise_for_plan(target_plan)
    if amount != expected:
        logger.warning(
            "payment.webhook.amount_mismatch",
            extra={"amount": amount, "expected": expected},
        )
        return

    user_result = await db.execute(select(User).where(User.id == user_uuid))
    user = user_result.scalar_one_or_none()
    if user is None:
        logger.warning(
            "payment.webhook.user_not_found",
            extra={"user_id": user_id_raw},
        )
        return

    payment_time = _payment_timestamp(entity)

    ledger = PaymentLedger(
        razorpay_payment_id=str(payment_id),
        razorpay_order_id=order_id,
        user_id=user.id,
        plan=target_plan.value,
        amount_paise=amount,
        currency=currency,
    )
    db.add(ledger)

    _apply_plan_to_user(user, target_plan, payment_time)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.info(
            "payment.webhook.duplicate_payment",
            extra={"payment_id": str(payment_id)},
        )
        return

    logger.info(
        "payment.webhook.applied",
        extra={
            "payment_id": str(payment_id),
            "user_id": str(user.id),
            "plan": target_plan.value,
        },
    )


async def handle_webhook_body(db: AsyncSession, body: bytes) -> None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("payment.webhook.invalid_json")
        return
    if not isinstance(payload, dict):
        return
    await handle_webhook_payload(db, payload)

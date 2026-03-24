from pydantic import BaseModel, Field

from app.models.plan import Plan


class CreateOrderRequest(BaseModel):
    plan: Plan = Field(
        ...,
        description="Paid plan to purchase (amount is resolved server-side).",
    )


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    plan: str

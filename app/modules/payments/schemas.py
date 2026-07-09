from pydantic import BaseModel, Field
from uuid import UUID


class PaymentRequest(BaseModel):
    consultation_id: UUID
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", max_length=3)
    payment_method: str | None = Field(default=None, max_length=50)
    idempotency_key: str = Field(min_length=1, max_length=255)


class PaymentResponse(BaseModel):
    id: UUID
    consultation_id: UUID
    amount: float
    currency: str
    status: str
    payment_method: str | None


class RefundRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)

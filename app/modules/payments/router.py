from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import require_role
from app.modules.payments.schemas import PaymentRequest, RefundRequest
from app.modules.payments.service import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("")
async def process_payment(
    body: PaymentRequest,
    current_user: dict = Depends(require_role("patient")),
    session: AsyncSession = Depends(get_session),
):
    return await payment_service.process_payment(
        session,
        patient_id=current_user["id"],
        consultation_id=body.consultation_id,
        amount=body.amount,
        currency=body.currency,
        idempotency_key=body.idempotency_key,
        payment_method=body.payment_method,
    )


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: str,
    body: RefundRequest = RefundRequest(),
    current_user: dict = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    return await payment_service.refund_payment(
        session, UUID(payment_id), body.reason,
    )

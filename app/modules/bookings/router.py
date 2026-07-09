from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user, require_role
from app.modules.bookings.schemas import BookingRequest, CancelBookingRequest
from app.modules.bookings.service import booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("")
async def book_slot(
    body: BookingRequest,
    current_user: dict = Depends(require_role("patient")),
    session: AsyncSession = Depends(get_session),
):
    return await booking_service.book_slot(
        session,
        patient_id=current_user["id"],
        doctor_id=body.doctor_id,
        slot_id=body.slot_id,
        idempotency_key=body.idempotency_key,
        symptoms=body.symptoms,
    )


@router.post("/{consultation_id}/cancel")
async def cancel_booking(
    consultation_id: str,
    body: CancelBookingRequest = CancelBookingRequest(),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await booking_service.cancel_booking(
        session,
        consultation_id=UUID(consultation_id),
        user_id=current_user["id"],
        role=current_user["role"],
        reason=body.reason,
    )

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictException, NotFoundException
from app.modules.consultations.models import Consultation, ConsultationStatus
from app.modules.doctors.models import AvailabilitySlot
from app.modules.doctors.repository import doctor_repository


class BookingService:
    async def book_slot(
        self, session: AsyncSession, patient_id: UUID,
        doctor_id: UUID, slot_id: UUID,
        idempotency_key: str, symptoms: str | None = None,
    ) -> dict:
        doctor = await doctor_repository.get_by_id(session, doctor_id)
        if not doctor:
            raise NotFoundException("Doctor not found")

        slot = await session.execute(
            select(AvailabilitySlot).where(
                AvailabilitySlot.id == slot_id,
                AvailabilitySlot.doctor_id == doctor_id,
                ~AvailabilitySlot.is_booked,
            ).with_for_update()
        )
        slot = slot.scalar_one_or_none()
        if not slot:
            raise ConflictException("Slot is not available or already booked")

        consultation = Consultation(
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            status=ConsultationStatus.PENDING_PAYMENT,
            idempotency_key=idempotency_key,
            symptoms=symptoms,
        )
        session.add(consultation)

        slot.is_booked = True
        slot.version += 1

        await session.flush()

        return {
            "consultation_id": consultation.id,
            "status": consultation.status,
            "doctor_id": doctor_id,
            "patient_id": patient_id,
            "slot_id": slot_id,
        }

    async def cancel_booking(
        self, session: AsyncSession, consultation_id: UUID,
        user_id: UUID, role: str, reason: str | None = None,
    ) -> dict:
        result = await session.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            raise NotFoundException("Consultation not found")

        if role == "patient" and consultation.patient_id != user_id:
            raise ConflictException("You can only cancel your own bookings")

        if role == "doctor":
            doctor = await doctor_repository.get_by_user_id(session, user_id)
            if not doctor or consultation.doctor_id != doctor.id:
                raise ConflictException("You can only cancel your own consultations")

        if consultation.status in (ConsultationStatus.COMPLETED, ConsultationStatus.CANCELLED):
            raise ConflictException(f"Cannot cancel a {consultation.status} consultation")

        consultation.status = ConsultationStatus.CANCELLED
        if consultation.slot:
            consultation.slot.is_booked = False
            consultation.slot.version += 1

        return {
            "consultation_id": consultation.id,
            "status": consultation.status,
        }


booking_service = BookingService()

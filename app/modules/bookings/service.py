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
        ip_address: str | None = None, user_agent: str | None = None,
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

        from app.modules.audit.service import audit_service
        await audit_service.log_action(
            session, user_id=patient_id, action="created", entity_type="consultation",
            entity_id=str(consultation.id),
            new_values={"doctor_id": str(doctor_id), "slot_id": str(slot_id), "status": consultation.status},
            ip_address=ip_address, user_agent=user_agent,
        )

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
        ip_address: str | None = None, user_agent: str | None = None,
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

        old_status = consultation.status
        consultation.status = ConsultationStatus.CANCELLED
        if consultation.slot:
            consultation.slot.is_booked = False
            consultation.slot.version += 1

        from app.modules.audit.service import audit_service
        await audit_service.log_action(
            session, user_id=user_id, action="cancelled", entity_type="consultation",
            entity_id=str(consultation.id),
            old_values={"status": old_status},
            new_values={"status": ConsultationStatus.CANCELLED, "reason": reason},
            ip_address=ip_address, user_agent=user_agent,
        )

        return {
            "consultation_id": consultation.id,
            "status": consultation.status,
        }


booking_service = BookingService()

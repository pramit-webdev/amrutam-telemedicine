from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictException, NotFoundException
from app.modules.consultations.models import Consultation, ConsultationStatus
from app.modules.doctors.repository import doctor_repository


class ConsultationService:
    async def get_by_id(self, session: AsyncSession, consultation_id: UUID) -> dict:
        result = await session.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            raise NotFoundException("Consultation not found")
        return self._to_dict(consultation)

    async def list_for_patient(
        self, session: AsyncSession, patient_id: UUID,
    ) -> list[dict]:
        result = await session.execute(
            select(Consultation).where(
                Consultation.patient_id == patient_id
            ).order_by(Consultation.created_at.desc())
        )
        return [self._to_dict(c) for c in result.scalars().all()]

    async def list_for_doctor(
        self, session: AsyncSession, user_id: UUID,
    ) -> list[dict]:
        doctor = await doctor_repository.get_by_user_id(session, user_id)
        if not doctor:
            raise NotFoundException("Doctor profile not found")
        result = await session.execute(
            select(Consultation).where(
                Consultation.doctor_id == doctor.id
            ).order_by(Consultation.created_at.desc())
        )
        return [self._to_dict(c) for c in result.scalars().all()]

    async def start_consultation(
        self, session: AsyncSession, consultation_id: UUID,
        doctor_user_id: UUID, notes: str | None = None,
    ) -> dict:
        doctor = await doctor_repository.get_by_user_id(session, doctor_user_id)
        if not doctor:
            raise NotFoundException("Doctor profile not found")

        result = await session.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            raise NotFoundException("Consultation not found")
        if consultation.doctor_id != doctor.id:
            raise ConflictException("This consultation is not assigned to you")
        if consultation.status != ConsultationStatus.CONFIRMED:
            raise ConflictException(
                f"Cannot start consultation in status: {consultation.status}"
            )

        consultation.status = ConsultationStatus.IN_PROGRESS
        consultation.started_at = datetime.now(UTC)
        if notes:
            consultation.notes = notes

        return self._to_dict(consultation)

    async def complete_consultation(
        self, session: AsyncSession, consultation_id: UUID,
        doctor_user_id: UUID, notes: str | None = None,
    ) -> dict:
        doctor = await doctor_repository.get_by_user_id(session, doctor_user_id)
        if not doctor:
            raise NotFoundException("Doctor profile not found")

        result = await session.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            raise NotFoundException("Consultation not found")
        if consultation.doctor_id != doctor.id:
            raise ConflictException("This consultation is not assigned to you")
        if consultation.status != ConsultationStatus.IN_PROGRESS:
            raise ConflictException(
                f"Cannot complete consultation in status: {consultation.status}"
            )

        consultation.status = ConsultationStatus.COMPLETED
        consultation.ended_at = datetime.now(UTC)
        if notes:
            consultation.notes = notes

        return self._to_dict(consultation)

    def _to_dict(self, consultation: Consultation) -> dict:
        return {
            "id": consultation.id,
            "patient_id": consultation.patient_id,
            "doctor_id": consultation.doctor_id,
            "slot_id": consultation.slot_id,
            "status": consultation.status,
            "symptoms": consultation.symptoms,
            "notes": consultation.notes,
            "started_at": consultation.started_at,
            "ended_at": consultation.ended_at,
            "created_at": consultation.created_at,
        }


consultation_service = ConsultationService()

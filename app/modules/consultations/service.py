from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictException, NotFoundException
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.audit.service import audit_service
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
        page: int = 1, size: int = 20,
    ) -> list[dict]:
        pagination = PaginationParams(page, size)
        count_result = await session.execute(
            select(func.count()).where(Consultation.patient_id == patient_id)
        )
        total = count_result.scalar() or 0
        result = await session.execute(
            select(Consultation).where(
                Consultation.patient_id == patient_id
            ).offset(pagination.offset).limit(pagination.limit).order_by(Consultation.created_at.desc())
        )
        return self._paginated([self._to_dict(c) for c in result.scalars().all()], total, pagination)

    async def list_for_doctor(
        self, session: AsyncSession, user_id: UUID,
        page: int = 1, size: int = 20,
    ) -> list[dict]:
        doctor = await doctor_repository.get_by_user_id(session, user_id)
        if not doctor:
            raise NotFoundException("Doctor profile not found")
        pagination = PaginationParams(page, size)
        count_result = await session.execute(
            select(func.count()).where(Consultation.doctor_id == doctor.id)
        )
        total = count_result.scalar() or 0
        result = await session.execute(
            select(Consultation).where(
                Consultation.doctor_id == doctor.id
            ).offset(pagination.offset).limit(pagination.limit).order_by(Consultation.created_at.desc())
        )
        return self._paginated([self._to_dict(c) for c in result.scalars().all()], total, pagination)

    async def start_consultation(
        self, session: AsyncSession, consultation_id: UUID,
        doctor_user_id: UUID, notes: str | None = None,
        ip_address: str | None = None, user_agent: str | None = None,
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

        old_status = consultation.status
        consultation.status = ConsultationStatus.IN_PROGRESS
        consultation.started_at = datetime.now(UTC)
        if notes:
            consultation.notes = notes

        await audit_service.log_action(
            session, user_id=doctor_user_id, action="status_changed", entity_type="consultation",
            entity_id=str(consultation.id),
            old_values={"status": old_status},
            new_values={"status": ConsultationStatus.IN_PROGRESS, "started_at": consultation.started_at.isoformat()},
            ip_address=ip_address, user_agent=user_agent,
        )

        return self._to_dict(consultation)

    async def complete_consultation(
        self, session: AsyncSession, consultation_id: UUID,
        doctor_user_id: UUID, notes: str | None = None,
        ip_address: str | None = None, user_agent: str | None = None,
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

        old_status = consultation.status
        consultation.status = ConsultationStatus.COMPLETED
        consultation.ended_at = datetime.now(UTC)
        if notes:
            consultation.notes = notes

        await audit_service.log_action(
            session, user_id=doctor_user_id, action="status_changed", entity_type="consultation",
            entity_id=str(consultation.id),
            old_values={"status": old_status},
            new_values={"status": ConsultationStatus.COMPLETED, "ended_at": consultation.ended_at.isoformat()},
            ip_address=ip_address, user_agent=user_agent,
        )

        return self._to_dict(consultation)

    def _paginated(self, items: list, total: int, pagination: PaginationParams) -> dict:
        paginated = PaginatedResponse(items, total, pagination)
        return paginated.dict()

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

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictException, NotFoundException
from app.modules.consultations.models import Consultation
from app.modules.doctors.repository import doctor_repository
from app.modules.prescriptions.models import Prescription


class PrescriptionService:
    async def create(
        self, session: AsyncSession, doctor_user_id: UUID, data: dict,
    ) -> dict:
        doctor = await doctor_repository.get_by_user_id(session, doctor_user_id)
        if not doctor:
            raise NotFoundException("Doctor profile not found")

        result = await session.execute(
            select(Consultation).where(Consultation.id == data["consultation_id"])
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            raise NotFoundException("Consultation not found")
        if consultation.doctor_id != doctor.id:
            raise ConflictException("This consultation is not yours")

        prescription = Prescription(
            consultation_id=data["consultation_id"],
            doctor_id=doctor.id,
            medication_name=data["medication_name"],
            dosage=data["dosage"],
            frequency=data["frequency"],
            duration=data["duration"],
            notes=data.get("notes"),
        )
        session.add(prescription)
        await session.flush()

        return self._to_dict(prescription)

    async def list_for_consultation(
        self, session: AsyncSession, consultation_id: UUID,
    ) -> list[dict]:
        result = await session.execute(
            select(Prescription).where(
                Prescription.consultation_id == consultation_id
            ).order_by(Prescription.created_at.desc())
        )
        return [self._to_dict(p) for p in result.scalars().all()]

    def _to_dict(self, prescription: Prescription) -> dict:
        return {
            "id": prescription.id,
            "consultation_id": prescription.consultation_id,
            "doctor_id": prescription.doctor_id,
            "medication_name": prescription.medication_name,
            "dosage": prescription.dosage,
            "frequency": prescription.frequency,
            "duration": prescription.duration,
            "notes": prescription.notes,
            "created_at": prescription.created_at,
        }


prescription_service = PrescriptionService()

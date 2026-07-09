from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.doctors.repository import doctor_repository, slot_repository
from app.modules.doctors.models import Doctor
from app.common.exceptions import NotFoundException
from app.common.pagination import PaginationParams, PaginatedResponse


class DoctorService:
    async def create_or_update_profile(
        self, session: AsyncSession, user_id: UUID, data: dict
    ) -> dict:
        doctor = await doctor_repository.get_by_user_id(session, user_id)
        if doctor:
            for key, value in data.items():
                setattr(doctor, key, value)
        else:
            doctor = await doctor_repository.create(session, user_id=user_id, **data)

        return await self._to_response(session, doctor)

    async def get_profile(self, session: AsyncSession, user_id: UUID) -> dict:
        doctor = await doctor_repository.get_by_user_id(session, user_id)
        if not doctor:
            raise NotFoundException("Doctor profile not found. Create one first.")
        return await self._to_response(session, doctor)

    async def get_doctor_by_id(self, session: AsyncSession, doctor_id: UUID) -> dict:
        doctor = await doctor_repository.get_by_id(session, doctor_id)
        if not doctor:
            raise NotFoundException("Doctor not found")
        return await self._to_response(session, doctor)

    async def search(
        self, session: AsyncSession,
        specialization: str | None = None,
        min_rating: float | None = None,
        max_fee: float | None = None,
        available_only: bool = False,
        query: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        pagination = PaginationParams(page, size)
        doctors, total = await doctor_repository.search(
            session, specialization, min_rating, max_fee,
            available_only, query, pagination,
        )
        items = [await self._to_response(session, d) for d in doctors]
        paginated = PaginatedResponse(items, total, pagination)
        return paginated.dict()

    async def add_slots(
        self, session: AsyncSession, user_id: UUID, slots_data: list[dict]
    ) -> list[dict]:
        doctor = await doctor_repository.get_by_user_id(session, user_id)
        if not doctor:
            raise NotFoundException("Doctor profile not found")

        slots_db = await slot_repository.create_batch(session, doctor.id, slots_data)
        return [
            {
                "id": str(s.id),
                "doctor_id": str(s.doctor_id),
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "is_booked": s.is_booked,
            }
            for s in slots_db
        ]

    async def get_slots(
        self, session: AsyncSession, doctor_id: UUID, date_str: str | None = None
    ) -> list[dict]:
        if date_str:
            date = datetime.fromisoformat(date_str).date()
        else:
            date = datetime.utcnow().date()

        slots = await slot_repository.get_available_by_doctor_and_date(
            session, doctor_id, date
        )
        return [
            {
                "id": str(s.id),
                "doctor_id": str(s.doctor_id),
                "start_time": s.start_time.isoformat(),
                "end_time": s.end_time.isoformat(),
                "is_booked": s.is_booked,
            }
            for s in slots
        ]

    async def _to_response(self, session: AsyncSession, doctor: Doctor) -> dict:
        resp = {
            "id": doctor.id,
            "user_id": doctor.user_id,
            "specialization": doctor.specialization,
            "license_number": doctor.license_number,
            "years_of_experience": doctor.years_of_experience,
            "consultation_fee": doctor.consultation_fee,
            "average_rating": doctor.average_rating,
            "bio": doctor.bio,
            "is_available": doctor.is_available,
        }
        from app.modules.users.models import User
        user_result = await session.execute(
            select(User).options(selectinload(User.profile)).where(User.id == doctor.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            resp["user_email"] = user.email
            if user.profile:
                resp["first_name"] = user.profile.first_name
                resp["last_name"] = user.profile.last_name
        return resp


doctor_service = DoctorService()

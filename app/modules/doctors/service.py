from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions import BadRequestException, ConflictException, NotFoundException
from app.common.pagination import PaginatedResponse, PaginationParams
from app.modules.audit.service import audit_service
from app.modules.doctors.models import Doctor
from app.modules.doctors.repository import doctor_repository, slot_repository
from app.modules.users.models import User


class DoctorService:
    async def create_or_update_profile(
        self, session: AsyncSession, user_id: UUID, data: dict,
        ip_address: str | None = None, user_agent: str | None = None,
    ) -> dict:
        doctor = await doctor_repository.get_by_user_id(session, user_id)
        is_new = doctor is None
        old_data = None
        if doctor:
            old_data = {k: getattr(doctor, k) for k in data if hasattr(doctor, k)}
            for key, value in data.items():
                setattr(doctor, key, value)
        else:
            doctor = await doctor_repository.create(session, user_id=user_id, **data)

        await audit_service.log_action(
            session, user_id=user_id,
            action="created" if is_new else "updated",
            entity_type="doctor", entity_id=str(doctor.id),
            old_values=old_data, new_values=data,
            ip_address=ip_address, user_agent=user_agent,
        )

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
        self, session: AsyncSession, user_id: UUID, slots_data: list[dict],
        ip_address: str | None = None, user_agent: str | None = None,
    ) -> list[dict]:
        doctor = await doctor_repository.get_by_user_id(session, user_id)
        if not doctor:
            raise NotFoundException("Doctor profile not found")

        for slot_data in slots_data:
            overlapping = await slot_repository.find_overlapping(
                session, doctor.id, slot_data["start_time"], slot_data["end_time"]
            )
            if overlapping:
                msg = (
                    f"Slot overlaps with existing slot: "
                    f"{overlapping[0].start_time.isoformat()} - {overlapping[0].end_time.isoformat()}"
                )
                raise ConflictException(msg)

        slots_db = await slot_repository.create_batch(session, doctor.id, slots_data)
        serialized_slots = [
            {"start_time": s["start_time"].isoformat(), "end_time": s["end_time"].isoformat()}
            for s in slots_data
        ]
        await audit_service.log_action(
            session, user_id=user_id, action="created", entity_type="availability_slot",
            entity_id=str(doctor.id),
            new_values={"count": len(slots_db), "slots": serialized_slots},
            ip_address=ip_address, user_agent=user_agent,
        )

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
            try:
                date = datetime.fromisoformat(date_str).date()
            except ValueError:
                raise BadRequestException(f"Invalid date format: {date_str}. Use ISO format") from None
        else:
            date = datetime.now(UTC).date()

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

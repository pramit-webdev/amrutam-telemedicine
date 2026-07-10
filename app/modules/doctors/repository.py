from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.pagination import PaginationParams
from app.modules.doctors.models import AvailabilitySlot, Doctor
from app.modules.users.models import User


class DoctorRepository:
    async def get_by_user_id(self, session: AsyncSession, user_id: UUID) -> Doctor | None:
        result = await session.execute(
            select(Doctor).options(
                selectinload(Doctor.user).selectinload(User.profile)
            ).where(Doctor.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, doctor_id: UUID) -> Doctor | None:
        result = await session.execute(
            select(Doctor).options(
                selectinload(Doctor.user).selectinload(User.profile)
            ).where(Doctor.id == doctor_id)
        )
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, user_id: UUID, **kwargs) -> Doctor:
        doctor = Doctor(user_id=user_id, **kwargs)
        session.add(doctor)
        await session.flush()
        return doctor

    async def search(
        self, session: AsyncSession,
        specialization: str | None = None,
        min_rating: float | None = None,
        max_fee: float | None = None,
        available_only: bool = False,
        query: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> tuple[list[Doctor], int]:
        stmt = select(Doctor).options(selectinload(Doctor.user).selectinload(User.profile))

        conditions = []
        if specialization:
            conditions.append(Doctor.specialization.ilike(f"%{specialization}%"))
        if min_rating is not None:
            conditions.append(Doctor.average_rating >= min_rating)
        if max_fee is not None:
            conditions.append(Doctor.consultation_fee <= max_fee)
        if available_only:
            conditions.append(Doctor.is_available)
        if query:
            conditions.append(
                Doctor.specialization.ilike(f"%{query}%")
                | Doctor.bio.ilike(f"%{query}%")
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0

        if pagination:
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)

        result = await session.execute(stmt.order_by(Doctor.average_rating.desc().nullslast()))
        return list(result.scalars().all()), total


doctor_repository = DoctorRepository()


class AvailabilitySlotRepository:
    async def get_by_id(self, session: AsyncSession, slot_id: UUID) -> AvailabilitySlot | None:
        result = await session.execute(
            select(AvailabilitySlot).where(AvailabilitySlot.id == slot_id)
        )
        return result.scalar_one_or_none()

    async def get_available_by_doctor_and_date(
        self, session: AsyncSession, doctor_id: UUID, date: datetime.date
    ) -> list[AvailabilitySlot]:
        start_of_day = datetime.combine(date, datetime.min.time())
        end_of_day = datetime.combine(date, datetime.max.time())
        result = await session.execute(
            select(AvailabilitySlot).where(
                AvailabilitySlot.doctor_id == doctor_id,
                AvailabilitySlot.start_time >= start_of_day,
                AvailabilitySlot.end_time <= end_of_day,
                ~AvailabilitySlot.is_booked,
            ).order_by(AvailabilitySlot.start_time)
        )
        return list(result.scalars().all())

    async def create_batch(
        self, session: AsyncSession, doctor_id: UUID, slots: list[dict]
    ) -> list[AvailabilitySlot]:
        created = []
        for slot_data in slots:
            slot = AvailabilitySlot(doctor_id=doctor_id, **slot_data)
            session.add(slot)
            created.append(slot)
        await session.flush()
        return created


slot_repository = AvailabilitySlotRepository()

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.consultations.models import Consultation, ConsultationStatus
from app.modules.doctors.models import AvailabilitySlot


async def expire_pending_consultations(ctx: dict) -> dict:
    cutoff = datetime.now(UTC) - timedelta(minutes=15)
    async with async_session_factory() as session:
        result = await session.execute(
            select(Consultation).where(
                Consultation.status == ConsultationStatus.PENDING_PAYMENT,
                Consultation.created_at < cutoff,
            )
        )
        expired = list(result.scalars().all())
        for consultation in expired:
            consultation.status = ConsultationStatus.CANCELLED
            slot_result = await session.execute(
                select(AvailabilitySlot).where(AvailabilitySlot.id == consultation.slot_id)
            )
            slot = slot_result.scalar_one_or_none()
            if slot:
                slot.is_booked = False
        await session.commit()
    return {"expired_count": len(expired)}


async def send_reminder(ctx: dict, consultation_id: str) -> dict:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Consultation).where(Consultation.id == UUID(consultation_id))
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            return {"error": "not_found"}
    return {"reminder_sent": True, "consultation_id": consultation_id}


async def aggregate_analytics(ctx: dict) -> dict:
    async with async_session_factory() as session:
        from sqlalchemy import func
        total = await session.execute(
            select(func.count(Consultation.id))
        )
        total_count = total.scalar()
        pending = await session.execute(
            select(func.count(Consultation.id)).where(
                Consultation.status == ConsultationStatus.PENDING_PAYMENT
            )
        )
        pending_count = pending.scalar()
    return {
        "total_consultations": total_count,
        "pending_payments": pending_count,
        "aggregated_at": datetime.now(UTC).isoformat(),
    }


class WorkerSettings:
    functions = [expire_pending_consultations, send_reminder, aggregate_analytics]
    redis_settings = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    poll_delay = 10
    max_tasks = 10
    keep_result_seconds = 3600
    keep_result_hours = 1

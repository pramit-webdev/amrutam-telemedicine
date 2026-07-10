from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.consultations.models import Consultation, ConsultationStatus
from app.modules.doctors.models import Doctor
from app.modules.payments.models import Payment, PaymentStatus


class AnalyticsService:
    async def get_consultation_stats(
        self, session: AsyncSession, days: int = 30,
    ) -> dict:
        since = datetime.now(UTC) - timedelta(days=days)

        total_result = await session.execute(
            select(func.count()).select_from(Consultation).where(
                Consultation.created_at >= since
            )
        )
        total = total_result.scalar() or 0

        by_status = await session.execute(
            select(Consultation.status, func.count()).where(
                Consultation.created_at >= since
            ).group_by(Consultation.status)
        )
        status_breakdown = {row[0]: row[1] for row in by_status.all()}

        return {
            "period_days": days,
            "total_consultations": total,
            "by_status": status_breakdown,
        }

    async def get_revenue_stats(
        self, session: AsyncSession, days: int = 30,
    ) -> dict:
        since = datetime.now(UTC) - timedelta(days=days)

        result = await session.execute(
            select(
                func.coalesce(func.sum(Payment.amount), 0),
                func.count(),
            ).where(
                and_(
                    Payment.created_at >= since,
                    Payment.status == PaymentStatus.COMPLETED,
                )
            )
        )
        row = result.one()
        total_revenue = float(row[0])
        total_transactions = row[1]

        return {
            "period_days": days,
            "total_revenue": total_revenue,
            "total_transactions": total_transactions,
            "average_transaction": round(total_revenue / total_transactions, 2) if total_transactions > 0 else 0,
        }

    async def get_top_doctors(
        self, session: AsyncSession, days: int = 30, limit: int = 10,
    ) -> list[dict]:
        since = datetime.now(UTC) - timedelta(days=days)

        result = await session.execute(
            select(
                Consultation.doctor_id,
                func.count().label("consultation_count"),
            ).where(
                and_(
                    Consultation.created_at >= since,
                    Consultation.status == ConsultationStatus.COMPLETED,
                )
            ).group_by(Consultation.doctor_id).order_by(
                func.count().desc()
            ).limit(limit)
        )

        doctor_ids = []
        counts = {}
        for row in result.all():
            doctor_ids.append(row[0])
            counts[str(row[0])] = row[1]

        if not doctor_ids:
            return []

        doctors_result = await session.execute(
            select(Doctor).where(Doctor.id.in_(doctor_ids))
        )
        doctors = doctors_result.scalars().all()

        doctor_map = {str(d.id): d for d in doctors}
        return [
            {
                "doctor_id": str(did),
                "specialization": doctor_map.get(str(did), {}).specialization if doctor_map.get(str(did)) else None,
                "consultation_count": counts.get(str(did), 0),
            }
            for did in doctor_ids
            if str(did) in doctor_map
        ]


analytics_service = AnalyticsService()

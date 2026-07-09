from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payments.models import Payment, PaymentStatus
from app.modules.consultations.models import Consultation, ConsultationStatus
from app.common.exceptions import NotFoundException, ConflictException


class PaymentRepository:
    async def get_by_id(self, session: AsyncSession, payment_id: UUID) -> Payment | None:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_by_consultation(self, session: AsyncSession, consultation_id: UUID) -> Payment | None:
        result = await session.execute(
            select(Payment).where(Payment.consultation_id == consultation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, session: AsyncSession, key: str) -> Payment | None:
        result = await session.execute(
            select(Payment).where(Payment.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        session.add(payment)
        await session.flush()
        return payment


payment_repository = PaymentRepository()


class PaymentService:
    async def process_payment(
        self, session: AsyncSession, patient_id: UUID,
        consultation_id: UUID, amount: float, currency: str,
        idempotency_key: str, payment_method: str | None = None,
    ) -> dict:
        existing = await payment_repository.get_by_idempotency_key(session, idempotency_key)
        if existing:
            return self._to_dict(existing)

        result = await session.execute(
            select(Consultation).where(Consultation.id == consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if not consultation:
            raise NotFoundException("Consultation not found")
        if consultation.patient_id != patient_id:
            raise ConflictException("You can only pay for your own consultations")
        if consultation.status != ConsultationStatus.PENDING_PAYMENT:
            raise ConflictException(
                f"Cannot pay for consultation in status: {consultation.status}"
            )

        payment = await payment_repository.create(
            session,
            consultation_id=consultation_id,
            patient_id=patient_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.COMPLETED,
            payment_method=payment_method,
            idempotency_key=idempotency_key,
        )

        consultation.status = ConsultationStatus.CONFIRMED

        return self._to_dict(payment)

    async def refund_payment(
        self, session: AsyncSession, payment_id: UUID, reason: str | None = None,
    ) -> dict:
        payment = await payment_repository.get_by_id(session, payment_id)
        if not payment:
            raise NotFoundException("Payment not found")
        if payment.status != PaymentStatus.COMPLETED:
            raise ConflictException(f"Cannot refund payment in status: {payment.status}")

        payment.status = PaymentStatus.REFUNDED

        result = await session.execute(
            select(Consultation).where(Consultation.id == payment.consultation_id)
        )
        consultation = result.scalar_one_or_none()
        if consultation:
            consultation.status = ConsultationStatus.CANCELLED

        return self._to_dict(payment)

    def _to_dict(self, payment: Payment) -> dict:
        return {
            "id": payment.id,
            "consultation_id": payment.consultation_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "payment_method": payment.payment_method,
        }


payment_service = PaymentService()

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, ConsultationStatus


class Consultation(Base, TimestampMixin):
    __tablename__ = "consultations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("availability_slots.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    status: Mapped[ConsultationStatus] = mapped_column(
        SAEnum(ConsultationStatus), nullable=False, default=ConsultationStatus.PENDING_PAYMENT, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    slot = relationship("AvailabilitySlot", back_populates="consultation")
    prescriptions = relationship("Prescription", back_populates="consultation", lazy="selectin", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="consultation", uselist=False)

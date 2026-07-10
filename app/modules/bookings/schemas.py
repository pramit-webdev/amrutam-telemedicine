from uuid import UUID

from pydantic import BaseModel, Field


class BookingRequest(BaseModel):
    doctor_id: UUID
    slot_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=255)
    symptoms: str | None = Field(default=None, max_length=2000)


class BookingResponse(BaseModel):
    consultation_id: UUID
    status: str
    doctor_id: UUID
    patient_id: UUID
    slot_id: UUID


class CancelBookingRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)

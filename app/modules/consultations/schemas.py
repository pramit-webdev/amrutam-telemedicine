from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class ConsultationResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    slot_id: UUID | None
    status: str
    symptoms: str | None
    notes: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class StartConsultationRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class CompleteConsultationRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PrescriptionCreate(BaseModel):
    consultation_id: UUID
    medication_name: str = Field(max_length=255)
    dosage: str = Field(max_length=100)
    frequency: str = Field(max_length=100)
    duration: str = Field(max_length=100)
    notes: str | None = Field(default=None, max_length=2000)


class PrescriptionResponse(BaseModel):
    id: UUID
    consultation_id: UUID
    doctor_id: UUID
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    notes: str | None
    created_at: datetime

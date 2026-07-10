from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DoctorCreate(BaseModel):
    specialization: str = Field(max_length=100)
    license_number: str = Field(max_length=50)
    years_of_experience: int = Field(default=0, ge=0)
    consultation_fee: float = Field(default=0.0, ge=0)
    bio: str | None = Field(default=None, max_length=2000)


class DoctorResponse(BaseModel):
    id: UUID
    user_id: UUID
    specialization: str
    license_number: str
    years_of_experience: int
    consultation_fee: float
    average_rating: float | None
    bio: str | None
    is_available: bool
    user_email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class SlotCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class SlotBatchCreate(BaseModel):
    slots: list[SlotCreate]


class SlotResponse(BaseModel):
    id: UUID
    doctor_id: UUID
    start_time: datetime
    end_time: datetime
    is_booked: bool
    version: int

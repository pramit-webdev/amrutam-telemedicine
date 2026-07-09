from pydantic import BaseModel, Field
from datetime import date
from uuid import UUID


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    is_active: bool
    mfa_enabled: bool


class ProfileResponse(BaseModel):
    first_name: str | None
    last_name: str | None
    date_of_birth: date | None
    gender: str | None
    address: str | None
    avatar_url: str | None


class ProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, pattern="^(male|female|other)$")
    address: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = Field(default=None, max_length=512)

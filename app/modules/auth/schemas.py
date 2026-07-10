from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="patient", pattern="^(patient|doctor|admin)$")
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MFAEnrollResponse(BaseModel):
    secret: str
    uri: str
    qr_code: str


class MFAVerifyRequest(BaseModel):
    user_id: str
    token: str = Field(min_length=6, max_length=6)


class MFAVerifyResponse(BaseModel):
    verified: bool
    backup_codes: list[str] | None = None


class RefreshRequest(BaseModel):
    refresh_token: str

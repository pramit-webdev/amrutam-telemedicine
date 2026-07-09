from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import (
    RegisterRequest, LoginRequest, MFAEnrollResponse, MFAVerifyRequest, RefreshRequest,
)
from app.modules.auth.service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    return await auth_service.register(
        session, body.email, body.password, body.role,
        body.first_name, body.last_name,
    )


@router.post("/login")
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    return await auth_service.login(session, body.email, body.password)


@router.post("/mfa/enroll", response_model=MFAEnrollResponse)
async def enroll_mfa(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await auth_service.enroll_mfa(session, current_user["id"])


@router.post("/mfa/verify")
async def verify_mfa(
    body: MFAVerifyRequest,
    user_id: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    # user_id comes from query param after initial login response when mfa_required is true
    if not user_id:
        from app.common.exceptions import UnauthorizedException
        raise UnauthorizedException("user_id is required for MFA verification")
    import uuid
    return await auth_service.verify_mfa(session, uuid.UUID(user_id), body.token)


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    return await auth_service.refresh_token(body.refresh_token)

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.rate_limit import rate_limiter
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import (
    LoginRequest,
    MFAVerifyRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.modules.auth.service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
@rate_limiter.limit("10/minute")
async def register(request: Request, body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await auth_service.register(
        session, body.email, body.password, body.role,
        body.first_name, body.last_name,
        ip_address=ip_address, user_agent=user_agent,
    )


@router.post("/login")
@rate_limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, session: AsyncSession = Depends(get_session)):
    return await auth_service.login(session, body.email, body.password)


@router.post("/mfa/enroll")
@rate_limiter.limit("5/minute")
async def enroll_mfa(
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await auth_service.enroll_mfa(session, current_user["id"])


@router.post("/mfa/verify")
@rate_limiter.limit("10/minute")
async def verify_mfa(
    request: Request,
    body: MFAVerifyRequest,
    session: AsyncSession = Depends(get_session),
):
    return await auth_service.verify_mfa(session, UUID(body.user_id), body.token)


@router.post("/refresh")
@rate_limiter.limit("10/minute")
async def refresh(
    request: Request,
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    return await auth_service.refresh_token(session, body.refresh_token)

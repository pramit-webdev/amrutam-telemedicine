import base64
import io
from uuid import UUID

import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    verify_password,
    verify_totp,
)
from app.modules.users.models import Profile
from app.modules.users.repository import user_repository


class AuthService:
    async def register(
        self, session: AsyncSession, email: str, password: str, role: str,
        first_name: str | None, last_name: str | None,
        ip_address: str | None = None, user_agent: str | None = None,
    ) -> dict:
        existing = await user_repository.get_by_email(session, email)
        if existing:
            raise ConflictException("Email already registered")

        user = await user_repository.create(
            session,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )

        profile = Profile(user_id=user.id, first_name=first_name, last_name=last_name)
        session.add(profile)

        from app.modules.audit.service import audit_service
        await audit_service.log_action(
            session, user_id=user.id, action="created", entity_type="user",
            entity_id=str(user.id), new_values={"email": email, "role": role},
            ip_address=ip_address, user_agent=user_agent,
        )

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
        }

    async def login(self, session: AsyncSession, email: str, password: str) -> dict:
        user = await user_repository.get_by_email(session, email)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        if user.mfa_enabled:
            return {"mfa_required": True, "user_id": str(user.id)}

        access_token = create_access_token(user.id, user.role)
        refresh_token = create_refresh_token(user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email, "role": user.role},
        }

    async def enroll_mfa(self, session: AsyncSession, user_id: UUID) -> dict:
        user = await user_repository.get_by_id(session, user_id)
        if not user:
            raise UnauthorizedException("User not found")

        secret = generate_totp_secret()
        uri = get_totp_uri(secret, user.email)

        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        user.mfa_secret = secret
        user.mfa_enabled = True

        return {"secret": secret, "uri": uri, "qr_code": qr_b64}

    async def verify_mfa(self, session: AsyncSession, user_id: UUID, token: str) -> dict:
        user = await user_repository.get_by_id(session, user_id)
        if not user or not user.mfa_secret:
            raise UnauthorizedException("MFA not configured")

        if not verify_totp(user.mfa_secret, token):
            raise UnauthorizedException("Invalid MFA token")

        access_token = create_access_token(user.id, user.role)
        refresh_token = create_refresh_token(user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email, "role": user.role},
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid refresh token")

        access_token = create_access_token(UUID(user_id), payload.get("role", "patient"))
        new_refresh = create_refresh_token(UUID(user_id))
        return {"access_token": access_token, "refresh_token": new_refresh, "token_type": "bearer"}


auth_service = AuthService()

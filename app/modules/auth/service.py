import base64
import io
import time
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
from app.modules.audit.service import audit_service
from app.modules.users.models import Profile
from app.modules.users.repository import user_repository

# In-memory account lockout tracking.
# Key: email, Value: [failed_attempts, lockout_until_timestamp]
# This is acceptable for this deployment scale; counter resets on restart.
_lockout_store: dict[str, list[int | float]] = {}

MAX_FAILED_ATTEMPTS = 10
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes


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
        if not user:
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        now = time.time()
        entry = _lockout_store.get(email)
        if entry:
            _, lock_until = entry
            if lock_until > now:
                remaining = int((lock_until - now) // 60)
                raise UnauthorizedException(f"Account locked. Try again in {remaining} minute(s).")

        if not verify_password(password, user.password_hash):
            attempts, lock_until = entry if entry else (0, 0)
            attempts += 1
            if attempts >= MAX_FAILED_ATTEMPTS:
                _lockout_store[email] = [0, now + LOCKOUT_DURATION_SECONDS]
                remaining = LOCKOUT_DURATION_SECONDS // 60
                raise UnauthorizedException(f"Account locked. Try again in {remaining} minute(s).")
            else:
                _lockout_store[email] = [attempts, 0]
            raise UnauthorizedException("Invalid email or password")

        _lockout_store.pop(email, None)

        if user.mfa_enabled:
            return {"mfa_required": True, "user_id": str(user.id)}

        access_token = create_access_token(user.id, user.role)
        refresh_token = create_refresh_token(user.id, user.token_version)
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
        refresh_token = create_refresh_token(user.id, user.token_version)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email, "role": user.role},
        }

    async def refresh_token(self, session: AsyncSession, refresh_token_str: str) -> dict:
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid refresh token")

        token_version_claim = payload.get("ver", 0)

        user = await user_repository.get_by_id(session, UUID(user_id))
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")

        if user.token_version != token_version_claim:
            raise UnauthorizedException("Refresh token has been revoked")

        user.token_version += 1

        access_token = create_access_token(user.id, user.role)
        new_refresh = create_refresh_token(user.id, user.token_version)
        return {"access_token": access_token, "refresh_token": new_refresh, "token_type": "bearer"}


auth_service = AuthService()

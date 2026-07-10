from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundException
from app.modules.users.models import Profile
from app.modules.users.repository import user_repository


class UserService:
    async def get_profile(self, session: AsyncSession, user_id: UUID) -> dict:
        user = await user_repository.get_by_id(session, user_id)
        if not user:
            raise NotFoundException("User not found")
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "mfa_enabled": user.mfa_enabled,
            "profile": {
                "first_name": user.profile.first_name if user.profile else None,
                "last_name": user.profile.last_name if user.profile else None,
                "date_of_birth": user.profile.date_of_birth if user.profile else None,
                "gender": user.profile.gender if user.profile else None,
                "address": user.profile.address if user.profile else None,
                "avatar_url": user.profile.avatar_url if user.profile else None,
            } if user.profile else None,
        }

    async def update_profile(self, session: AsyncSession, user_id: UUID, data: dict) -> dict:
        user = await user_repository.get_by_id(session, user_id)
        if not user:
            raise NotFoundException("User not found")

        if not user.profile:
            profile = Profile(user_id=user_id)
            session.add(profile)
            await session.flush()
            user.profile = profile

        for key, value in data.items():
            if value is not None:
                setattr(user.profile, key, value)

        return await self.get_profile(session, user_id)


user_service = UserService()

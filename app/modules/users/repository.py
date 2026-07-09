from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


class UserRepository:
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, user_id: UUID) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, **kwargs) -> User:
        user = User(**kwargs)
        session.add(user)
        await session.flush()
        return user


user_repository = UserRepository()

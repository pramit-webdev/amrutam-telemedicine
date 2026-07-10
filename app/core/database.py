from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

pool_size = 20 if settings.environment == "production" else 5
max_overflow = 10 if settings.environment == "production" else 2

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_pre_ping=True,
    connect_args={"timeout": 10},
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

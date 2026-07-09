from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import get_settings

settings = get_settings()

ssl_arg = {"ssl": "require"} if settings.environment != "development" else {}

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=settings.environment != "development" and 5 or 20,
    max_overflow=settings.environment != "development" and 2 or 10,
    pool_pre_ping=True,
    connect_args=ssl_arg,
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

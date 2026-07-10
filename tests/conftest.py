import os

os.environ.setdefault("ENABLE_METRICS", "false")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.base import Base
from app.core.database import get_session
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://amrutam:amrutam@localhost:5432/amrutam_test"


@pytest_asyncio.fixture(scope="function")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine):
    async def override_get_session():
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            finally:
                await s.close()

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def patient_token(client: AsyncClient) -> str:
    await client.post("/auth/register", json={
        "email": "pat_test@test.com", "password": "password123",
        "role": "patient", "first_name": "Test", "last_name": "Patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "pat_test@test.com", "password": "password123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def doctor_token(client: AsyncClient) -> tuple[str, str, str]:
    await client.post("/auth/register", json={
        "email": "doc_test@test.com", "password": "password123",
        "role": "doctor", "first_name": "Test", "last_name": "Doctor",
    })
    resp = await client.post("/auth/login", json={
        "email": "doc_test@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]
    await client.post("/doctors/profile", json={
        "specialization": "Cardiology", "license_number": "LIC-TEST",
        "years_of_experience": 5, "consultation_fee": 300,
    }, headers={"Authorization": f"Bearer {token}"})
    slots_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-07-15T09:00:00Z", "end_time": "2026-07-15T09:30:00Z"}]
    }, headers={"Authorization": f"Bearer {token}"})
    slots_data = slots_resp.json()
    slot_id = slots_data[0]["id"]
    doctor_id = slots_data[0]["doctor_id"]
    return token, slot_id, doctor_id

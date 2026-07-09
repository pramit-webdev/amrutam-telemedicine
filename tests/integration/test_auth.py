import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_patient(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "email": "new_pat@test.com", "password": "password123",
        "role": "patient", "first_name": "New", "last_name": "Patient",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "new_pat@test.com"
    assert data["role"] == "patient"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "dup@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/register", json={
        "email": "dup@test.com", "password": "password123", "role": "patient",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "login@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "login@test.com", "password": "password123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "wrong@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "wrong@test.com", "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mfa_enroll(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "mfa@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "mfa@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.post("/auth/mfa/enroll", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "secret" in data
    assert "uri" in data
    assert "qr_code" in data

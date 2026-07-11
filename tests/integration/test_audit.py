import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_logs_admin_access(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "aud_admin@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={"email": "aud_admin@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp = await client.get("/audit-logs?page=1&size=10",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data


@pytest.mark.asyncio
async def test_audit_logs_patient_forbidden(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "aud_pat@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={"email": "aud_pat@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp = await client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_unauthorized(client: AsyncClient):
    resp = await client.get("/audit-logs")
    assert resp.status_code == 401

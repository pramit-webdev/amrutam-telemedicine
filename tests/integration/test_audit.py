import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_logs_admin_only(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "audit_pat@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "audit_pat@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_admin_access(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "audit_admin@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={
        "email": "audit_admin@test.com", "password": "password123",
    })
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
async def test_audit_log_filtering(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "audit_filter_admin@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={
        "email": "audit_filter_admin@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.get("/audit-logs?action=created&entity_type=user",
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data

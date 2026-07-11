import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_analytics_consultations(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "an_admin@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={"email": "an_admin@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/consultations?days=30",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_consultations" in data
    assert "by_status" in data
    assert data["period_days"] == 30


@pytest.mark.asyncio
async def test_admin_analytics_revenue(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "an_rev@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={"email": "an_rev@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/revenue?days=30",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_revenue" in data
    assert "total_transactions" in data
    assert "average_transaction" in data
    assert data["period_days"] == 30


@pytest.mark.asyncio
async def test_admin_analytics_top_doctors(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "an_top@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={"email": "an_top@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/top-doctors?days=30&limit=5",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_patient_cannot_access_analytics(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "an_pat@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={"email": "an_pat@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/consultations",
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

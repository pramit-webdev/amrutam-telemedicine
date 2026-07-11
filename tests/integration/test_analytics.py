import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_admin_only(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "analytics_pat@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "analytics_pat@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/consultations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analytics_consultation_stats(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "analytics_admin@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={
        "email": "analytics_admin@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/consultations?days=30",
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_consultations" in data
    assert "by_status" in data
    assert "period_days" in data


@pytest.mark.asyncio
async def test_analytics_revenue_stats(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "analytics_rev_admin@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={
        "email": "analytics_rev_admin@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/revenue?days=30",
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_revenue" in data
    assert "total_transactions" in data
    assert "average_transaction" in data


@pytest.mark.asyncio
async def test_analytics_top_doctors(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "analytics_top_admin@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={
        "email": "analytics_top_admin@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/top-doctors?days=30&limit=5",
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

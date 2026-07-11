import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_patient_cannot_create_doctor_profile(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "rbac_pat@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "rbac_pat@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.post("/doctors/profile", json={
        "specialization": "Cardiology", "license_number": "LIC-RBAC",
        "years_of_experience": 5, "consultation_fee": 300,
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_doctor_cannot_book_slot(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "rbac_doc@test.com", "password": "password123", "role": "doctor",
    })
    resp = await client.post("/auth/login", json={
        "email": "rbac_doc@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.post("/bookings", json={
        "doctor_id": "00000000-0000-0000-0000-000000000000",
        "slot_id": "00000000-0000-0000-0000-000000000000",
        "idempotency_key": "rbac-bk-1",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_analytics(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "rbac_admin@test.com", "password": "password123", "role": "admin",
    })
    resp = await client.post("/auth/login", json={
        "email": "rbac_admin@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.get("/analytics/consultations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_patient_cannot_refund_payment(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "rbac_refund@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "rbac_refund@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    resp = await client.post("/payments/00000000-0000-0000-0000-000000000000/refund", json={},
                              headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

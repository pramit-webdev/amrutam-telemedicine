import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_doctor_profile(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "doc_prof@test.com", "password": "password123", "role": "doctor",
    })
    resp = await client.post("/auth/login", json={"email": "doc_prof@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    resp = await client.post("/doctors/profile", json={
        "specialization": "Pediatrics", "license_number": "LIC-PROF",
        "years_of_experience": 7, "consultation_fee": 600,
        "bio": "Experienced pediatrician",
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["specialization"] == "Pediatrics"
    assert data["consultation_fee"] == 600
    assert data["years_of_experience"] == 7
    return data


@pytest.mark.asyncio
async def test_get_own_profile(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "doc_own@test.com", "password": "password123", "role": "doctor",
    })
    resp = await client.post("/auth/login", json={"email": "doc_own@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "Dermatology", "license_number": "LIC-OWN",
        "years_of_experience": 4, "consultation_fee": 350,
    }, headers={"Authorization": f"Bearer {token}"})

    resp = await client.get("/doctors/profile", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["specialization"] == "Dermatology"


@pytest.mark.asyncio
async def test_get_doctor_by_id(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "doc_id@test.com", "password": "password123", "role": "doctor",
    })
    resp = await client.post("/auth/login", json={"email": "doc_id@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    prof = await client.post("/doctors/profile", json={
        "specialization": "Orthopedics", "license_number": "LIC-ID",
        "years_of_experience": 10, "consultation_fee": 800,
    }, headers={"Authorization": f"Bearer {token}"})
    doctor_id = prof.json()["id"]

    resp = await client.get(f"/doctors/{doctor_id}")
    assert resp.status_code == 200
    assert resp.json()["specialization"] == "Orthopedics"

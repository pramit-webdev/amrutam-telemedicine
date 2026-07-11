import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_by_specialization(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "srch_doc@test.com", "password": "password123", "role": "doctor",
    })
    resp = await client.post("/auth/login", json={"email": "srch_doc@test.com", "password": "password123"})
    token = resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "Ophthalmology", "license_number": "LIC-SRCH",
        "years_of_experience": 6, "consultation_fee": 450,
    }, headers={"Authorization": f"Bearer {token}"})

    resp = await client.get("/doctors/search?specialization=Ophthalmology")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["specialization"] == "Ophthalmology"


@pytest.mark.asyncio
async def test_search_empty_results(client: AsyncClient):
    resp = await client.get("/doctors/search?specialization=NonExistentSpecialtyXYZ")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 0
    assert data["total"] == 0

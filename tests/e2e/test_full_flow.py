import pytest
from httpx import AsyncClient


@pytest.mark.e2e
async def test_user_journey(client: AsyncClient):
    register_resp = await client.post("/auth/register", json={
        "email": "jane@example.com",
        "password": "securepass123",
        "role": "patient",
        "first_name": "Jane",
        "last_name": "Doe",
    })
    assert register_resp.status_code == 200

    login_resp = await client.post("/auth/login", json={
        "email": "jane@example.com",
        "password": "securepass123",
    })
    assert login_resp.status_code == 200
    patient_token = login_resp.json()["access_token"]

    me_resp = await client.get("/users/me", headers={"Authorization": f"Bearer {patient_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "jane@example.com"

    doc_register = await client.post("/auth/register", json={
        "email": "dr.smith@example.com",
        "password": "docpass123",
        "role": "doctor",
        "first_name": "John",
        "last_name": "Smith",
    })
    assert doc_register.status_code == 200

    doc_login = await client.post("/auth/login", json={
        "email": "dr.smith@example.com",
        "password": "docpass123",
    })
    assert doc_login.status_code == 200
    doctor_token = doc_login.json()["access_token"]

    profile_resp = await client.post("/doctors/profile", json={
        "specialization": "Dermatology",
        "license_number": "LIC-E2E-001",
        "years_of_experience": 8,
        "consultation_fee": 500,
    }, headers={"Authorization": f"Bearer {doctor_token}"})
    assert profile_resp.status_code == 200

    slots_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-07-20T10:00:00Z", "end_time": "2026-07-20T10:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doctor_token}"})
    assert slots_resp.status_code == 200
    slot_id = slots_resp.json()[0]["id"]
    doctor_id = slots_resp.json()[0]["doctor_id"]

    search_resp = await client.get("/doctors/search", params={"specialization": "Dermatology"})
    assert search_resp.status_code == 200
    assert len(search_resp.json()["items"]) > 0

    book_resp = await client.post("/bookings", json={
        "slot_id": slot_id,
        "doctor_id": doctor_id,
        "idempotency_key": "e2e-book-001",
    }, headers={"Authorization": f"Bearer {patient_token}"})
    assert book_resp.status_code == 200
    consultation_id = book_resp.json()["consultation_id"]

    pay_resp = await client.post("/payments", json={
        "consultation_id": consultation_id,
        "amount": 500,
        "currency": "INR",
        "idempotency_key": "e2e-pay-001",
    }, headers={"Authorization": f"Bearer {patient_token}"})
    assert pay_resp.status_code == 200
    assert pay_resp.json()["status"] == "completed"

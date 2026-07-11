import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_payment_success(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "pay_pat@test.com", "password": "password123", "role": "patient",
    })
    pat = await client.post("/auth/login", json={"email": "pay_pat@test.com", "password": "password123"})
    pat_token = pat.json()["access_token"]

    await client.post("/auth/register", json={
        "email": "pay_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc = await client.post("/auth/login", json={"email": "pay_doc@test.com", "password": "password123"})
    doc_token = doc.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "General", "license_number": "LIC-PAY",
        "years_of_experience": 3, "consultation_fee": 500,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-08-01T09:00:00Z", "end_time": "2026-08-01T09:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot.json()[0]["id"]
    doctor_id = slot.json()[0]["doctor_id"]

    bk = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "pay-test-bk", "symptoms": "Cough",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    consult_id = bk.json()["consultation_id"]

    resp = await client.post("/payments", json={
        "consultation_id": consult_id, "amount": 500,
        "currency": "INR", "idempotency_key": "pay-test-pay",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["amount"] == 500
    assert resp.json()["currency"] == "INR"

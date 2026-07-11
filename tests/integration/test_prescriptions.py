import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_prescription(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "rx2_pat@test.com", "password": "password123", "role": "patient",
    })
    await client.post("/auth/register", json={
        "email": "rx2_doc@test.com", "password": "password123", "role": "doctor",
    })

    doc = await client.post("/auth/login", json={"email": "rx2_doc@test.com", "password": "password123"})
    doc_token = doc.json()["access_token"]
    pat = await client.post("/auth/login", json={"email": "rx2_pat@test.com", "password": "password123"})
    pat_token = pat.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "General", "license_number": "LIC-RX2",
        "years_of_experience": 2, "consultation_fee": 200,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-08-02T09:00:00Z", "end_time": "2026-08-02T09:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot.json()[0]["id"]
    doctor_id = slot.json()[0]["doctor_id"]

    bk = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "rx2-bk", "symptoms": "Pain",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    cid = bk.json()["consultation_id"]

    await client.post("/payments", json={
        "consultation_id": cid, "amount": 200,
        "currency": "INR", "idempotency_key": "rx2-pay",
    }, headers={"Authorization": f"Bearer {pat_token}"})

    await client.post(f"/consultations/{cid}/start", json={}, headers={"Authorization": f"Bearer {doc_token}"})
    await client.post(f"/consultations/{cid}/complete", json={"notes": "Done"}, headers={"Authorization": f"Bearer {doc_token}"})

    rx = await client.post("/prescriptions", json={
        "consultation_id": cid, "medication_name": "Ibuprofen",
        "dosage": "400mg", "frequency": "Twice daily", "duration": "5 days",
    }, headers={"Authorization": f"Bearer {doc_token}"})
    assert rx.status_code == 200
    assert rx.json()["medication_name"] == "Ibuprofen"

    lst = await client.get(f"/prescriptions/consultation/{cid}", headers={"Authorization": f"Bearer {pat_token}"})
    assert lst.status_code == 200
    assert len(lst.json()) >= 1

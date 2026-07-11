import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_consultation_lifecycle(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "lifecycle_pat@test.com", "password": "password123", "role": "patient",
    })
    pat_resp = await client.post("/auth/login", json={
        "email": "lifecycle_pat@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    await client.post("/auth/register", json={
        "email": "lifecycle_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "lifecycle_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "General", "license_number": "LIC-LIFECYCLE",
        "years_of_experience": 3, "consultation_fee": 100,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-08-10T09:00:00Z", "end_time": "2026-08-10T09:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot_resp.json()[0]["id"]
    doctor_id = slot_resp.json()[0]["doctor_id"]

    book = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "lifecycle-bk", "symptoms": "Checkup",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert book.json()["status"] == "pending_payment"

    cid = book.json()["consultation_id"]

    pay = await client.post("/payments", json={
        "consultation_id": cid, "amount": 100, "currency": "INR",
        "idempotency_key": "lifecycle-pay",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert pay.json()["status"] == "completed"

    get_consult = await client.get(f"/consultations/{cid}",
                                    headers={"Authorization": f"Bearer {pat_token}"})
    assert get_consult.json()["status"] == "confirmed"

    start = await client.post(f"/consultations/{cid}/start", json={},
                               headers={"Authorization": f"Bearer {doc_token}"})
    assert start.json()["status"] == "in_progress"

    complete = await client.post(f"/consultations/{cid}/complete", json={"notes": "All good"},
                                  headers={"Authorization": f"Bearer {doc_token}"})
    assert complete.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_cannot_start_unconfirmed_consultation(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "badstart_pat@test.com", "password": "password123", "role": "patient",
    })
    pat_resp = await client.post("/auth/login", json={
        "email": "badstart_pat@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    await client.post("/auth/register", json={
        "email": "badstart_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "badstart_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "General", "license_number": "LIC-BADSTART",
        "years_of_experience": 3, "consultation_fee": 100,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-08-11T09:00:00Z", "end_time": "2026-08-11T09:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot_resp.json()[0]["id"]
    doctor_id = slot_resp.json()[0]["doctor_id"]

    book = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "badstart-bk", "symptoms": "Pain",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    cid = book.json()["consultation_id"]

    start = await client.post(f"/consultations/{cid}/start", json={},
                               headers={"Authorization": f"Bearer {doc_token}"})
    assert start.status_code == 409

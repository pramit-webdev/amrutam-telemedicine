import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cancel_booking_as_patient(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "cancel_pat@test.com", "password": "password123", "role": "patient",
    })
    pat_resp = await client.post("/auth/login", json={
        "email": "cancel_pat@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    await client.post("/auth/register", json={
        "email": "cancel_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "cancel_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "General", "license_number": "LIC-CANCEL",
        "years_of_experience": 3, "consultation_fee": 150,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-08-01T09:00:00Z", "end_time": "2026-08-01T09:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot_resp.json()[0]["id"]
    doctor_id = slot_resp.json()[0]["doctor_id"]

    book_resp = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "cancel-bk-1", "symptoms": "Pain",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    consult_id = book_resp.json()["consultation_id"]

    cancel_resp = await client.post(f"/bookings/{consult_id}/cancel", json={"reason": "Changed mind"},
                                     headers={"Authorization": f"Bearer {pat_token}"})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_nonexistent_consultation(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "nonexist@test.com", "password": "password123", "role": "patient",
    })
    resp = await client.post("/auth/login", json={
        "email": "nonexist@test.com", "password": "password123",
    })
    token = resp.json()["access_token"]

    from uuid import uuid4
    resp = await client.post(f"/bookings/{uuid4()}/cancel", json={},
                              headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_already_completed_consultation(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "comp_cancel@test.com", "password": "password123", "role": "patient",
    })
    pat_resp = await client.post("/auth/login", json={
        "email": "comp_cancel@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    await client.post("/auth/register", json={
        "email": "comp_cancel_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "comp_cancel_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "General", "license_number": "LIC-COMP-CANCEL",
        "years_of_experience": 3, "consultation_fee": 150,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-08-02T10:00:00Z", "end_time": "2026-08-02T10:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot_resp.json()[0]["id"]
    doctor_id = slot_resp.json()[0]["doctor_id"]

    book = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "comp-cancel-bk", "symptoms": "Fever",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    cid = book.json()["consultation_id"]

    await client.post("/payments", json={
        "consultation_id": cid, "amount": 150, "currency": "INR",
        "idempotency_key": "comp-cancel-pay",
    }, headers={"Authorization": f"Bearer {pat_token}"})

    await client.post(f"/consultations/{cid}/start", json={},
                       headers={"Authorization": f"Bearer {doc_token}"})
    await client.post(f"/consultations/{cid}/complete", json={},
                       headers={"Authorization": f"Bearer {doc_token}"})

    cancel_resp = await client.post(f"/bookings/{cid}/cancel", json={},
                                     headers={"Authorization": f"Bearer {pat_token}"})
    assert cancel_resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_by_doctor(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "doccancel_pat@test.com", "password": "password123", "role": "patient",
    })
    pat_resp = await client.post("/auth/login", json={
        "email": "doccancel_pat@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    await client.post("/auth/register", json={
        "email": "doccancel_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "doccancel_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "General", "license_number": "LIC-DOCCANCEL",
        "years_of_experience": 3, "consultation_fee": 150,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-08-03T11:00:00Z", "end_time": "2026-08-03T11:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot_resp.json()[0]["id"]
    doctor_id = slot_resp.json()[0]["doctor_id"]

    book = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "doccancel-bk", "symptoms": "Cough",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    cid = book.json()["consultation_id"]

    cancel_resp = await client.post(f"/bookings/{cid}/cancel", json={"reason": "Doctor unavailable"},
                                     headers={"Authorization": f"Bearer {doc_token}"})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_booking_flow(client: AsyncClient):
    # Register patient
    await client.post("/auth/register", json={
        "email": "flow_pat@test.com", "password": "password123",
        "role": "patient", "first_name": "Flow", "last_name": "Patient",
    })
    pat_resp = await client.post("/auth/login", json={
        "email": "flow_pat@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    # Register doctor
    await client.post("/auth/register", json={
        "email": "flow_doc@test.com", "password": "password123",
        "role": "doctor", "first_name": "Flow", "last_name": "Doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "flow_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    # Create doctor profile
    prof_resp = await client.post("/doctors/profile", json={
        "specialization": "Neurology", "license_number": "LIC-FLOW",
        "years_of_experience": 8, "consultation_fee": 400,
    }, headers={"Authorization": f"Bearer {doc_token}"})
    assert prof_resp.status_code == 200

    # Add slot
    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-07-20T10:00:00Z", "end_time": "2026-07-20T10:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    assert slot_resp.status_code == 200
    slot_data = slot_resp.json()
    slot_id = slot_data[0]["id"]
    doctor_id = slot_data[0]["doctor_id"]

    # Book slot
    book_resp = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "flow-bk-1", "symptoms": "Headache",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert book_resp.status_code == 200
    consult_id = book_resp.json()["consultation_id"]
    assert book_resp.json()["status"] == "pending_payment"

    # Process payment
    pay_resp = await client.post("/payments", json={
        "consultation_id": consult_id, "amount": 400,
        "currency": "INR", "idempotency_key": "flow-pay-1",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert pay_resp.status_code == 200
    assert pay_resp.json()["status"] == "completed"

    # Start consultation
    start_resp = await client.post(f"/consultations/{consult_id}/start", json={},
                                   headers={"Authorization": f"Bearer {doc_token}"})
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "in_progress"

    # Complete consultation
    complete_resp = await client.post(f"/consultations/{consult_id}/complete", json={"notes": "Patient recovered"},
                                      headers={"Authorization": f"Bearer {doc_token}"})
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"

    # Verify patient consultations list
    cons_list = await client.get("/consultations", headers={"Authorization": f"Bearer {pat_token}"})
    assert cons_list.status_code == 200
    assert len(cons_list.json()) >= 1


@pytest.mark.asyncio
async def test_double_booking_prevention(client: AsyncClient):
    # Setup
    await client.post("/auth/register", json={
        "email": "db_pat@test.com", "password": "password123", "role": "patient",
    })
    pat_resp = await client.post("/auth/login", json={
        "email": "db_pat@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    await client.post("/auth/register", json={
        "email": "db_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "db_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "Dermatology", "license_number": "LIC-DB",
        "years_of_experience": 3, "consultation_fee": 200,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-07-25T14:00:00Z", "end_time": "2026-07-25T14:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot_resp.json()[0]["id"]
    doctor_id = slot_resp.json()[0]["doctor_id"]

    # First booking - should succeed
    bk1 = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "db-bk-1", "symptoms": "Rash",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert bk1.status_code == 200

    # Second booking - same slot, different patient, different key → should fail
    await client.post("/auth/register", json={
        "email": "db_pat2@test.com", "password": "password123", "role": "patient",
    })
    pat2_resp = await client.post("/auth/login", json={
        "email": "db_pat2@test.com", "password": "password123",
    })
    pat2_token = pat2_resp.json()["access_token"]

    bk2 = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "db-bk-2", "symptoms": "Itching",
    }, headers={"Authorization": f"Bearer {pat2_token}"})
    assert bk2.status_code == 409


@pytest.mark.asyncio
async def test_idempotent_payment(client: AsyncClient):
    await client.post("/auth/register", json={
        "email": "idem_pat@test.com", "password": "password123", "role": "patient",
    })
    pat_resp = await client.post("/auth/login", json={
        "email": "idem_pat@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    await client.post("/auth/register", json={
        "email": "idem_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "idem_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    await client.post("/doctors/profile", json={
        "specialization": "ENT", "license_number": "LIC-IDEM",
        "years_of_experience": 4, "consultation_fee": 250,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-07-25T15:00:00Z", "end_time": "2026-07-25T15:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot_resp.json()[0]["id"]
    doctor_id = slot_resp.json()[0]["doctor_id"]

    book_resp = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "idem-bk-1", "symptoms": "Ear pain",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    consult_id = book_resp.json()["consultation_id"]

    # First payment
    pay1 = await client.post("/payments", json={
        "consultation_id": consult_id, "amount": 250,
        "currency": "INR", "idempotency_key": "idem-pay-1",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert pay1.status_code == 200
    assert pay1.json()["status"] == "completed"

    # Same idempotency key - should return same result
    pay2 = await client.post("/payments", json={
        "consultation_id": consult_id, "amount": 250,
        "currency": "INR", "idempotency_key": "idem-pay-1",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    assert pay2.status_code == 200
    assert pay2.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_prescription_flow(client: AsyncClient):
    # Setup - register users
    for u in [("rx_pat@test.com", "patient"), ("rx_doc@test.com", "doctor")]:
        await client.post("/auth/register", json={
            "email": u[0], "password": "password123", "role": u[1],
        })

    doc_resp = await client.post("/auth/login", json={
        "email": "rx_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]

    pat_resp = await client.post("/auth/login", json={
        "email": "rx_pat@test.com", "password": "password123",
    })
    pat_token = pat_resp.json()["access_token"]

    # Doctor profile
    await client.post("/doctors/profile", json={
        "specialization": "General", "license_number": "LIC-RX",
        "years_of_experience": 2, "consultation_fee": 100,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    slot_resp = await client.post("/doctors/slots", json={
        "slots": [{"start_time": "2026-07-25T16:00:00Z", "end_time": "2026-07-25T16:30:00Z"}]
    }, headers={"Authorization": f"Bearer {doc_token}"})
    slot_id = slot_resp.json()[0]["id"]
    doctor_id = slot_resp.json()[0]["doctor_id"]

    # Book and pay
    bk = await client.post("/bookings", json={
        "doctor_id": doctor_id, "slot_id": slot_id,
        "idempotency_key": "rx-bk-1", "symptoms": "Fever",
    }, headers={"Authorization": f"Bearer {pat_token}"})
    cid = bk.json()["consultation_id"]

    await client.post("/payments", json={
        "consultation_id": cid, "amount": 100,
        "currency": "INR", "idempotency_key": "rx-pay-1",
    }, headers={"Authorization": f"Bearer {pat_token}"})

    await client.post(f"/consultations/{cid}/start", json={},
                      headers={"Authorization": f"Bearer {doc_token}"})
    await client.post(f"/consultations/{cid}/complete", json={"notes": "Prescribed medication"},
                      headers={"Authorization": f"Bearer {doc_token}"})

    # Create prescription
    rx_resp = await client.post("/prescriptions", json={
        "consultation_id": cid,
        "medication_name": "Paracetamol",
        "dosage": "500mg",
        "frequency": "3 times a day",
        "duration": "5 days",
        "notes": "After meals",
    }, headers={"Authorization": f"Bearer {doc_token}"})
    assert rx_resp.status_code == 200
    rx_data = rx_resp.json()
    assert rx_data["medication_name"] == "Paracetamol"

    # List prescriptions
    list_resp = await client.get(f"/prescriptions/consultation/{cid}",
                                  headers={"Authorization": f"Bearer {pat_token}"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


@pytest.mark.asyncio
async def test_doctor_search(client: AsyncClient):
    # Register a doctor first
    await client.post("/auth/register", json={
        "email": "search_doc@test.com", "password": "password123", "role": "doctor",
    })
    doc_resp = await client.post("/auth/login", json={
        "email": "search_doc@test.com", "password": "password123",
    })
    doc_token = doc_resp.json()["access_token"]
    await client.post("/doctors/profile", json={
        "specialization": "Cardiology", "license_number": "LIC-SRCH",
        "years_of_experience": 5, "consultation_fee": 300,
    }, headers={"Authorization": f"Bearer {doc_token}"})

    resp = await client.get("/doctors/search?specialization=Cardio")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert "Cardio" in data["items"][0]["specialization"]

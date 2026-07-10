# Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐
│     User     │       │    Profile       │
│──────────────│       │──────────────────│
│ id (PK, UUID)│1────1│ id (PK, UUID)    │
│ email (UQ)   │       │ user_id (FK, UQ) │
│ phone        │       │ first_name       │
│ password_hash│       │ last_name        │
│ role (enum)  │       │ date_of_birth    │
│ is_active    │       │ gender           │
│ created_at   │       │ address          │
│ updated_at   │       │ avatar_url       │
│ mfa_enabled  │       │ created_at       │
│ mfa_secret   │       └──────────────────┘
└──────┬───────┘       └──────────────────┘
       │
       │ 1
       │
       ▼
┌──────────────────┐       ┌──────────────────┐
│     Doctor       │       │ Prescription     │
│──────────────────│       │──────────────────│
│ id (PK, UUID)   │1───*  │ id (PK, UUID)    │
│ user_id (FK, UQ)│       │ consultation_id  │
│ specialization   │       │ doctor_id (FK)   │
│ license_number   │       │ medication_name  │
│ years_of_exp     │       │ dosage           │
│ consultation_fee │       │ frequency        │
│ average_rating   │       │ duration         │
│ bio              │       │ notes            │
│ is_available     │       │ created_at       │
│ created_at       │       └──────────────────┘
│ updated_at       │
└──────┬───────────┘
       │
       │ 1
       │
       ▼
┌──────────────────┐       ┌──────────────────┐
│ AvailabilitySlot │       │ Consultation     │
│──────────────────│       │──────────────────│
│ id (PK, UUID)   │───*  │ id (PK, UUID)   │
│ doctor_id (FK)  │       │ patient_id (FK)  │
│ start_time       │       │ doctor_id (FK)   │
│ end_time         │       │ slot_id (FK)     │
│ is_booked        │       │ status (enum)    │
│ version          │       │ symptoms         │
│ created_at       │       │ notes            │
│ updated_at       │       │ idempotency_key  │
└──────────────────┘       │ started_at       │
                            │ ended_at         │
┌──────────────────┐       │ created_at       │
│    Payment       │       │ updated_at       │
│──────────────────│       └──────────────────┘
│ id (PK, UUID)   │
│ consultation_id  │
│ patient_id (FK)  │       ┌──────────────────┐
│ amount           │       │   AuditLog       │
│ currency         │       │──────────────────│
│ status (enum)    │       │ id (PK, UUID)    │
│ payment_method   │       │ user_id (FK)     │
│ idempotency_key  │       │ action           │
│ created_at       │       │ entity_type      │
│ updated_at       │       │ entity_id        │
└──────────────────┘       │ old_values (JSON)│
                            │ new_values (JSON)│
                            │ ip_address       │
                            │ user_agent       │
                            │ created_at       │
                            └──────────────────┘
                           │ details (JSONB)  │
                           │ ip_address       │
                           │ user_agent       │
                           │ created_at       │
                           └──────────────────┘
```

## Relationships

| From | To | Type | Constraint |
|---|---|---|---|
| User | Profile | 1:1 | `user_id` unique FK |
| User | Doctor | 1:1 | `user_id` unique FK |
| User | Consultation (as patient) | 1:∞ | `patient_id` FK |
| User | Payment | 1:∞ | `user_id` FK |
| User | AuditLog | 1:∞ | `user_id` FK |
| Doctor | AvailabilitySlot | 1:∞ | `doctor_id` FK |
| Doctor | Consultation | 1:∞ | `doctor_id` FK |
| Doctor | Prescription | 1:∞ | `doctor_id` FK |
| AvailabilitySlot | Consultation | 1:1 | `slot_id` FK (unique) |
| Consultation | Payment | 1:1 | `consultation_id` FK (unique) |
| Consultation | Prescription | 1:∞ | `consultation_id` FK |

## Indexes

| Table | Index | Type | Purpose |
|---|---|---|---|
| users | `idx_users_email` | UNIQUE B-tree | Login lookup |
| users | `idx_users_role` | B-tree | Role filtering |
| doctors | `idx_doctors_specialization` | B-tree | Search by specialization |
| doctors | `idx_doctors_fee` | B-tree | Fee range filtering |
| availability_slots | `idx_slots_doctor_time` | B-tree (composite) | Slot availability lookup |
| availability_slots | `idx_slots_booked` | Partial B-tree | Unbooked slots only |
| consultations | `idx_consultations_patient` | B-tree | Patient history |
| consultations | `idx_consultations_doctor` | B-tree | Doctor calendar |
| consultations | `idx_consultations_status` | B-tree | Status-based queries |
| consultations | `idx_consultations_idempotency` | UNIQUE B-tree | Idempotency enforcement |
| payments | `idx_payments_consultation` | UNIQUE B-tree | Payment lookup |
| payments | `idx_payments_idempotency` | UNIQUE B-tree | Idempotency enforcement |
| audit_logs | `idx_audit_user` | B-tree | User audit trail |
| audit_logs | `idx_audit_resource` | B-tree | Resource change history |
| audit_logs | `idx_audit_created` | BRIN | Time-range queries |

## Table Sizes (Estimate @ 100k consultations)

| Table | Rows | Size |
|---|---|---|
| users | 150,000 | ~30 MB |
| profiles | 150,000 | ~150 MB |
| doctors | 50,000 | ~20 MB |
| availability_slots | 500,000 | ~80 MB |
| consultations | 100,000 | ~100 MB |
| payments | 100,000 | ~30 MB |
| prescriptions | 300,000 | ~50 MB |
| audit_logs | 1,000,000 | ~500 MB |

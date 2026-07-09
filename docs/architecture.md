# Architecture Document — Amrutam Telemedicine

## 1. High-Level Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────────────────┐
│   Mobile     │     │    Web       │     │               API Gateway                    │
│   App        │────▶│   Client     │────▶│        (FastAPI + Middleware)                 │
│              │     │              │     │  Rate Limit │ Auth │ Request ID │ CORS       │
└──────────────┘     └──────────────┘     └────────────────────┬─────────────────────────┘
                                                              │
                                              ┌───────────────┼───────────────┐
                                              ▼               ▼               ▼
                                   ┌─────────────────┐ ┌─────────┐ ┌──────────────┐
                                   │  Modular Monolith│ │  Redis  │ │  Async Job   │
                                   │  (FastAPI App)   │ │  Cache  │ │  Workers     │
                                   │                  │ │  + Rate │ │  (arq)       │
                                   │  ┌───────────┐   │ │  Limit  │ │              │
                                   │  │ Auth Module│   │ └─────────┘ │ - Expiry    │
                                   │  │ Users Mod │   │             │ - Notify    │
                                   │  │ Doctors   │   │             │ - Analytics │
                                   │  │ Bookings  │   │             └──────────────┘
                                   │  │ Consult   │   │
                                   │  │ Payments  │   │
                                   │  │ Prescript │   │
                                   │  │ Search    │   │
                                   │  │ Analytics │   │
                                   │  │ Audit     │   │
                                   │  └───────────┘   │
                                   └────────┬─────────┘
                                            │
                                            ▼
                                   ┌────────────────┐
                                   │   PostgreSQL   │
                                   │   (Primary)    │
                                   │                │
                                   │ users          │
                                   │ profiles       │
                                   │ doctors        │
                                   │ avail_slots    │
                                   │ consultations  │
                                   │ prescriptions  │
                                   │ payments       │
                                   │ audit_logs     │
                                   └────────────────┘
```

## 2. Data Flow — Booking

```
Patient                   API                        DB                    Redis
   │                       │                         │                      │
   │── GET /search ────────│─────────────────────────│──────────────────────│──┐
   │                       │                         │                      │  │ Cache
   │                       │                         │                      │◀─┘
   │◀─────── results ──────│─────────────────────────│──────────────────────│
   │                       │                         │                      │
   │── POST /bookings ─────│─ Check idempotency key ─│──────────────────────│──┐
   │   {idempotency_key}   │                         │                      │  │ Check
   │                       │─ SELECT slot FOR UPDATE─│──────────────────────│◀─┘
   │                       │                         │── lock acquired ─────│
   │                       │─ INSERT consultation ───│──────────────────────│
   │                       │─ UPDATE slot booked ────│──────────────────────│
   │◀────── 201 Created ───│─────────────────────────│──────────────────────│
   │                       │                         │                      │
   │── POST /payments ─────│─ Check idempotency ─────│──────────────────────│
   │                       │─ UPDATE consult status  │── confirmed ────────│
   │◀────── 200 OK ────────│─────────────────────────│──────────────────────│
```

## 3. Scaling Strategy

### Reads (target p95 <200ms)
- Redis cache for doctor search results (TTL 5 min)
- Redis cache for availability slots (TTL 1 min)
- Database read replicas for analytics queries
- Connection pooling (20 pool / 10 overflow)

### Writes (target p95 <500ms)
- Async SQLAlchemy sessions (non-blocking I/O)
- Event loop handles multiple concurrent writes
- Optimistic locking with `version` column on slots
- Idempotency keys prevent duplicate writes

### Data Partitioning
- `availability_slots`: Range partition by month on `start_time`
- `consultations`: Range partition by month on `created_at`
- `audit_logs`: Range partition by month on `created_at`
- `payments`: Range partition by month on `created_at`

### Caching Strategy
| Data | Cache | TTL | Invalidation |
|---|---|---|---|
| Doctor search results | Redis | 5 min | On profile update |
| Available slots | Redis | 1 min | On booking/cancel |
| User sessions | Redis JWT | 15 min | On logout |

## 4. Concurrency Handling

### Slot Booking (Critical Section)
```python
# Pessimistic lock prevents race conditions
slot = await session.execute(
    select(AvailabilitySlot).where(
        AvailabilitySlot.id == slot_id,
        AvailabilitySlot.is_booked == False
    ).with_for_update()  # ← Row-level lock
)
```

### Optimistic Locking
```python
# version column prevents lost updates
UPDATE availability_slots
SET is_booked = true, version = version + 1
WHERE id = $1 AND version = $2
```

## 5. Transaction Management

### Saga Pattern — Booking Flow
```
1. Create Consultation (pending_payment)     → compensation: release slot
2. Process Payment (completed)               → compensation: refund + cancel
3. Start Consultation (in_progress)
4. Complete Consultation (completed)
```

### Compensation Actions
- Payment failure → release slot, cancel consultation
- Booking timeout (15 min unpaid) → release slot, cancel consultation

## 6. Retry & Backoff Strategy

| Operation | Max Retries | Backoff | Jitter |
|---|---|---|---|
| DB connection | 3 | Exponential (1s, 2s, 4s) | ±100ms |
| Payment processing | 3 | Exponential (100ms, 200ms, 400ms) | ±50ms |
| Cache connection | 3 | Exponential (500ms, 1s, 2s) | ±100ms |
| External notification | 5 | Exponential (1s, 2s, 4s, 8s, 16s) | ±200ms |

## 7. Backup & Disaster Recovery

### Backup Schedule
- **Full backup**: Daily at 02:00 UTC (pg_dump)
- **WAL archiving**: Continuous (for point-in-time recovery)
- **Retention**: 30 days daily, 12 monthly

### Recovery
- **RPO**: <1 hour (WAL archiving)
- **RTO**: <4 hours (full restore from backup)
- **Procedure**: Restore latest full backup + replay WAL

### DR Strategy
- Multi-AZ deployment (AWS RDS or Neon)
- Read replicas in different AZ
- Automated failover (10-30s downtime)

## 8. Module Dependencies

```
auth ──→ users
users ──→ (none)
doctors ──→ users
bookings ──→ doctors, consultations
consultations ──→ doctors, users
payments ──→ consultations
prescriptions ──→ consultations, doctors
search ──→ doctors
analytics ──→ consultations, payments
audit ──→ (none, standalone)
```

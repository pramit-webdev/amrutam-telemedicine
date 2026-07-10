# Amrutam Telemedicine — Project Documentation

> v0.1.0 — Jul 11, 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [System Architecture](#3-system-architecture)
4. [Data Model](#4-data-model)
5. [API Reference](#5-api-reference)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Background Jobs (arq)](#7-background-jobs-arq)
8. [Observability](#8-observability)
9. [Deployment](#9-deployment)
10. [Development Guide](#10-development-guide)
11. [Testing Strategy](#11-testing-strategy)
12. [Production Checklist](#12-production-checklist)

---

## 1. Project Overview

Amrutam Telemedicine is a production-grade modular monolith backend for connecting patients with doctors. It handles the full lifecycle: search → book → pay → consult → prescribe → analytics.

### Key Features

- **Patient**: Register, search doctors, book slots, pay, attend consultations, get prescriptions
- **Doctor**: Manage profile, set availability, accept consultations, write prescriptions
- **Admin**: Oversight, refunds, analytics
- **All**: MFA via TOTP, audit trail, rate limiting

### Design Principles

| Principle | Implementation |
|---|---|
| Secure by default | bcrypt, JWT with jti, RBAC, rate limiting, input validation |
| Resilient | Retry with backoff, idempotency keys, pessimistic locking |
| Observable | Structured logging, Prometheus metrics, OpenTelemetry tracing |
| Testable | Integration tests with ephemeral DB, unit tests, E2E flow |
| Production-ready | Docker, CI/CD, health checks, env-based config |

---

## 2. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.12 |
| Web Framework | FastAPI | 0.115+ |
| ASGI Server | Uvicorn | 0.34+ |
| ORM | SQLAlchemy 2.0 (async) | 2.0+ |
| DB Driver | asyncpg | 0.30+ |
| Migrations | Alembic | 1.14+ |
| Cache | Redis | 7.x |
| Job Queue | arq | 0.27+ |
| Auth | python-jose + bcrypt + pyotp | — |
| Validation | Pydantic v2 | 2.10+ |
| Rate Limiting | slowapi (slowapi) | 0.1.9+ |
| Retry | tenacity | 9.1+ |
| Metrics | Prometheus (prometheus-fastapi-instrumentator) | 7.0+ |
| Tracing | OpenTelemetry | 1.30+ |
| Logging | structlog | 25.1+ |
| Package Manager | uv | latest |
| Container | Docker + Compose | — |
| CI | GitHub Actions | — |
| Hosting | Render (web + PostgreSQL) | — |

---

## 3. System Architecture

### 3.1 High-Level Diagram

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│   Client    │────▶│            FastAPI Application           │
│  (Mobile /  │     │                                          │
│   Web)      │     │  ┌─────────┐ ┌────────┐ ┌────────────┐  │
└─────────────┘     │  │ CORS    │ │ Rate   │ │ Request ID │  │
                    │  │ Middle  │ │ Limiter│ │ Logging    │  │
                    │  └─────────┘ └────────┘ └────────────┘  │
                    │                                          │
                    │  ┌──────────────────────────────────────┐│
                    │  │         Module Layer                 ││
                    │  │  Auth│Users│Doctors│Bookings│Consult  ││
                    │  │  Payments│Prescriptions│Search│Audit  ││
                    │  │  Analytics                            ││
                    │  └──────────────────────────────────────┘│
                    │                                          │
                    │  ┌──────────────────────────────────────┐│
                    │  │          Common Layer                ││
                    │  │  Exceptions│Pagination│Retry│Middleware│
                    │  └──────────────────────────────────────┘│
                    └──────────────────┬───────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌──────────────┐   ┌──────────┐   ┌─────────────────┐
            │  PostgreSQL  │   │  Redis   │   │   arq Workers   │
            │  (Primary)   │   │  Cache / │   │                 │
            │              │   │  Rate    │   │ - Expire Pending│
            │  8 tables    │   │  Limit   │   │ - Send Reminder │
            │              │   │  Queue   │   │ - Aggregate     │
            └──────────────┘   └──────────┘   └─────────────────┘
```

### 3.2 Module Dependency Graph

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
audit ──→ (standalone)
```

### 3.3 Request Lifecycle

```
HTTP Request
    │
    ▼
CORSMiddleware ──▶ RequestLoggingMiddleware ──▶ SlowAPIMiddleware
    │                                                │
    │                                         ┌──────┘
    ▼                                         ▼
FastAPI Router ──▶ Dependency Injection ──▶ Module Service ──▶ DB
                      │                       │
                      │                       ├── Audit Log
                      │                       ├── Return response
                      ▼                       ▼
                 RBAC Check              JSON Response
```

### 3.4 Booking Flow (Saga Pattern)

```
Step 1: POST /bookings (idempotency_key)
    └── Create Consultation (status: PENDING_PAYMENT)
    └── Lock slot (SELECT FOR UPDATE)
    └── Mark slot as booked
    └── Compensation: release slot if payment fails

Step 2: POST /payments (idempotency_key)
    └── Process payment
    └── Update Consultation (status: CONFIRMED)
    └── Compensation: refund + cancel if downstream fails

Step 3: PATCH /consultations/{id}/start
    └── Update Consultation (status: IN_PROGRESS)

Step 4: PATCH /consultations/{id}/complete
    └── Update Consultation (status: COMPLETED)
```

### 3.5 Concurrency Model

| Scenario | Mechanism |
|---|---|
| Double booking | `SELECT ... FOR UPDATE` (pessimistic row lock) |
| Lost update | `version` column on slots (optimistic lock) |
| Duplicate payment | Idempotency key (UNIQUE constraint) |
| Race on register | Email unique constraint (DB-level) |

---

## 4. Data Model

### 4.1 Entity Relationship

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
│ mfa_enabled  │       │ address          │
│ mfa_secret   │       │ avatar_url       │
│ created_at   │       └──────────────────┘
│ updated_at   │
└──────┬───────┘
       │ 1
       │
       ▼
┌──────────────────┐       ┌──────────────────┐
│     Doctor       │       │  Prescription    │
│──────────────────│       │──────────────────│
│ id (PK, UUID)   │1───*  │ id (PK, UUID)   │
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
       │ 1
       │
       ▼
┌──────────────────┐       ┌──────────────────┐
│ AvailabilitySlot │       │  Consultation    │
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
│ consultation_id  │       ┌──────────────────┐
│ patient_id (FK)  │       │   AuditLog       │
│ amount           │       │──────────────────│
│ currency         │       │ id (PK, UUID)    │
│ status (enum)    │       │ user_id (FK)     │
│ payment_method   │       │ action           │
│ idempotency_key  │       │ entity_type      │
│ created_at       │       │ entity_id        │
│ updated_at       │       │ old_values (JSONB)│
└──────────────────┘       │ new_values (JSONB)│
                            │ details (JSONB)  │
                            │ ip_address       │
                            │ user_agent       │
                            │ created_at       │
                            └──────────────────┘
```

### 4.2 Enums

```python
class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"

class ConsultationStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
```

### 4.3 Key Indexes

| Table | Index | Type |
|---|---|---|
| users | `idx_users_email` | UNIQUE B-tree |
| users | `idx_users_role` | B-tree |
| doctors | `idx_doctors_specialization` | B-tree |
| doctors | `idx_doctors_fee` | B-tree |
| availability_slots | `idx_slots_doctor_time` | Composite B-tree |
| consultations | `idx_consultations_idempotency` | UNIQUE B-tree |
| consultations | `idx_consultations_status` | B-tree |
| payments | `idx_payments_idempotency` | UNIQUE B-tree |
| audit_logs | `idx_audit_created` | BRIN |

### 4.4 Estimated Table Sizes (100k consultations)

| Table | Rows | Size |
|---|---|---|
| users | 150k | ~30 MB |
| profiles | 150k | ~150 MB |
| doctors | 50k | ~20 MB |
| availability_slots | 500k | ~80 MB |
| consultations | 100k | ~100 MB |
| payments | 100k | ~30 MB |
| prescriptions | 300k | ~50 MB |
| audit_logs | 1M | ~500 MB |

---

## 5. API Reference

### 5.1 Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/db-check` | Database connectivity check |

**`GET /health`** → `200 {"status": "ok", "service": "amrutam-telemedicine"}`

**`GET /db-check`** → `200 {"db": "ok", "result": 1}` on success, `500 {"db": "error", ...}` on failure

---

### 5.2 Auth

All endpoints are unauthenticated.

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login, returns JWT tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/mfa/setup` | Enable MFA (returns TOTP URI) |
| POST | `/auth/mfa/verify` | Verify TOTP code |

**`POST /auth/register`**

```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "role": "patient",
  "first_name": "John",
  "last_name": "Doe"
}
```

→ `201 {"id": "uuid", "email": "...", "role": "patient"}`

**`POST /auth/login`**

```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

→ `200 {"access_token": "...", "refresh_token": "...", "token_type": "bearer", "mfa_required": false}`

If MFA required → `200 {"mfa_required": true, "mfa_token": "..."}` (submit to `/auth/mfa/verify`)

---

### 5.3 Users

Requires authentication.

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Any | Current user profile |
| PUT | `/users/me` | Any | Update profile |

---

### 5.4 Doctors

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/doctors/profile` | Doctor | Create/update doctor profile |
| GET | `/doctors/profile` | Doctor | Get own profile |
| GET | `/doctors/{doctor_id}` | Any | Get doctor by ID |
| GET | `/doctors/search` | Any | Search doctors |
| POST | `/doctors/slots` | Doctor | Add availability slots |
| GET | `/doctors/slots/{doctor_id}` | Any | Get slots for a doctor |

**Search params**: `specialization`, `min_rating`, `max_fee`, `available_only`, `query`, `page`, `size`

---

### 5.5 Bookings

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/bookings` | Patient | Book a slot |
| POST | `/bookings/{id}/cancel` | Patient | Cancel a booking |

**`POST /bookings`**

```json
{
  "slot_id": "uuid",
  "symptoms": "Chest pain",
  "idempotency_key": "client-generated-uuid"
}
```

→ `201 { "id": "uuid", "status": "pending_payment", ... }`

---

### 5.6 Payments

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/payments` | Patient | Process payment |
| POST | `/payments/{id}/refund` | Admin | Refund payment |

**`POST /payments`**

```json
{
  "consultation_id": "uuid",
  "amount": 300.00,
  "currency": "INR",
  "payment_method": "card",
  "idempotency_key": "client-generated-uuid"
}
```

---

### 5.7 Consultations

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/consultations` | Any | List consultations (paginated) |
| PATCH | `/consultations/{id}/start` | Doctor | Start consultation |
| PATCH | `/consultations/{id}/complete` | Doctor | Complete consultation |

**Pagination**: `GET /consultations?page=1&size=20`

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "size": 20,
  "total_pages": 3
}
```

---

### 5.8 Prescriptions

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/prescriptions` | Doctor | Create prescription |
| GET | `/prescriptions?consultation_id=uuid` | Any | List prescriptions |

---

### 5.9 Analytics

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/analytics/consultations` | Admin | Consultation statistics |
| GET | `/analytics/revenue` | Admin | Revenue data |
| GET | `/analytics/top-doctors` | Admin | Top doctors ranking |

---

### 5.10 Audit

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/audit` | Admin | List audit log entries |
| GET | `/audit?user_id=uuid&entity_type=consultation` | Admin | Filtered audit trail |

---

### 5.11 Search

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/search/doctors` | Any | Search doctors (cached) |

---

## 6. Authentication & Authorization

### 6.1 Token Strategy

- **Access Token**: JWT, 15 min expiry, contains `sub` (user_id), `role`, `jti`, `type: "access"`
- **Refresh Token**: JWT, 7 day expiry, contains `sub`, `jti`, `type: "refresh"`
- **Token Rotation**: Each refresh generates new tokens; old refresh token is invalidated
- **JWT ID (jti)**: Unique per token, enables revocation tracking

### 6.2 Password Security

- Algorithm: bcrypt with cost factor 12
- Min length: 8 characters (validated at schema level)
- Max length: 128 characters

### 6.3 MFA

- Algorithm: TOTP (RFC 6238), 30-second window
- Compatible with: Google Authenticator, Authy, 1Password
- Setup returns provisioning URI (QR code compatible)
- Optional per user; enforced by the application

### 6.4 RBAC

| Role | Permissions |
|---|---|
| patient | Create bookings, view own consultations, make payments |
| doctor | Manage profile, manage slots, start/complete consultations, write prescriptions |
| admin | View analytics, refund payments, view audit logs |

### 6.5 Rate Limiting

| Scope | Limit | Storage |
|---|---|---|
| General API | 100 req/min | Redis (prod) / Memory (dev) |
| Auth endpoints | 10 req/min per IP | Memory (always) |

Rate limiter auto-disables in `testing` environment.

---

## 7. Background Jobs (arq)

### 7.1 Worker Configuration

```python
class WorkerSettings:
    functions = [expire_pending_consultations, send_reminder, aggregate_analytics]
    redis_settings = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    poll_delay = 10       # seconds
    max_tasks = 10         # concurrent tasks
    keep_result_seconds = 3600
```

### 7.2 Tasks

| Task | Schedule | Description |
|---|---|---|
| `expire_pending_consultations` | Every poll cycle | Cancel consultations unpaid after 15 min |
| `send_reminder` | On demand | Send consultation reminder |
| `aggregate_analytics` | Every poll cycle | Compute consultation counts |

### 7.3 Running

```bash
# Start worker
uv run arq app.worker.WorkerSettings

# In Docker
docker compose up worker
```

---

## 8. Observability

### 8.1 Logging (structlog)

- **Development**: Colored console output (`ConsoleRenderer`)
- **Production**: Structured JSON (`JSONRenderer`)
- **Fields**: `timestamp`, `level`, `event`, `method`, `path`, `status_code`, `duration_ms`, `request_id`

Every request gets a unique `X-Request-ID` header, correlated in logs.

### 8.2 Metrics (Prometheus)

| Metric | Type | Labels | Description |
|---|---|---|---|
| `http_requests_total` | Counter | method, path, status | Total request count |
| `http_request_duration_seconds` | Histogram | method, path | Request latency distribution |

Endpoint: `GET /metrics` (disabled in production via `ENABLE_METRICS=false` to avoid crashes on Render free tier).

### 8.3 Tracing (OpenTelemetry)

- **Provider**: `OTLPSpanExporter` (gRPC)
- **Instrumentation**: FastAPI routes, SQLAlchemy queries
- **Endpoint**: Configurable via `OTEL_EXPORTER_OTLP_ENDPOINT`
- **Safe**: Tracing module gracefully degrades if packages not installed or endpoint not set

---

## 9. Deployment

### 9.1 Render (Current)

| Component | Plan | Region |
|---|---|---|
| Web Service | Free | Oregon |
| PostgreSQL | Free (expires Aug 9, 2026) | Oregon |

**URL**: https://amrutam-telemedicine.onrender.com

### 9.2 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | Yes | 256-bit random secret |
| `ENVIRONMENT` | Yes | `production`, `development`, or `testing` |
| `CORS_ORIGINS` | No | JSON array of allowed origins (default: `["*"]`) |
| `REDIS_URL` | No | Redis connection string for rate limiting + jobs |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | OpenTelemetry gRPC endpoint |
| `ENABLE_METRICS` | No | Enable Prometheus metrics (default: `true`) |
| `ENABLE_TRACING` | No | Enable OpenTelemetry tracing (default: `false`) |

### 9.3 Docker

```bash
# Build and run
docker compose -f infrastructure/docker-compose.yml up -d

# Production build
docker build -t amrutam-api .

# Run production
docker run -p 8000:8000 --env-file .env amrutam-api
```

### 9.4 Docker Compose Services

| Service | Image | Dependencies |
|---|---|---|
| api | Build from Dockerfile | db, redis |
| db | postgres:16-alpine | — |
| redis | redis:7-alpine | — |
| worker | Build from Dockerfile | db, redis |

---

## 10. Development Guide

### 10.1 Prerequisites

- Python 3.12+
- `uv` (package manager)
- PostgreSQL 16 (via Docker or native)
- Redis 7 (optional, for rate limiting)

### 10.2 Setup

```bash
# Clone
git clone https://github.com/pramit-webdev/amrutam-telemedicine.git
cd amrutam-telemedicine

# Create venv and install deps
uv sync --extra dev

# Start infra
docker compose -f infrastructure/docker-compose.yml up -d

# Run migrations
uv run alembic upgrade head

# Run tests
PYTHONPATH=$PWD ENABLE_METRICS=false uv run pytest tests/ -v

# Start dev server (hot reload)
PYTHONPATH=$PWD ENABLE_METRICS=false uv run uvicorn app.main:app --reload
```

### 10.3 Project Structure

```
amrutam-telemedicine/
├── app/
│   ├── main.py                    # App entry point
│   ├── models.py                  # Barrel import
│   ├── core/
│   │   ├── config.py              # Settings from env
│   │   ├── database.py            # Async engine + sessions
│   │   ├── security.py            # bcrypt, JWT, TOTP
│   │   ├── cache.py               # Redis client
│   │   ├── base.py                # Declarative Base
│   │   └── dependencies.py        # DI (auth, roles)
│   ├── common/
│   │   ├── exceptions.py          # HTTP exception classes
│   │   ├── middleware.py          # Request logging
│   │   ├── pagination.py          # PaginatedResponse
│   │   ├── rate_limit.py          # Env-aware rate limiter
│   │   ├── retry.py               # tenacity presets
│   │   └── errors.py              # Global handlers
│   ├── modules/
│   │   ├── auth/                  # Register, login, MFA, refresh
│   │   ├── users/                 # User model + profile
│   │   ├── doctors/               # Doctor profile + slots
│   │   ├── bookings/              # Booking + cancellation
│   │   ├── consultations/         # Lifecycle management
│   │   ├── payments/              # Payment + refund
│   │   ├── prescriptions/         # Prescription CRUD
│   │   ├── search/                # Doctor search
│   │   ├── analytics/             # Stats + revenue
│   │   └── audit/                 # Audit trail
│   └── monitoring/
│       ├── metrics.py             # Prometheus
│       └── tracing.py             # OpenTelemetry
├── tests/
│   ├── conftest.py                # Shared fixtures
│   ├── integration/
│   │   ├── test_auth.py           # 5 tests
│   │   └── test_booking_flow.py   # 5 tests
│   ├── unit/
│   │   └── test_security.py       # 5 tests
│   └── e2e/
│       └── test_full_flow.py      # 1 test
├── docs/
│   ├── architecture.md
│   ├── threat-model.md
│   ├── ER-diagram.md
│   ├── openapi.json
│   └── project-documentation.md
├── infrastructure/
│   └── docker-compose.yml
├── worker.py
├── Dockerfile
├── pyproject.toml
└── .github/workflows/ci.yml
```

### 10.4 Commands

```bash
# Tests
uv run pytest tests/ -v --tb=short
uv run pytest tests/ -v --cov=app --cov-report=term-missing
uv run pytest tests/integration/test_auth.py -v

# Lint / Format
uv run ruff check app/ tests/
uv run ruff format app/ tests/

# Migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "message"

# Worker
uv run arq app.worker.WorkerSettings
```

---

## 11. Testing Strategy

### 11.1 Test Suite (16 tests)

| Suite | File | Count | Type |
|---|---|---|---|
| Auth | `test_auth.py` | 5 | Integration |
| Booking Flow | `test_booking_flow.py` | 5 | Integration |
| Security | `test_security.py` | 5 | Unit |
| Full Flow | `test_full_flow.py` | 1 | E2E |

### 11.2 Test Database

- URL: `postgresql+asyncpg://amrutam:amrutam@localhost:5432/amrutam_test`
- Fixture scope: **function** (fresh DB per test)
- Schema: Auto-created via `Base.metadata.create_all`, dropped after test

### 11.3 CI Pipeline (GitHub Actions)

| Job | Services | Commands |
|---|---|---|
| `test` | postgres:16 + redis:7 | migrations → pytest with coverage |
| `lint` | — | `ruff check` |
| `security` | — | `safety check` (dependency vulnerabilities) |

### 11.4 Fixtures

- `engine` (function-scoped): Creates/drops all tables
- `session`: SQLAlchemy async session per test
- `client`: HTTPX AsyncClient with ASGI transport (overrides DB session)
- `patient_token`: Registered patient's JWT
- `doctor_token`: Registered doctor's JWT + profile + slots

### 11.5 Writing Tests

```python
async def test_something(client, patient_token):
    resp = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "pat_test@test.com"
```

---

## 12. Production Checklist

### 12.1 Pre-Launch

- [ ] Set strong `JWT_SECRET_KEY` (256-bit random, rotate every 90 days)
- [ ] Configure `CORS_ORIGINS` to specific domains
- [ ] Deploy Redis and set `REDIS_URL` for rate limiting + background jobs
- [ ] Enable `ENABLE_TRACING` with OTLP endpoint (Jaeger/Honeycomb/Datadog)
- [ ] Set up database backups (pg_dump daily + WAL archiving)
- [ ] Configure structured JSON logging (`ENVIRONMENT=production`)
- [ ] Run full test suite and verify CI passes
- [ ] Review OpenAPI schema at `docs/openapi.json`
- [ ] Conduct security review using `docs/threat-model.md`

### 12.2 Scaling

| Metric | Target | Action if exceeded |
|---|---|---|
| p95 response time | <200ms reads, <500ms writes | Add read replicas, optimize queries |
| Connection pool | <80% of pool_size | Increase pool_size (watch DB max_connections) |
| Error rate | <0.1% | Check logs, rollback recent changes |
| DB CPU | <70% | Add indexes, read replicas, partition tables |

### 12.3 Data Partitioning (Future)

When tables grow beyond 10M rows, implement range partitioning by month on:

- `availability_slots` by `start_time`
- `consultations` by `created_at`
- `audit_logs` by `created_at`
- `payments` by `created_at`

### 12.4 Disaster Recovery

| Scenario | RPO | RTO | Action |
|---|---|---|---|
| DB failure | <1 hour | <4 hours | Restore latest backup + replay WAL |
| Region outage | <1 hour | <1 hour | DNS switch to read replica in other AZ |
| Corrupt data | <24 hours | <4 hours | Point-in-time recovery to before corruption |

### 12.5 Monitoring Alerts

- [ ] API error rate > 1% (5 min window)
- [ ] p95 latency > 1s
- [ ] DB connection count > 80% of max
- [ ] Disk space < 20% free
- [ ] Certificate expiry < 30 days
- [ ] Rate limit threshold breached by single IP

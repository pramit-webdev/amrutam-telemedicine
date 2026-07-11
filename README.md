# Amrutam Telemedicine API

Production-grade backend for a telemedicine system built with FastAPI, PostgreSQL, and Redis.

## Features

- **Auth**: Registration, login, JWT + refresh tokens, MFA (TOTP), RBAC
- **Doctors**: Profile management, availability slots
- **Booking**: Slot search, idempotent booking with pessimistic locking
- **Consultations**: Lifecycle (pending → confirmed → in-progress → completed)
- **Payments**: Idempotent payment processing, refunds
- **Prescriptions**: Create and list prescriptions
- **Search**: Doctor search with specialization, rating, fee filters
- **Analytics**: Consultation stats, revenue, top doctors
- **Audit**: Full audit trail for all state-changing operations
- **Observability**: Prometheus metrics, structured logging, OpenTelemetry tracing
- **E2E Testing**: Postman collection with 34 requests, 75 assertions across 12 workflows

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Jobs | arq (Redis-based async queue) |
| Auth | JWT + bcrypt + TOTP |
| Observability | Prometheus + OpenTelemetry + structlog |
| Container | Docker + Compose |
| CI/CD | GitHub Actions |

## Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/yourusername/amrutam-telemedicine.git
cd amrutam-telemedicine

# 2. Start infrastructure
docker compose -f infrastructure/docker-compose.yml up -d

# 3. Install dependencies (pick one)
uv sync                          # via uv (recommended for dev)
pip install -r requirements.txt  # via pip (matches Docker runtime)

# 4. Run migrations
uv run alembic upgrade head
# OR: alembic upgrade head

# 5. Start server
uv run uvicorn app.main:app --reload
# OR: uvicorn app.main:app --reload

# 6. Open API docs
open http://localhost:8000/docs
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `JWT_SECRET_KEY` | (required) | JWT signing secret |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `ENVIRONMENT` | `development` | `development`, `testing`, `production` |
| `ENABLE_METRICS` | `true` | Enable Prometheus metrics at `/metrics` |
| `ENABLE_TRACING` | `false` | Enable OpenTelemetry tracing |

## API Overview

### Auth
- `POST /auth/register` — Register (patient, doctor, admin)
- `POST /auth/login` — Login, returns JWT pair
- `POST /auth/mfa/enroll` — Enroll in TOTP MFA
- `POST /auth/mfa/verify` — Verify MFA token
- `POST /auth/refresh` — Refresh access token

### Doctors
- `POST /doctors/profile` — Create/update profile (doctor)
- `GET /doctors/profile` — Get own profile (doctor)
- `GET /doctors/search` — Search doctors
- `GET /doctors/{id}` — Get doctor by ID
- `POST /doctors/slots` — Add availability slots (doctor)
- `GET /doctors/{id}/slots` — Get available slots

### Bookings
- `POST /bookings` — Book a slot (patient, idempotent)
- `POST /bookings/{id}/cancel` — Cancel booking

### Consultations
- `GET /consultations` — List own consultations
- `GET /consultations/{id}` — Get consultation details
- `POST /consultations/{id}/start` — Start consultation (doctor)
- `POST /consultations/{id}/complete` — Complete consultation (doctor)

### Payments
- `POST /payments` — Process payment (patient, idempotent)
- `POST /payments/{id}/refund` — Refund payment (admin)

### Prescriptions
- `POST /prescriptions` — Create prescription (doctor)
- `GET /prescriptions/consultation/{id}` — List prescriptions

### Admin
- `GET /analytics/consultations` — Consultation stats
- `GET /analytics/revenue` — Revenue stats
- `GET /analytics/top-doctors` — Top doctors by volume
- `GET /audit-logs` — Query audit logs

### Health
- `GET /health` — Service health check
- `GET /db-check` — Database connectivity check
- `GET /health/full` — Full health check (DB + Redis status)

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## E2E Testing

A Postman collection (`Amrutam-Telemedicine.postman_collection.json`) covers the full workflow with realistic use-case data:

| Scenario | Persona | Details |
|----------|---------|---------|
| Patient | Rajesh Kumar | 45-yr-old Mumbai resident, diabetes symptoms |
| Doctor | Dr. Priya Sharma | Endocrinologist, Apollo Hospitals, 15 yrs exp |
| Admin | Vikram Patel | Platform administrator |
| Condition | Type 2 Diabetes | HbA1c 8.2%, prescribed Metformin 500mg |
| Payment | ₹1,200 | Paid via UPI |

```bash
# Run via Newman
newman run Amrutam-Telemedicine.postman_collection.json \
  --env-var "base_url=https://amrutam-telemedicine.onrender.com"

# Expected: 34/34 requests, 75/75 assertions ✅
```

Results are documented in [`E2E-TEST-RESULTS.md`](./E2E-TEST-RESULTS.md).

## Performance Characteristics (Observed)

| Metric | Value | Notes |
|--------|-------|-------|
| Avg response time | 804ms | Across full E2E run (34 requests) |
| Min response time | 312ms | Cached/read endpoints |
| Max response time | 2.1s | Registration (bcrypt cost factor 12) |
| Total E2E run | 28.9s | 34 sequential requests on Render free tier |
| Redis | Not available | Falls back to in-memory rate limiting on free tier |

## Security

- Password hashing with bcrypt
- JWT with short-lived access tokens
- MFA via TOTP (Google Authenticator compatible)
- RBAC (patient, doctor, admin roles)
- Idempotency keys on all write operations
- Pessimistic locking on slot booking
- Input validation via Pydantic
- Rate limiting via Redis
- Full audit trail
- CORS configured
- See [docs/threat-model.md](docs/threat-model.md) for detailed security analysis

## Deployment

### Render (Current)

**Live URL**: https://amrutam-telemedicine.onrender.com

| Component | Runtime | Region | Plan |
|-----------|---------|--------|------|
| Web Service | Docker | Oregon | Free |
| PostgreSQL | Render Managed | Oregon | Free (expires Aug 9, 2026) |

1. Push code to GitHub
2. Create a new **Web Service** on Render, connect your repo
3. Set **Runtime** to `Docker`
4. Ensure `Dockerfile` is at repo root (builds via `pip install -r requirements.txt`)
5. Start command is hardcoded in `Dockerfile` as `CMD uvicorn app.main:app --host 0.0.0.0 --port 10000`
6. Add a **PostgreSQL** database and set `DATABASE_URL`
7. Set required env vars (`JWT_SECRET_KEY`, `ENVIRONMENT=production`, `LOG_LEVEL=INFO`)
8. Deploy
9. Run migrations: connect via Render Shell, run `alembic upgrade head`

### Docker

```bash
# Full stack (API + DB + Redis + Worker)
docker compose -f infrastructure/docker-compose.yml up --build

# Production build only
docker build -t amrutam-api .
docker run -p 10000:10000 --env-file .env amrutam-api
```

## Files

| File | Purpose |
|------|---------|
| `Amrutam-Telemedicine.postman_collection.json` | Postman E2E collection (34 requests) |
| `E2E-TEST-RESULTS.md` | Full request/response documentation |
| `Dockerfile` | Single-stage Docker build (pip-based) |
| `requirements.txt` | Python dependencies for Docker build |
| `project-documentation.md` | Detailed project docs |

## License

MIT

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

# 3. Install dependencies
uv sync

# 4. Run migrations
uv run alembic upgrade head

# 5. Start server
uv run uvicorn app.main:app --reload

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
- `GET /health` — Health check

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## Performance Characteristics

- **p95 reads**: <200ms (with Redis caching)
- **p95 writes**: <500ms (with async DB sessions)
- **Scale**: 100k consultations/day (~1.2/sec sustained)
- **Availability**: 99.95% (designed for multi-region deployment)

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

### Render (Free Tier)

1. Push code to GitHub
2. Create a new **Web Service** on Render, connect your repo
3. Set build command: `pip install uv && uv sync`
4. Set start command: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`
6. Create a **Neon** PostgreSQL database and copy the connection string to `DATABASE_URL`
7. Deploy

### Docker

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

## License

MIT

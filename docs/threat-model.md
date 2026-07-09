# Threat Model — Amrutam Telemedicine

## 1. Assets

| Asset | Sensitivity | Impact of Breach |
|---|---|---|
| User passwords (hashed) | Critical | Account takeover |
| JWT signing key | Critical | Unauthorized access |
| Patient health records | High | HIPAA/GDPR violation |
| Payment information | High | Financial fraud |
| PII (email, phone, name) | Medium | Phishing, spam |
| Doctor credentials (license) | Medium | Fake practitioners |
| Audit logs | Medium | Compliance failure |

## 2. Trust Boundaries

```
[Client] ──TLS──▶ [API Gateway] ──▶ [App Server] ──▶ [Database]
                      │                                 │
                      │                                 │
                  [Redis Cache]                  [Backup Storage]
```

- **Boundary 1**: Internet → API Gateway (rate limit, auth, TLS)
- **Boundary 2**: API Gateway → App Server (internal network only)
- **Boundary 3**: App Server → Database (firewalled, service account)

## 3. Threat Scenarios & Mitigations

### T1: Account Takeover
- **Attack**: Credential stuffing, brute force, weak passwords
- **Mitigations**:
  - bcrypt (cost 12) — slow hash, resistant to GPU/ASIC
  - Rate limiting on `/auth/login` (5 attempts/min per IP)
  - MFA via TOTP (optional but available)
  - JWT rotation (15 min access, 7 day refresh)
  - Account lockout after 10 failed attempts (15 min)

### T2: Unauthorized Data Access
- **Attack**: JWT token theft, manipulation, replay
- **Mitigations**:
  - Short-lived tokens (15 min)
  - Token binding to `jti` (JWT ID)
  - Refresh token rotation (old invalidated on use)
  - RBAC middleware on every endpoint
  - Row-level access checks (patients see only own records)
  - HTTPS enforced via CORS config + SSL termination

### T3: SQL Injection
- **Attack**: Malicious input in search, booking, or profile fields
- **Mitigations**:
  - SQLAlchemy parameterized queries (no raw SQL)
  - Pydantic input validation (strict typing)
  - Input sanitization on all text fields

### T4: Race Conditions (Double Booking)
- **Attack**: Send 10 simultaneous booking requests for the same slot
- **Mitigations**:
  - `SELECT ... FOR UPDATE` (pessimistic row lock)
  - `is_booked` + unique slot constraint
  - Idempotency key ensures each booking is processed once
  - Version column for optimistic locking

### T5: Payment Fraud
- **Attack**: Replay payment, modify amount, use stolen card
- **Mitigations**:
  - Idempotency key (each payment processed once)
  - Amount locked from consultation (cannot be modified client-side)
  - Payments partitioned by user (cross-user payment fails)
  - Refund requires admin role

### T6: Session Hijacking
- **Attack**: Steal JWT from XSS, insecure storage
- **Mitigations**:
  - JWT stored in HTTP-only cookies (option)
  - Short access token expiry (15 min)
  - Refresh token rotation
  - Audit log all token refreshes

### T7: Data Exfiltration via Audit Logs
- **Attack**: Attacker with read-only access reads audit logs to extract PII
- **Mitigations**:
  - Audit logs exclude sensitive fields (passwords, payment details)
  - PII redacted in log messages
  - Audit logs access restricted to admin role

## 4. Compliance Mapping

| Requirement | Implementation |
|---|---|
| Unique user ID | UUID v4, collision probability <2^-122 |
| Access control | RBAC (patient, doctor, admin) |
| Audit trail | All state changes logged |
| Data integrity | Idempotency keys on writes |
| Secure storage | bcrypt for passwords, JWT for sessions |
| HTTPS | TLS termination at reverse proxy |
| Rate limiting | Redis-based token bucket |
| Input validation | Pydantic schemas on all endpoints |

## 5. Secrets Management

- **Development**: `.env` file (gitignored)
- **CI**: GitHub Actions secrets
- **Production**: Environment variables via Render dashboard
- **JWT signing key**: 256-bit random, rotated every 90 days
- **No secrets in code**: All secrets injected via environment

# Amrutam Telemedicine Backend

Production-oriented reference backend for Amrutam’s telemedicine assignment. It uses a modular FastAPI service with PostgreSQL, Redis-ready configuration, JWT authentication, role-based access control, idempotent booking, transactional state transitions, audit events, Prometheus metrics, Docker Compose, and CI.

## Quick start

```bash
cp .env.example .env
# Set JWT_SECRET to a random 32+ byte value in real environments
python -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
uvicorn app.main:app --reload
```

OpenAPI is at `http://localhost:8000/docs`; metrics are at `/metrics`. For the full local stack: `docker compose up --build`.

## Example flow

```bash
TOKEN=$(curl -s localhost:8000/v1/auth/register -H 'content-type: application/json' \
  -d '{"email":"patient@example.com","password":"CorrectHorseBattery12!"}' | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
curl localhost:8000/v1/doctors
curl -X POST localhost:8000/v1/consultations -H "Authorization: Bearer $TOKEN" \
  -H 'Idempotency-Key: unique-booking-001' -H 'content-type: application/json' \
  -d '{"slot_id":1,"reason":"headache"}'
```

## Design decisions

* PostgreSQL is the system of record. Availability slot booking uses a row lock plus a unique consultation/slot constraint, so concurrent requests cannot double-book a slot. The `Idempotency-Key` is persisted with a unique constraint and returns the original response on retry.
* JWTs are short-lived. Passwords use salted scrypt hashes. Roles are enforced at route boundaries. Production deployment should add an OIDC provider, MFA challenge verification, KMS-backed signing keys, and secure refresh-token rotation.
* Audit events are append-only application records. Do not log passwords, tokens, prescriptions, or raw medical payloads. Use structured log shipping with retention and tamper-evident storage in production.
* Heavy work such as reminders, notification delivery, prescription PDF generation, and analytics aggregation should be moved to an outbox-backed worker using Redis/RabbitMQ/Kafka. Retries use exponential backoff with jitter and a dead-letter queue.

## Repository map

| Path | Purpose |
|---|---|
| `app/` | API, security, persistence, schemas |
| `tests/` | Integration tests for critical flows |
| `docs/` | Architecture, sequence, ERD, threat model, DR and runbook |
| `ops/` | Prometheus configuration |
| `.github/workflows/ci.yml` | Lint, test and container build |
| `docker-compose.yml` | Local PostgreSQL, Redis, API and Prometheus |

## Production checklist

Run migrations rather than `create_all`; configure managed PostgreSQL with TLS, backups and read replicas; place the service behind a WAF/API gateway; set strict CORS; enable MFA for doctors/admins; use secret manager/KMS; add OpenTelemetry export; configure SLO alerts; test restore and failover quarterly; complete a DPIA and healthcare/privacy review before handling real PHI.

## Assignment coverage

The accompanying `docs/architecture.md` covers scale targets, data flow, partitioning, caching, transaction boundaries, sagas, retry/backoff and disaster recovery. `docs/threat-model.md` covers attack surface, classification, OWASP mitigations, encryption, key rotation, audit and dependency scanning. `openapi.yaml` is an exportable API contract for review.

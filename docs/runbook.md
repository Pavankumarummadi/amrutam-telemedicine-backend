# Operations Runbook and 5-minute Demo

## Demo script

1. Start `docker compose up --build` and show `/docs`, `/health/live`, and `/metrics`.
2. Register a patient and show JWT authentication.
3. Seed a doctor and slot using an admin-only setup or SQL console.
4. List/search doctors and available slots.
5. Book a slot with `Idempotency-Key`; repeat the request to show the same consultation is returned.
6. Attempt the admin analytics endpoint as a patient to demonstrate RBAC.
7. Transition the consultation through the lifecycle as the assigned doctor and create a prescription.
8. Show CI tests and the architecture/threat-model documents.

## Incident response

For elevated 5xx or latency: check `/metrics`, logs by request ID, DB pool/locks, queue lag and dependency health. Stop rollout, roll back the immutable image if regression is confirmed. For suspected credential/PHI exposure: disable credentials, preserve audit evidence, rotate keys, contain access, notify the security/privacy owner and follow the approved incident response plan. Never print PHI in incident channels.

## Backup restore

Provision an isolated database, restore the latest encrypted snapshot, replay WAL to the target timestamp, run migrations/checksums, validate counts and audit continuity, then perform a controlled application smoke test before DNS cutover.

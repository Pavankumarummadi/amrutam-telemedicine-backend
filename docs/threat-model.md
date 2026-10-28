# Security Checklist and Threat Model

## Data classification

* **Restricted PHI:** consultation reason, prescription medications, patient identifiers. Encrypt in transit and at rest; least-privilege access; redact from logs.
* **Confidential:** email, role, doctor profile and operational audit metadata.
* **Internal:** metrics, service configuration and deployment metadata.
* **Public:** approved doctor search fields only.

## Attack surface

Clients and third-party integrations reach the WAF/API gateway; the API reaches PostgreSQL, Redis and async workers; operators reach CI/CD, secret manager and observability systems. Threats include credential stuffing, token theft, broken object-level authorization, double booking, injection, replay, malicious dependencies, SSRF via future integrations, data exfiltration, insider misuse and ransomware.

## Mitigations mapped to OWASP

| Risk | Control |
|---|---|
| Broken access control | JWT validation, role dependencies, assigned-doctor check, deny-by-default routes, authorization tests |
| Cryptographic failures | TLS, bcrypt passwords, KMS-managed keys, encrypted disks/backups, no secrets in Git |
| Injection | Pydantic validation, SQLAlchemy parameters, no string-built SQL, dependency scanning |
| Insecure design | idempotency, DB constraints, explicit state machine, outbox/saga boundaries |
| Authentication failures | short-lived tokens, rate limiting at gateway, MFA for privileged users, lockout/step-up policy |
| Logging failures | correlation IDs, audit events, redaction, immutable retention, alerting |
| SSRF / supply chain | egress allow-list, URL validation, pinned dependencies, SBOM and Dependabot |

## Key management and operations

Use an external secret manager and KMS; rotate JWT signing keys with `kid` and overlapping verification windows. Rotate database and provider credentials at least every 90 days or after suspected exposure. Separate production projects and service accounts. CI uses OIDC short-lived cloud credentials, protected branches, signed images and an admission policy.

## Verification checklist

- [ ] Threat model reviewed before each material architecture change
- [ ] SAST, dependency audit, secret scan and container scan pass in CI
- [ ] DAST against staging and API schema fuzzing
- [ ] MFA enforced for admins/doctors
- [ ] Rate limits and account abuse alerts enabled
- [ ] Access to PHI audited and reviewed
- [ ] Backups encrypted and restore-tested
- [ ] Incident response, breach notification and retention policy approved by counsel
- [ ] Security headers, TLS 1.2+, HSTS and strict CORS at gateway

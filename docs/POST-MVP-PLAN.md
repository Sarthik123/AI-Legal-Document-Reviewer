# Post-MVP Production Plan

This plan describes the work required before the AI Legal Document Reviewer can serve production users. The current MVP runs locally with FastAPI, Next.js, PostgreSQL/pgvector, local Ollama inference, and local file storage. The local Playwright suite now covers registration through document deletion, upload validation, access isolation, grounded chat, citations, and scanned-PDF OCR.

## 1. Production-Readiness Gaps

- Database, backend, Ollama, and frontend addresses are hard-coded for local development.
- Uploaded PDFs are stored on the backend's local filesystem. There is no production object-storage adapter or retention policy.
- The backend has no migration framework or established upgrade/rollback process.
- Document processing, OCR, embeddings, and model requests run synchronously in upload/request handlers.
- Email verification and expiring password-reset flows are implemented. Password reset is disabled by default until SMTP delivery is verified; enable it explicitly on both the backend and frontend when ready. Refresh/revocation, MFA, and account-deletion flows are absent; the browser stores access tokens in local storage.
- Rate limits, production TLS, centralized monitoring, and alerting are not configured.
- Production capacity, AI quality thresholds, privacy terms, and service objectives have not been approved.

## 2. Security Hardening

- Threat-model document upload, user isolation, model access, storage, and administrative access.
- Enforce HTTPS, private service networking, encrypted database connections, encrypted storage, and managed secrets.
- Replace local-storage bearer tokens with secure, HttpOnly, SameSite cookies or another reviewed session design; add token rotation, revocation, and short-lived access credentials.
- Validate and bound uploads, processing time, extracted text, page count, and model input. Keep uploaded content isolated as untrusted data through extraction, retrieval, and prompting.
- Review authorization checks for every document, file, analysis, chat, and deletion route. Add automated cross-user access tests.
- Scan dependencies and container images, pin production dependencies, restrict service permissions, and redact document text, credentials, and personal data from logs.
- Define a vulnerability response process and conduct an independent security review before launch.

## 3. Database Migration Strategy

- Adopt Alembic and create a reviewed baseline migration for users, documents, chunks, chat messages, indexes, and the pgvector extension.
- Run migrations as a separate, serialized release step using a least-privilege migration account.
- Use forward-compatible expand/migrate/contract changes for releases that overlap old and new application versions.
- Back up PostgreSQL before schema changes; test both forward migration and restore/rollback procedures in staging.
- Keep schema creation out of normal application startup. Track migration versions in source control and verify the deployed version during release checks.

## 4. Production Environment Variables

Introduce validated environment configuration before deployment. At minimum, support:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Production PostgreSQL/pgvector connection string, supplied through a secret manager |
| `JWT_SECRET_KEY` | Authentication signing key, managed and rotated outside source control |
| `CORS_ORIGINS` | Explicit approved browser origins, including lawyerlens.in and www.lawyerlens.in |
| `NEXT_PUBLIC_API_URL` | Public API base URL used by the frontend |
| `AI_PROVIDER`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_AI_MODEL`, `CLOUDFLARE_EMBEDDING_MODEL`, `CLOUDFLARE_OCR_MODEL` | Production Workers AI configuration; OCR model override is optional |
| `EMBEDDING_MODEL` | Approved local embedding model, initially `sentence-transformers/all-MiniLM-L6-v2` |
| `EMAIL_PROVIDER`, `BREVO_API_KEY`, `BREVO_FROM_EMAIL`, `BREVO_FROM_NAME` | Production Brevo HTTPS email configuration |
| `APP_BASE_URL` | Base URL used in verification and password-reset links |
| `EMAIL_VERIFICATION_ENABLED` | Keep `true` outside local development; local development can set `false` until SMTP is configured |
| `PASSWORD_RESET_ENABLED` | Backend feature flag; keep `false` until reset email delivery is verified |
| `NEXT_PUBLIC_PASSWORD_RESET_ENABLED` | Frontend feature flag; set to `true` with the backend flag when password reset is enabled |
| `DOCUMENT_STORAGE` settings | Private object-storage bucket, region, and credentials or workload identity |
| `MAX_UPLOAD_BYTES` | Server-side upload limit |
| `ENVIRONMENT`, `LOG_LEVEL` | Runtime mode and log verbosity |
| `SENTRY_DSN` | Error-reporting destination, if selected |

Do not commit production values, certificates, passwords, or signing keys. Validate required settings at startup without printing secret values.

## 5. Frontend Deployment

- Build the Next.js application in CI with a pinned Node version and lockfile.
- Deploy to a managed Next.js host or an approved container platform.
- Configure `NEXT_PUBLIC_API_URL` for the production API and verify that no local `127.0.0.1` URLs remain in production bundles.
- Apply security headers, a restrictive content security policy, and cache rules that never expose authenticated document data.
- Keep preview, staging, and production settings isolated. Promote the same tested build artifact between environments.

## 6. Backend Deployment

- Package FastAPI and its Python dependencies in a reproducible, non-root container.
- Run behind a TLS-terminating ingress or reverse proxy with explicit health and readiness checks.
- Configure outbound access only to PostgreSQL, private object storage, Ollama, and approved telemetry endpoints.
- Preload and pin the approved embedding and Ollama models. Verify model files and licenses before each upgrade.
- Move long-running extraction, OCR, embedding, and analysis work to a durable background queue before accepting production-scale traffic. Return a persistent processing state and support safe retries.
- Set worker and request timeouts based on measured CPU/GPU performance and the documented upload limits.

## 7. Production PostgreSQL

- Use a managed PostgreSQL service with a supported pgvector version, private networking, TLS, automated patching, and point-in-time recovery.
- Provision separate least-privilege application and migration roles; require encrypted connections and rotate credentials.
- Validate vector dimensions, indexes, query plans, connection pooling, and capacity using a representative document corpus.
- Define storage, connection, latency, and availability alerts. Test failover and restore procedures in staging.

## 8. Production File Storage

- Use a private, encrypted object-storage bucket with public access blocked and versioning/lifecycle settings aligned with the retention policy.
- Store an opaque object key and required metadata in PostgreSQL; do not rely on local container disks for durable uploads.
- Authorize every download through the backend or short-lived signed URLs scoped to one object and user.
- Make document deletion remove the object, extracted text, embeddings, chat history, and derived analysis; make retries idempotent and record completion without retaining document contents in logs.

## 9. HTTPS and Domain Configuration

- Select production domains and DNS ownership for the frontend and API.
- Use managed certificates, automatic renewal, HTTPS-only redirects, HSTS after validation, and secure cookie settings.
- Configure exact CORS origins and trusted proxy headers. Reject unknown hosts and origins.
- Verify TLS for browser-to-API, API-to-database, API-to-storage, and API-to-model traffic where supported.

## 10. Authentication Hardening

- Move session credentials out of local storage and use secure, HttpOnly, SameSite cookies or an equivalently reviewed design.
- Keep email verification and password-reset tokens single-use, hashed at rest, and expiry-limited; configure a verified sender, rate-limit requests, and test delivery failures.
- Add session revocation, password-change handling, and a documented password policy.
- Consider MFA for privileged or business accounts. Rate-limit registration and login, protect against credential stuffing, and monitor suspicious authentication activity.
- Test expired, revoked, malformed, and cross-user credentials in CI and staging.

## 11. Rate Limiting

- Apply per-IP and per-account limits to registration, login, uploads, analysis, chat, and deletion.
- Add request-size, page-count, extracted-text, concurrency, and model-token limits.
- Use a shared rate-limit store for multi-instance deployments, return actionable `429` responses, and alert on abuse patterns.

## 12. Logging and Monitoring

- Emit structured logs with request IDs, operation status, latency, model identifier, and non-sensitive document IDs.
- Never log access tokens, passwords, full prompts, extracted text, model responses containing document data, or signed URLs.
- Monitor API availability, queue depth, upload and OCR failures, model latency/timeouts, database health, storage failures, and resource utilization.
- Define service objectives and on-call alerts before opening the service to users.

## 13. Error Tracking

- Select an error-tracking service and configure source maps for the frontend and release identifiers for both applications.
- Scrub user data, document contents, credentials, and request bodies before sending error events.
- Group errors by route and failure type; define ownership and response targets for authentication, upload, processing, AI, and storage failures.

## 14. CI/CD

- Run lint, TypeScript, backend import/compile checks, dependency checks, and automated tests on every pull request.
- Build immutable frontend/backend artifacts, scan dependencies and images, and retain test and build provenance.
- Deploy first to staging. Require explicit review before production promotion; keep rollback artifacts and a documented rollback decision path.
- Run database migrations as an explicit release step and verify health/readiness before shifting traffic.

## 15. Automated Testing in CI

- Keep the Playwright suite against an isolated frontend and backend. It covers registration, verification gating, the password-reset-disabled state, valid upload, PDF viewing, analysis sections, typo-tolerant and multi-part document Q&A, source evidence, chat persistence/clear, deletion, invalid/oversized uploads, unauthenticated access, cross-user denial, and OCR. Email tests use a local SMTP capture server and never send to real addresses.
- Run the E2E suite with an isolated disposable PostgreSQL/pgvector database, local Ollama model, synthetic PDFs, and a dedicated test secret. Never use user documents or production credentials as fixtures.
- Add backend unit/integration tests for authorization, failure cleanup, citations, migrations, and deletion cascades. Add deterministic grounding tests for behavior that should not depend on model sampling.
- Keep OCR fixtures image-only and verify extracted text and page metadata. Keep the CI job time-bounded and store reports/traces only for a short retention period.
- Track model evaluation on a versioned synthetic and approved benchmark set; require reviewed quality thresholds before changing models or prompts.

## 16. Backup and Recovery

- Enable managed PostgreSQL point-in-time recovery and encrypted backups with documented retention.
- Enable object versioning or an equivalent recovery mechanism consistent with user deletion requirements.
- Define recovery point and recovery time objectives, assign owners, and run scheduled restore drills into an isolated environment.
- Verify that a restored database and object store preserve ownership checks, citations, and deletion state.

## 17. Privacy and Data Deletion

- Publish a clear privacy notice covering uploaded files, extracted text, embeddings, chat history, model processing, retention, and subprocessors.
- Define retention periods and defaults. Do not use documents for model training.
- Implement account-level export and deletion, including files, database rows, embeddings, cached artifacts, backups according to the published schedule, and error/analytics data where applicable.
- Record deletion completion without retaining deleted content. Provide a user-visible deletion confirmation and test end-to-end deletion.
- Complete a privacy impact review for the target markets and legal obligations before launch.

## 18. Cost Considerations

- Measure CPU/GPU inference, embedding generation, OCR, storage, database, network, backup, and observability costs with realistic workloads.
- Estimate peak concurrency and per-document processing cost; set budgets and alerts for model hosting and storage growth.
- Compare private GPU hosting with CPU-only inference using latency, accuracy, availability, and privacy requirements. Keep inference local/self-hosted unless a different provider is explicitly approved.
- Use lifecycle rules and published retention limits to control storage and backup costs.

## 19. Exact Deployment Sequence

1. Approve target markets, data residency, privacy terms, service objectives, and production model versions.
2. Provision staging and production accounts, private network boundaries, DNS, TLS, secret management, and monitoring.
3. Provision managed PostgreSQL/pgvector and private object storage; verify access controls and backups.
4. Deploy the approved Ollama/model service and warm the embedding model; run the AI evaluation benchmark.
5. Build and scan immutable frontend/backend artifacts; publish them to the approved artifact registry.
6. Deploy the backend to staging with staging-only settings and private dependencies.
7. Apply the versioned database migration to staging and verify health, processing, and rollback readiness.
8. Deploy the frontend to staging with the staging API URL and security headers.
9. Run backend checks, Playwright E2E, OCR, access-isolation, migration, backup-restore, and AI grounding evaluations in staging.
10. Review logs, alerts, cost estimates, privacy deletion, and security findings; resolve launch-blocking issues.
11. Back up production data, apply the reviewed production migration, and deploy the approved backend artifact.
12. Verify readiness, database connectivity, model availability, storage permissions, and monitoring before routing user traffic.
13. Deploy the matching frontend artifact, perform a synthetic production smoke journey, and monitor errors and latency.
14. Keep rollback artifacts and the release owner available through the observation window; roll back on the defined triggers.

## 20. Final Production Checklist

- [ ] Security review and privacy review are approved.
- [ ] Production secrets and database roles are managed outside source control.
- [ ] HTTPS, cookies, CORS, CSP, and security headers are verified.
- [ ] Database migrations, backups, and a restore drill are verified.
- [ ] Private file storage, retention, and complete deletion are verified.
- [ ] Authentication recovery, expiry, revocation, and rate limits are verified.
- [ ] Ollama and embedding models are pinned, evaluated, monitored, and capacity-tested.
- [ ] Background processing, retry behavior, and user-visible failure states are ready.
- [ ] CI passes frontend checks, backend checks, integration tests, and app E2E tests.
- [ ] Logging, error tracking, dashboards, alerts, owners, and on-call procedures are ready.
- [ ] Cost budgets, data retention, recovery objectives, and rollback triggers are approved.
- [ ] Staging sign-off and the production release owner are recorded.

## Production-Readiness Status

The MVP is verified locally by the Playwright user journey, but it is **not production-ready**. A rotated Brevo SMTP key and a verified sender on an authenticated domain must be configured before reliable verification and reset email delivery can be confirmed; the password-reset feature flags should remain off until that verification is complete. Production environment configuration, migrations, durable storage, hardened sessions, asynchronous processing, rate limiting, privacy/deletion controls, monitoring, and recovery procedures remain to be implemented and reviewed. No deployment has been performed.

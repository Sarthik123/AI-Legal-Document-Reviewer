# Staging environment

Staging is the safe place to test reliability changes before production.
Production uses a separate frontend deployment, API service, Neon branch, and
storage bucket. Never copy production secrets into staging.

## Deploy order

1. Push changes to `codex/staging-reliability`.
2. Vercel creates a preview deployment for that branch. Set its
   `NEXT_PUBLIC_API_URL` to the staging API URL.
3. Create a separate Neon branch and apply the migrations in
   `backend/migrations/` to that branch.
4. Create a separate R2 bucket and Brevo sender for staging.
5. Create the Render service from `infra/render.staging.yaml`. It uses the
   `singapore` region, a health check at `/health`, and an always-on Starter
   instance so long processing does not wait for a cold start.
6. Add the staging values to Render and run the staging E2E suite.
7. Add the staging API URL as the GitHub `STAGING_API_URL` secret so the
   scheduled health monitor checks it every ten minutes.

The Render Starter plan is paid. Creating or upgrading that service can incur
provider charges, so it must be approved in the Render dashboard before the
Blueprint is applied. The repository configuration is ready for it.

## Reliability behavior

- Browser API calls retry transient network and 5xx failures with backoff and
  stop after a bounded timeout.
- Upload and dashboard errors keep the existing selected document and show a
  Retry action.
- Staging uploads are stored as durable `document_jobs` rows and return a
  `202` response. The API worker claims queued jobs, retries failures, and
  updates the document status for the UI to poll.
- `/health` is checked by GitHub Actions on a ten-minute schedule with curl
  retries. Failed checks appear as failed workflow runs.
- Sentry is enabled only when `SENTRY_DSN` is provided. It is configured to
  avoid sending personal document content (`send_default_pii=false`).

## Promote to production

Promote only after staging passes the full E2E suite, OCR tests, queue retry
test, migration check, health monitor check, and a manual smoke test. Promote
the same commit, apply the migrations to the production Neon branch, configure
production environment values, and then deploy the frontend and API together.

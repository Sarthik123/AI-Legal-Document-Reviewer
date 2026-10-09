# Database migrations

Apply SQL files in filename order against the production `DATABASE_URL`.
The initial migration creates the `vector` extension and all current model
tables. The email-auth migration is additive and runs afterward.

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f backend/migrations/20260927_initial_schema.sql \
  -f backend/migrations/20260928_email_auth.sql \
  -f backend/migrations/20261009_document_processing_error.sql
```

`20261009_document_processing_error.sql` is additive. On an existing database,
apply it **before** deploying the backend that reads `processing_error`.

Run this once for a new Neon database. Do not run destructive reset commands.

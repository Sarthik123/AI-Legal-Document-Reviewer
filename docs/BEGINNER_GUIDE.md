# AI Legal Document Reviewer: Beginner Operations Guide

## What runs where

| Part | Service | URL |
|---|---|---|
| Website | Vercel | https://lawyerlens.in |
| Website alias | Vercel | https://www.lawyerlens.in |
| API | Render | https://api.lawyerlens.in |
| API health | FastAPI | https://api.lawyerlens.in/health |
| Database | Neon PostgreSQL + pgvector | Neon dashboard |
| File storage | Cloudflare R2 private bucket | Cloudflare dashboard |
| AI generation | Cloudflare Workers AI | Cloudflare dashboard |
| Email | Brevo HTTPS API | Brevo dashboard |
| Source code | GitHub | Repository connected to Vercel and Render |

## Open the project locally

1. Open the repository folder in VS Code.
2. Open two terminals.
3. Backend terminal:

```bash
cd backend
.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

4. Frontend terminal:

```bash
cd frontend
npm run dev
```

5. Open http://localhost:3000.

Local backend defaults use PostgreSQL at `localhost` and the local API URL.
Never copy production secrets into Git or into this guide.

## Environment variables

### Render backend

Set these in Render's Environment tab. Enter secret values directly there.

```text
DATABASE_URL
JWT_SECRET_KEY
CORS_ORIGINS=https://lawyerlens.in,https://www.lawyerlens.in,https://ai-legal-document-reviewer.vercel.app
APP_BASE_URL=https://lawyerlens.in
DB_POOL_SIZE=1
DB_MAX_OVERFLOW=0

AI_PROVIDER=cloudflare_workers_ai
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
CLOUDFLARE_AI_MODEL=@cf/meta/llama-3.1-8b-instruct

EMAIL_PROVIDER=brevo_api
BREVO_API_KEY
BREVO_FROM_EMAIL
BREVO_FROM_NAME
EMAIL_VERIFICATION_ENABLED=true
PASSWORD_RESET_ENABLED=false

R2_ENDPOINT_URL
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET_NAME
R2_REGION=auto
```

### Vercel frontend

Set this in the Vercel project Environment Variables for Production and
Preview when the preview should use production:

```text
NEXT_PUBLIC_API_URL=https://api.lawyerlens.in
NEXT_PUBLIC_PASSWORD_RESET_ENABLED=false
```

Local frontend development uses `frontend/.env.example` as its starting point.

## Database setup and maintenance

The schema is defined by the SQL files in `backend/migrations/`. For a new
Neon database, paste the files into Neon SQL Editor in filename order:

```text
20260927_initial_schema.sql
20260928_email_auth.sql
```

The initial migration creates the vector extension and the four application
tables. Never use a destructive reset against production. Before changing a
schema, take a Neon backup/branch and add a new numbered migration.

Useful checks in Neon SQL Editor:

```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

## Deploying a code change

1. Make a small change in VS Code.
2. Run checks locally:

```bash
PYTHONPATH=backend ./backend/.venv/bin/python -m unittest discover -s backend/tests -v
npm run lint --prefix frontend
./frontend/node_modules/.bin/tsc --noEmit -p frontend/tsconfig.json
npm run build --prefix frontend
npx playwright test
```

3. Review the diff and ensure no `.env`, token, password, or generated file is included.
4. Commit and push to `main` only after checks pass.
5. Vercel builds the frontend from the push. Render redeploys the backend from
   the push.
6. Check Render deploy logs and then open `/health`.
7. Run the smoke journey: register, verify email, login, upload, analyze, ask
   a question, refresh, clear chat, delete, and logout.

## Render settings

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
```

Root directory is the repository root.

## Troubleshooting

- Website opens but signup/login hangs: check `https://api.lawyerlens.in/health`,
  Render logs, Render service status, and CORS variables.
- `404` on document APIs: check the access token and document ownership.
- Email does not arrive: check Brevo sender verification, API key, and Render
  `EMAIL_PROVIDER=brevo_api`.
- AI errors: check Workers AI account ID, token permissions, and model name.
- Upload errors: check R2 variables and bucket permissions.
- Database errors: check `DATABASE_URL`, Neon status, pgvector, and migrations.
- Out-of-memory errors: keep one Render worker and preserve lazy OCR/embedding
  loading; large scanned documents may require smaller files or a larger plan.

## Security rules

- Do not commit `.env` files or secrets.
- Keep the R2 bucket private.
- Keep CORS limited to approved website origins.
- Do not disable ownership checks or upload validation.
- Treat uploaded document text as untrusted data.
- Review AI answers and citations against the displayed source evidence.

# AI Legal Document Reviewer

Using AI to simplify reading legal documents with page-aware citations.

## Local development

Start the backend from `backend/`:

```bash
.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend from `frontend/`:

```bash
npm run dev
```

The backend expects PostgreSQL with pgvector. Local development can use
Ollama; production uses Cloudflare Workers AI and the Brevo HTTPS API.
Copy the example environment files before configuring local email or a
non-local API URL. Password reset remains disabled by default until email
delivery is verified.

Run the browser regression suite from the repository root:

```bash
npx playwright test
```

Production architecture, security hardening, deployment sequencing, and the
release checklist are documented in [docs/POST-MVP-PLAN.md](docs/POST-MVP-PLAN.md).

## Portfolio and interview guide

See [docs/GUIDE.md](docs/GUIDE.md) for a short,
beginner-friendly explanation of the product, architecture, development
timeline, testing, and deployment. It is safe to share publicly: secrets,
private documents, and environment values must stay out of GitHub.

import os
import logging
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.routes import router
from app.models.document_chunk import DocumentChunk
from app.models.document_job import DocumentJob
from app.services.document_processing import (
    start_processing_worker,
    stop_processing_worker,
)


logger = logging.getLogger(__name__)


def _configure_error_monitoring() -> None:
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        release=os.getenv("RELEASE_VERSION", "local"),
        integrations=[FastApiIntegration()],
        send_default_pii=False,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
    )


_configure_error_monitoring()

app = FastAPI(
    title="AI Legal Document Reviewer API",
    description="Backend API for the AI Legal Document Reviewer",
    version="0.1.0",
)
configured_origins = os.getenv("CORS_ORIGINS", "").strip()
production_origins = [
    "https://lawyerlens.in",
    "https://www.lawyerlens.in",
    "https://ai-legal-document-reviewer.vercel.app",
]
allowed_origins = [
    origin.strip()
    for origin in configured_origins.split(",")
    if origin.strip()
] + production_origins + [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
]
allowed_origins = list(dict.fromkeys(allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled request failure method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        raise
    response.headers["x-request-id"] = request_id
    return response
app.include_router(router)
app.include_router(auth_router)


@app.on_event("startup")
async def start_background_services() -> None:
    start_processing_worker()


@app.on_event("shutdown")
async def stop_background_services() -> None:
    stop_processing_worker()


@app.get("/")
def root():
    return {"message": "AI Legal Document Reviewer API is running"}

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.routes import router
from app.models.document_chunk import DocumentChunk

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
app.include_router(router)
app.include_router(auth_router)


@app.get("/")
def root():
    return {"message": "AI Legal Document Reviewer API is running"}

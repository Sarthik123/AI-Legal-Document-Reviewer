from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.routes import router

app = FastAPI(
    title="AI Legal Document Reviewer API",
    description="Backend API for the AI Legal Document Reviewer",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(auth_router)


@app.get("/")
def root():
    return {"message": "AI Legal Document Reviewer API is running"}
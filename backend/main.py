from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="AI Legal Document Reviewer API",
    description="Backend API for the AI Legal Document Reviewer",
    version="0.1.0",
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "AI Legal Document Reviewer API is running"}
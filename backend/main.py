from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "AI Legal Document Reviewer API is running"}
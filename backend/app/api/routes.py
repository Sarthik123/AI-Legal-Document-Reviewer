from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.document_service import extract_text_from_pdf

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "healthy"}


@router.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents are supported.",
        )

    file_data = await file.read()

    if not file_data:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(file_data)
        temp_path = temp_file.name

    try:
        extracted_text = extract_text_from_pdf(temp_path)

        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "text_length": len(extracted_text),
            "message": "PDF uploaded and text extracted successfully.",
        }

    finally:
        Path(temp_path).unlink(missing_ok=True)
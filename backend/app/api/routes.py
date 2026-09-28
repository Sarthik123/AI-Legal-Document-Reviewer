from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal
from uuid import uuid4

from app.models.chat import ChatMessage

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.analysis_service import analyze_document
from app.services.chat_service import chat_about_document
from app.services.document_service import (
    extract_pages_from_pdf,
)
from app.services.ocr_service import (
    extract_pages_with_ocr,
)

from app.services.rag_service import process_document_chunks
from app.services.storage_service import save_document


router = APIRouter()


class QuestionRequest(BaseModel):
    question: str


class ChatMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessageRequest] = []


@router.get("/health")
def health_check():
    return {"status": "healthy"}


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents are supported.",
        )

    file_data = await file.read()
    max_file_size = 10 * 1024 * 1024

    if len(file_data) > max_file_size:
        raise HTTPException(
            status_code=400,
            detail="File size must be 10 MB or less.",
        )

    if not file_data:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if not file_data.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF.",
        )

    document_id, stored_path = save_document(
        file.filename or "document.pdf",
        file_data,
    )

    document = Document(
        id=document_id,
        user_id=current_user.id,
        filename=file.filename or "document.pdf",
        content_type=file.content_type,
        storage_path=stored_path,
        processing_status="uploaded",
    )

    db.add(document)
    db.commit()

    with NamedTemporaryFile(
        suffix=".pdf",
        delete=False,
    ) as temp_file:
        temp_file.write(file_data)
        temp_path = temp_file.name

    try:
        pages = extract_pages_from_pdf(
         temp_path
        )

        extracted_text = "\n".join(
           text
           for _, text in pages
           if text
        )

        if len(extracted_text.strip()) < 50:
         pages = extract_pages_with_ocr(
        temp_path
      )

         extracted_text = "\n".join(
        text
        for _, text in pages
        if text
    ).strip()

        document.text_length = len(extracted_text)
        document.processing_status = "processing"
        db.commit()

        chunk_count = process_document_chunks(
           db=db,
           document_id=document_id,
           pages=pages,
        )

        document.processing_status = "processed"
        db.commit()

        return {
            "document_id": document_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "text_length": len(extracted_text),
            "chunk_count": chunk_count,
            "message": (
                "PDF uploaded, processed, chunked, and embedded successfully."
            ),
        }
    except Exception as error:
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id,
        ).delete(synchronize_session=False)

        storage_path = Path(document.storage_path)

        if storage_path.exists():
            storage_path.unlink()

        db.delete(document)
        db.commit()

        raise HTTPException(
            status_code=500,
            detail=(
                "Document processing failed: "
                f"{type(error).__name__}: {error}"
            ),
        )
    finally:
        Path(temp_path).unlink(missing_ok=True)


@router.get("/documents")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        {
            "document_id": document.id,
            "filename": document.filename,
            "content_type": document.content_type,
            "processing_status": document.processing_status,
            "text_length": document.text_length,
            "created_at": document.created_at,
        }
        for document in documents
    ]


@router.get("/documents/{document_id}")
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "document_id": document.id,
        "filename": document.filename,
        "content_type": document.content_type,
        "processing_status": document.processing_status,
        "text_length": document.text_length,
        "created_at": document.created_at,
    }


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    storage_path = Path(document.storage_path)

    if not storage_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF file not found.",
        )

    return FileResponse(
        path=storage_path,
        media_type="application/pdf",
        filename=document.filename,
    )


@router.post("/documents/{document_id}/analyze")
def analyze_document_route(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return analyze_document(
            db=db,
            document_id=document_id,
            user_id=current_user.id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception as error:
     print(
        f"AI ANALYSIS ERROR: {type(error).__name__}: {error}",
        flush=True,
    )

    raise HTTPException(
        status_code=500,
        detail=f"AI analysis failed: {type(error).__name__}: {error}",
    )

@router.get("/documents/{document_id}/chat")
def get_chat_history(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.document_id == document_id,
            ChatMessage.user_id == current_user.id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return {
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "sources": message.sources_json or [],
            }
            for message in messages
        ]
    }
@router.delete("/documents/{document_id}/chat")
def clear_chat_history(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(ChatMessage).filter(
        ChatMessage.document_id == document_id,
        ChatMessage.user_id == current_user.id,
    ).delete(synchronize_session=False)

    db.commit()

    return {"message": "Chat cleared successfully."}

@router.post("/documents/{document_id}/chat")
def chat_document(
    document_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    history = [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in request.history[-8:]
    ]

    try:
        result = chat_about_document(
            db=db,
            document_id=document_id,
            user_id=current_user.id,
            message=message,
            history=history,
        )

        db.add(
            ChatMessage(
                id=str(uuid4()),
                document_id=document_id,
                user_id=current_user.id,
                role="user",
                content=message,
            )
        )

        db.add(
            ChatMessage(
                id=str(uuid4()),
                document_id=document_id,
                user_id=current_user.id,
                role="assistant",
                content=result["answer"],
                sources_json=result["sources"],
            )
        )

        db.commit()

        sources = [
            {
                "source": index,
                "content": source,
            }
            for index, source in enumerate(
                result["sources"],
                start=1,
            )
        ]

        return {
            "message": message,
            "answer": result["answer"],
            "standalone_question": result["standalone_question"],
            "sources": sources,
        }

    except HTTPException:
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(error)}",
        )
@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    storage_path = Path(document.storage_path)

    if storage_path.exists():
        storage_path.unlink()

    db.delete(document)
    db.commit()

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id,
    }
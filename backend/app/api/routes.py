from pathlib import Path
from typing import Literal
from uuid import uuid4

from app.models.chat import ChatMessage

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.services.analysis_service import AnalysisGenerationError, analyze_document
from app.services.chat_service import chat_about_document
from app.services.processing_service import (
    FILE_MISSING,
    IN_PROGRESS_STATUSES,
    NO_TEXT,
    DocumentProcessingError,
    fail_stale_documents,
    mark_failed,
    process_document,
)
from app.services.qa_service import sanitize_citation
from app.services.storage_service import delete_document as delete_stored_document, read_document, save_document


router = APIRouter()

PROCESSING_FAILED_MESSAGE = "Something went wrong while processing your document."
NO_TEXT_MESSAGE = (
    "No readable text was found in this PDF. Upload a clearer PDF "
    "or one with selectable text."
)


def processing_failed_response(
    db: Session,
    document: Document,
    error: Exception,
) -> JSONResponse:
    if isinstance(error, DocumentProcessingError):
        reason = error.reason
        cause = error.__cause__
    else:
        reason = "unknown"
        cause = error
    if cause is not None:
        # Exception type only: messages can contain file names or document text.
        print(f"DOCUMENT PROCESSING ERROR: {type(cause).__name__}", flush=True)
    mark_failed(db, document, reason)

    return JSONResponse(
        status_code=500,
        content={
            "detail": NO_TEXT_MESSAGE if reason == NO_TEXT else PROCESSING_FAILED_MESSAGE,
            "document_id": document.id,
            "reason": reason,
        },
    )


def read_stored_bytes(storage_path: str) -> bytes:
    stored_document = read_document(storage_path)
    if isinstance(stored_document, Path):
        if not stored_document.exists():
            raise DocumentProcessingError(FILE_MISSING)
        return stored_document.read_bytes()
    return stored_document.read()


class QuestionRequest(BaseModel):
    question: str


class ChatMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessageRequest] = []


def serialize_chat_sources(sources: list | None) -> list[dict]:
    if not isinstance(sources, list):
        return []

    serialized = []

    for index, source in enumerate(sources, start=1):
        if isinstance(source, dict):
            if isinstance(source.get("source"), int) and isinstance(
                source.get("content"), str
            ):
                serialized.append(
                    {
                        **source,
                        "content": sanitize_citation(source["content"]),
                    }
                )
        elif isinstance(source, str):
            serialized.append(
                {
                    "source": index,
                    "content": sanitize_citation(source),
                }
            )

    return serialized


@router.get("/health")
def health_check():
    return {"status": "healthy"}


@router.post("/documents")
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents are supported.",
        )

    max_file_size = 10 * 1024 * 1024
    file_data = file.file.read(max_file_size + 1)

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

    try:
        document_id, stored_path = save_document(
            file.filename or "document.pdf",
            file_data,
        )
    except Exception as error:
        print(f"DOCUMENT STORAGE FAILED: {type(error).__name__}", flush=True)
        return JSONResponse(
            status_code=500,
            content={"detail": PROCESSING_FAILED_MESSAGE, "reason": "storage_failed"},
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

    try:
        chunk_count = process_document(db, document, file_data)
    except Exception as error:
        return processing_failed_response(db, document, error)

    return {
        "document_id": document_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "text_length": document.text_length,
        "chunk_count": chunk_count,
        "message": (
            "PDF uploaded, processed, chunked, and embedded successfully."
        ),
    }


@router.get("/documents")
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fail_stale_documents(db, current_user.id)

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
            "processing_error": document.processing_error,
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
    fail_stale_documents(db, current_user.id)

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
        "processing_error": document.processing_error,
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

    stored_document = read_document(document.storage_path)
    if isinstance(stored_document, Path):
        if not stored_document.exists():
            raise HTTPException(status_code=404, detail="PDF file not found.")
        return FileResponse(path=stored_document, media_type="application/pdf", filename=document.filename)
    return StreamingResponse(stored_document, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{document.filename}"'})


@router.post("/documents/{document_id}/analyze")
def analyze_document_route(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fail_stale_documents(db, current_user.id)

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    if document.processing_status in IN_PROGRESS_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="This document is still being processed. Try again in a minute.",
        )

    # Retry: re-run processing from the stored file before analysis.
    if document.processing_status == "failed":
        try:
            process_document(db, document, read_stored_bytes(document.storage_path))
        except Exception as error:
            return processing_failed_response(db, document, error)

    try:
        return analyze_document(
            db=db,
            document_id=document_id,
            user_id=current_user.id,
        )

    except AnalysisGenerationError as error:
        print(f"AI ANALYSIS ERROR: {type(error).__name__}: {error}", flush=True)
        raise HTTPException(
            status_code=502,
            detail="Analysis could not be completed. Please try again.",
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception as error:
        error_detail = f"AI analysis failed: {type(error).__name__}: {error}"
        print(f"AI ANALYSIS ERROR: {error_detail}", flush=True)
        raise HTTPException(
            status_code=500,
            detail="Analysis could not be completed. Please try again.",
        ) from error

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
                "sources": serialize_chat_sources(
                    message.sources_json
                ),
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
                sources_json=sources,
            )
        )

        db.commit()

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

    delete_stored_document(document.storage_path)

    db.delete(document)
    db.commit()

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id,
    }

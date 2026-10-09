from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.document_service import (
    extract_pages_from_pdf,
    pages_requiring_ocr,
)
from app.services.ocr_service import extract_pages_with_ocr
from app.services.rag_service import process_document_chunks


# A document still "uploaded" or "processing" after this long was interrupted
# (worker restart, out-of-memory kill, deploy) and will never finish on its own.
STALE_PROCESSING_AFTER = timedelta(minutes=15)

IN_PROGRESS_STATUSES = ("uploaded", "processing")

# Short, content-free reason codes. Safe to store, log, and send to analytics.
NO_TEXT = "no_text"
EXTRACTION_FAILED = "extraction_failed"
OCR_FAILED = "ocr_failed"
EMBEDDING_FAILED = "embedding_failed"
FILE_MISSING = "file_missing"
INTERRUPTED = "interrupted"


class DocumentProcessingError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def process_document(db: Session, document: Document, file_data: bytes) -> int:
    """Extract, chunk, and embed a stored PDF, then mark it processed.

    Raises DocumentProcessingError with a reason code. The caller must then
    call mark_failed so the document never stays "uploaded".
    """
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id,
    ).delete(synchronize_session=False)
    document.processing_status = "uploaded"
    document.processing_error = None
    document.processing_started_at = datetime.utcnow()
    db.commit()

    with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(file_data)
        temp_path = temp_file.name

    try:
        try:
            pages = extract_pages_from_pdf(temp_path)
            ocr_page_numbers = pages_requiring_ocr(temp_path, pages)
        except Exception as error:
            raise DocumentProcessingError(EXTRACTION_FAILED) from error

        if ocr_page_numbers:
            try:
                ocr_pages = dict(
                    extract_pages_with_ocr(
                        temp_path,
                        page_numbers=ocr_page_numbers,
                    )
                )
            except Exception as error:
                raise DocumentProcessingError(OCR_FAILED) from error

            pages = [
                (
                    page_number,
                    ocr_pages.get(page_number, page_text)
                    if page_number in ocr_page_numbers
                    else page_text,
                )
                for page_number, page_text in pages
            ]

        extracted_text = "\n".join(
            text
            for _, text in pages
            if text
        ).strip()

        if not extracted_text:
            raise DocumentProcessingError(NO_TEXT)

        document.text_length = len(extracted_text)
        document.processing_status = "processing"
        db.commit()

        try:
            chunk_count = process_document_chunks(
                db=db,
                document_id=document.id,
                pages=pages,
            )
        except Exception as error:
            raise DocumentProcessingError(EMBEDDING_FAILED) from error

        document.processing_status = "processed"
        db.commit()
        return chunk_count
    finally:
        Path(temp_path).unlink(missing_ok=True)


def mark_failed(db: Session, document: Document, reason: str) -> None:
    """Record a processing failure. Keeps the stored file so the user can retry."""
    db.rollback()
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id,
    ).delete(synchronize_session=False)
    document.processing_status = "failed"
    document.processing_error = reason
    db.commit()
    # Reason code only: never log document text or file names.
    print(f"DOCUMENT PROCESSING FAILED: reason={reason}", flush=True)


def fail_stale_documents(db: Session, user_id: str) -> None:
    """Mark this user's interrupted documents as failed so they can be retried."""
    cutoff = datetime.utcnow() - STALE_PROCESSING_AFTER
    updated = (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.processing_status.in_(IN_PROGRESS_STATUSES),
            func.coalesce(Document.processing_started_at, Document.created_at) < cutoff,
        )
        .update(
            {
                Document.processing_status: "failed",
                Document.processing_error: INTERRUPTED,
            },
            synchronize_session=False,
        )
    )
    if updated:
        db.commit()

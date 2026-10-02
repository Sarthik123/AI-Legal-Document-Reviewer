"""Document processing pipeline and durable queue worker."""

import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_job import DocumentJob
from app.services.document_service import extract_pages_from_pdf, pages_requiring_ocr
from app.services.ocr_service import extract_pages_with_ocr
from app.services.rag_service import process_document_chunks
from app.services.storage_service import read_document


MAX_JOB_ATTEMPTS = 3
STALE_JOB_SECONDS = 15 * 60


def enqueue_document_job(db: Session, document_id: str) -> DocumentJob:
    job = DocumentJob(
        id=str(uuid4()),
        document_id=document_id,
        status="queued",
        available_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    return job


def _friendly_processing_error(error: Exception) -> str:
    text = str(error)
    if "No readable text" in text:
        return (
            "No readable text was found in this PDF. Upload a clearer PDF "
            "or one with selectable text."
        )
    if "OCR" in text or "Cloudflare" in text:
        return "The OCR service is temporarily unavailable. Please try again."
    return "Document processing could not be completed. Please try again."


def _write_stored_document_to_temp(document: Document) -> str:
    stored_document = read_document(document.storage_path)
    with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        if isinstance(stored_document, Path):
            temp_file.write(stored_document.read_bytes())
        else:
            temp_file.write(stored_document.read())
        return temp_file.name


def process_document(
    document_id: str,
    *,
    retry: bool = True,
) -> tuple[str, str | None]:
    """Process one queued document in an independent database session."""
    db = SessionLocal()
    temp_path = ""
    document: Document | None = None
    job: DocumentJob | None = None

    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        job = db.query(DocumentJob).filter(DocumentJob.document_id == document_id).first()

        if not document:
            return "missing", "Document not found."

        document.processing_status = "processing"
        document.processing_error = None
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id,
        ).delete(synchronize_session=False)
        if job and job.status != "processing":
            job.status = "processing"
            job.started_at = datetime.utcnow()
            job.attempts += 1
        db.commit()

        temp_path = _write_stored_document_to_temp(document)
        pages = extract_pages_from_pdf(temp_path)
        ocr_page_numbers = pages_requiring_ocr(temp_path, pages)

        if ocr_page_numbers:
            ocr_pages = dict(
                extract_pages_with_ocr(
                    temp_path,
                    page_numbers=ocr_page_numbers,
                )
            )
            pages = [
                (
                    page_number,
                    ocr_pages.get(page_number, page_text)
                    if page_number in ocr_page_numbers
                    else page_text,
                )
                for page_number, page_text in pages
            ]

        extracted_text = "\n".join(text for _, text in pages if text).strip()
        if not extracted_text:
            raise ValueError("No readable text could be extracted from this PDF.")

        document.text_length = len(extracted_text)
        document.processing_status = "processing"
        db.commit()

        process_document_chunks(
            db=db,
            document_id=document_id,
            pages=pages,
        )

        document.processing_status = "processed"
        document.processing_error = None
        if job:
            job.status = "completed"
            job.finished_at = datetime.utcnow()
            job.last_error = None
        db.commit()
        return "processed", None
    except Exception as error:
        db.rollback()
        document = db.query(Document).filter(Document.id == document_id).first()
        job = db.query(DocumentJob).filter(DocumentJob.document_id == document_id).first()
        retrying = bool(retry and job and job.attempts < MAX_JOB_ATTEMPTS)
        if document:
            document.processing_status = "processing" if retrying else "failed"
            document.processing_error = None if retrying else _friendly_processing_error(error)
        if job:
            job.status = "queued" if retrying else "failed"
            job.available_at = datetime.utcnow() + timedelta(
                seconds=2 ** max(job.attempts - 1, 0)
            ) if retrying else datetime.utcnow()
            job.finished_at = None if retrying else datetime.utcnow()
            job.last_error = type(error).__name__
        db.commit()
        if retrying:
            return "queued", None
        return "failed", _friendly_processing_error(error)
    finally:
        db.close()
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def _claim_next_job(db: Session) -> DocumentJob | None:
    stale_before = datetime.utcnow() - timedelta(seconds=STALE_JOB_SECONDS)
    db.query(DocumentJob).filter(
        DocumentJob.status == "processing",
        DocumentJob.started_at < stale_before,
    ).update(
        {
            DocumentJob.status: "queued",
            DocumentJob.available_at: datetime.utcnow(),
            DocumentJob.last_error: "Worker lease expired; retrying.",
        },
        synchronize_session=False,
    )
    db.commit()
    job = (
        db.query(DocumentJob)
        .filter(
            DocumentJob.status == "queued",
            DocumentJob.available_at <= datetime.utcnow(),
        )
        .order_by(DocumentJob.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if not job:
        return None

    job.status = "processing"
    job.started_at = datetime.utcnow()
    db.commit()
    return job


def run_one_queued_job() -> bool:
    db = SessionLocal()
    try:
        job = _claim_next_job(db)
        if not job:
            return False
        process_document(job.document_id)
        return True
    finally:
        db.close()


def processing_worker_enabled() -> bool:
    return (
        os.getenv("PROCESSING_WORKER_ENABLED", "false")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"}
    )


_worker_stop = threading.Event()
_worker_thread: threading.Thread | None = None


def start_processing_worker() -> None:
    global _worker_thread
    if not processing_worker_enabled() or _worker_thread is not None:
        return

    _worker_stop.clear()

    def worker_loop() -> None:
        while not _worker_stop.is_set():
            try:
                processed = run_one_queued_job()
            except Exception:
                processed = False
            if not processed:
                _worker_stop.wait(2)

    _worker_thread = threading.Thread(
        target=worker_loop,
        name="document-processing-worker",
        daemon=True,
    )
    _worker_thread.start()


def stop_processing_worker() -> None:
    global _worker_thread
    _worker_stop.set()
    if _worker_thread is not None:
        _worker_thread.join(timeout=5)
        _worker_thread = None

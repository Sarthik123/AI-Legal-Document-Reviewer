import contextlib
import io
import unittest
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import get_current_user
from app.database import Base, get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from main import app


PDF_BYTES = b"%PDF-1.4 synthetic test file"
FILENAME = "private-client-agreement.pdf"
PAGES = [(1, "This agreement starts on 1 January.")]


class DocumentProcessingTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            engine,
            tables=[Document.__table__, DocumentChunk.__table__],
        )
        self.Session = sessionmaker(bind=engine, autoflush=False)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
        self.client = TestClient(app)

        self.stored = {}

        def fake_save(filename, data):
            document_id = f"doc-{len(self.stored) + 1}"
            path = f"r2://bucket/documents/{document_id}"
            self.stored[path] = data
            return document_id, path

        def fake_read(path):
            return BytesIO(self.stored[path])

        self.patches = [
            patch("app.api.routes.save_document", side_effect=fake_save),
            patch("app.api.routes.read_document", side_effect=fake_read),
            patch("app.services.processing_service.pages_requiring_ocr", return_value=set()),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self):
        for active_patch in self.patches:
            active_patch.stop()
        app.dependency_overrides.clear()

    def upload(self):
        return self.client.post(
            "/documents",
            files={"file": (FILENAME, PDF_BYTES, "application/pdf")},
        )

    def document(self, document_id):
        with self.Session() as db:
            return db.get(Document, document_id)

    def add_document(self, status, age_minutes, error=None):
        with self.Session() as db:
            document = Document(
                id=f"existing-{status}-{age_minutes}",
                user_id="user-1",
                filename=FILENAME,
                content_type="application/pdf",
                storage_path=f"r2://bucket/documents/existing-{status}-{age_minutes}",
                processing_status=status,
                processing_error=error,
                created_at=datetime.utcnow() - timedelta(minutes=age_minutes),
            )
            db.add(document)
            db.commit()
            self.stored[document.storage_path] = PDF_BYTES
            return document.id

    # --- Stuck-status fix -------------------------------------------------

    @patch("app.services.processing_service.process_document_chunks", return_value=2)
    @patch("app.services.processing_service.extract_pages_from_pdf", return_value=PAGES)
    def test_successful_upload_is_processed(self, *_):
        response = self.upload()

        self.assertEqual(response.status_code, 200)
        document = self.document(response.json()["document_id"])
        self.assertEqual(document.processing_status, "processed")
        self.assertIsNone(document.processing_error)

    @patch(
        "app.services.processing_service.extract_pages_from_pdf",
        side_effect=RuntimeError("corrupt xref"),
    )
    def test_extraction_failure_marks_failed_not_uploaded(self, _):
        response = self.upload()

        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertEqual(body["reason"], "extraction_failed")
        self.assertEqual(
            body["detail"],
            "Something went wrong while processing your document.",
        )
        document = self.document(body["document_id"])
        self.assertEqual(document.processing_status, "failed")
        self.assertEqual(document.processing_error, "extraction_failed")

    @patch("app.services.processing_service.extract_pages_with_ocr", side_effect=RuntimeError("ocr down"))
    @patch("app.services.processing_service.extract_pages_from_pdf", return_value=[(1, "")])
    def test_ocr_failure_marks_failed(self, *_):
        with patch("app.services.processing_service.pages_requiring_ocr", return_value={1}):
            response = self.upload()

        self.assertEqual(response.json()["reason"], "ocr_failed")
        self.assertEqual(
            self.document(response.json()["document_id"]).processing_status,
            "failed",
        )

    @patch("app.services.processing_service.extract_pages_from_pdf", return_value=[(1, "")])
    def test_no_text_marks_failed_with_specific_message(self, _):
        response = self.upload()

        body = response.json()
        self.assertEqual(body["reason"], "no_text")
        self.assertIn("No readable text", body["detail"])
        self.assertEqual(self.document(body["document_id"]).processing_error, "no_text")

    @patch(
        "app.services.processing_service.process_document_chunks",
        side_effect=RuntimeError("embedding service unavailable"),
    )
    @patch("app.services.processing_service.extract_pages_from_pdf", return_value=PAGES)
    def test_embedding_failure_marks_failed_and_keeps_file_for_retry(self, *_):
        response = self.upload()

        body = response.json()
        self.assertEqual(body["reason"], "embedding_failed")
        document = self.document(body["document_id"])
        self.assertEqual(document.processing_status, "failed")
        self.assertIn(document.storage_path, self.stored)

    def test_storage_failure_returns_reason_code(self):
        with patch("app.api.routes.save_document", side_effect=RuntimeError("r2 down")):
            response = self.upload()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["reason"], "storage_failed")

    def test_interrupted_document_is_marked_failed_on_next_read(self):
        stale_id = self.add_document("uploaded", age_minutes=60)
        stale_processing_id = self.add_document("processing", age_minutes=30)
        fresh_id = self.add_document("uploaded", age_minutes=1)

        listed = {
            item["document_id"]: item
            for item in self.client.get("/documents").json()
        }

        self.assertEqual(listed[stale_id]["processing_status"], "failed")
        self.assertEqual(listed[stale_id]["processing_error"], "interrupted")
        self.assertEqual(listed[stale_processing_id]["processing_status"], "failed")
        self.assertEqual(listed[fresh_id]["processing_status"], "uploaded")

        single = self.client.get(f"/documents/{stale_id}").json()
        self.assertEqual(single["processing_status"], "failed")

    def test_retry_in_progress_on_old_document_is_not_marked_interrupted(self):
        document_id = self.add_document("uploaded", age_minutes=60)
        with self.Session() as db:
            document = db.get(Document, document_id)
            document.processing_started_at = datetime.utcnow()
            db.commit()

        single = self.client.get(f"/documents/{document_id}").json()

        self.assertEqual(single["processing_status"], "uploaded")
        self.assertEqual(
            self.client.post(f"/documents/{document_id}/analyze").status_code,
            409,
        )

    @patch(
        "app.services.processing_service.extract_pages_from_pdf",
        side_effect=RuntimeError("corrupt xref"),
    )
    def test_failure_logs_never_contain_file_name_or_text(self, _):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.upload()

        logged = output.getvalue()
        self.assertIn("reason=extraction_failed", logged)
        self.assertNotIn(FILENAME, logged)
        self.assertNotIn("corrupt xref", logged)

    # --- Retry flow -------------------------------------------------------

    @patch("app.api.routes.analyze_document", return_value={"summary": "ok"})
    @patch("app.services.processing_service.process_document_chunks", return_value=3)
    @patch("app.services.processing_service.extract_pages_from_pdf", return_value=PAGES)
    def test_retry_reprocesses_failed_document_then_analyzes(self, extract, chunks, analyze):
        document_id = self.add_document("failed", age_minutes=60, error="interrupted")

        response = self.client.post(f"/documents/{document_id}/analyze")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"summary": "ok"})
        document = self.document(document_id)
        self.assertEqual(document.processing_status, "processed")
        self.assertIsNone(document.processing_error)
        extract.assert_called_once()
        analyze.assert_called_once()

    @patch("app.api.routes.analyze_document")
    @patch(
        "app.services.processing_service.process_document_chunks",
        side_effect=RuntimeError("embedding service unavailable"),
    )
    @patch("app.services.processing_service.extract_pages_from_pdf", return_value=PAGES)
    def test_failed_retry_stays_failed_with_reason(self, extract, chunks, analyze):
        document_id = self.add_document("failed", age_minutes=60, error="interrupted")

        response = self.client.post(f"/documents/{document_id}/analyze")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["reason"], "embedding_failed")
        self.assertEqual(self.document(document_id).processing_error, "embedding_failed")
        analyze.assert_not_called()

    @patch("app.api.routes.analyze_document")
    def test_retry_with_missing_file_reports_file_missing(self, analyze):
        document_id = self.add_document("failed", age_minutes=60, error="interrupted")
        self.stored.clear()

        with patch("app.api.routes.read_document", return_value=Path("/nonexistent.pdf")):
            response = self.client.post(f"/documents/{document_id}/analyze")

        self.assertEqual(response.json()["reason"], "file_missing")
        analyze.assert_not_called()

    @patch("app.api.routes.analyze_document")
    def test_analyze_while_still_processing_returns_409(self, analyze):
        document_id = self.add_document("processing", age_minutes=1)

        response = self.client.post(f"/documents/{document_id}/analyze")

        self.assertEqual(response.status_code, 409)
        analyze.assert_not_called()

    @patch("app.api.routes.analyze_document", return_value={"summary": "ok"})
    @patch("app.services.processing_service.extract_pages_from_pdf")
    def test_processed_document_is_not_reprocessed(self, extract, analyze):
        document_id = self.add_document("processed", age_minutes=60)

        response = self.client.post(f"/documents/{document_id}/analyze")

        self.assertEqual(response.status_code, 200)
        extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()

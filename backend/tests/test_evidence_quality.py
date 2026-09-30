import unittest
from pathlib import Path
from types import SimpleNamespace

from app.api.routes import serialize_chat_sources
from app.services.document_service import pages_requiring_ocr
from app.services.qa_service import (
    _evidence_for_chunk,
    _explicit_grade_answer,
    _extractive_grounded_answer,
    sanitize_citation,
)


class EvidenceQualityTests(unittest.TestCase):
    def test_scanned_page_with_garbled_hidden_text_layer_is_sent_to_ocr(self):
        scanned_pdf = (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "fixtures"
            / "synthetic-scanned-agreement.pdf"
        )
        fake_hidden_text = (
            "Entrp Jo:: L8BMEO42 and incorrectly recognized words "
            "that make this seem like extracted text."
        )

        self.assertEqual(
            pages_requiring_ocr(str(scanned_pdf), [(1, fake_hidden_text)]),
            {1},
        )

    def test_citation_uses_answer_evidence_instead_of_first_line(self):
        chunk = SimpleNamespace(
            content=(
                "MONTHLY SERVICE AGREEMENT\n"
                "Rent is $4,250 per month, due on the first day.\n"
                "This agreement begins on July 1, 2026."
            ),
            page_number=1,
        )

        citation = _evidence_for_chunk(
            "What is the monthly rent?",
            chunk,
            answer="The monthly rent is $4,250.",
        )

        self.assertIn("Line 2", citation)
        self.assertIn("$4,250 per month", citation)
        self.assertNotIn("MONTHLY SERVICE AGREEMENT", citation)

    def test_unsupported_answer_has_no_citation(self):
        chunk = SimpleNamespace(
            content="Rent is $4,250 per month.",
            page_number=1,
        )

    def test_extractive_answer_does_not_repeat_obvious_ocr_errors(self):
        chunk = SimpleNamespace(
            id="ocr-chunk",
            chunk_index=0,
            page_number=1,
            content=(
                "The Degree of @achelor of @echnologp in Mechanical Engineering "
                "was conferred in 2022."
            ),
        )

        self.assertIsNone(
            _extractive_grounded_answer(
                "What degree and year were awarded?",
                [chunk],
            )
        )

        self.assertIsNone(
            _evidence_for_chunk(
                "What is the rent?",
                chunk,
                answer="The rent is $9,999 per year.",
            )
        )

    def test_grade_question_answers_ocr_misspelled_label_with_page_citation(self):
        chunk = SimpleNamespace(
            id="ocr-grade-chunk",
            chunk_index=0,
            page_number=1,
            content=(
                "SARTHIK BHAN completed the degree.\n"
                "Cumulatibe Grave AJoint Aberage of 6.67"
            ),
        )

        result = _explicit_grade_answer(
            "what grade did Sarthik Bhan score?",
            [chunk],
        )

        self.assertIsNotNone(result)
        answer, supported, sources = result
        self.assertTrue(supported)
        self.assertIn("6.67", answer)
        self.assertEqual(
            sources,
            [
                "Page 1 · OCR text may contain recognition errors; check the PDF page."
            ],
        )

    def test_grade_answer_requires_requested_name_to_match_source(self):
        chunk = SimpleNamespace(
            id="different-student-chunk",
            chunk_index=0,
            page_number=1,
            content="Cumulative grade point average of 6.67",
        )

        self.assertIsNone(
            _explicit_grade_answer(
                "what cgpa did Sarthik Bhan score?",
                [chunk],
            )
        )

    def test_garbled_saved_ocr_quote_is_replaced_with_page_reference(self):
        citation = sanitize_citation(
            "Page 1 · Line 2: @achelot of @echnologp"
        )

        self.assertEqual(
            citation,
            "Page 1 · OCR text may contain recognition errors; check the PDF page.",
        )

    def test_chat_history_sanitizes_previously_saved_ocr_citations(self):
        sources = serialize_chat_sources(
            [
                {
                    "source": 1,
                    "content": "Page 1 · Line 1: Entrp Jo:: L8BMEO42",
                }
            ]
        )

        self.assertEqual(
            sources[0]["content"],
            "Page 1 · OCR text may contain recognition errors; check the PDF page.",
        )


if __name__ == "__main__":
    unittest.main()

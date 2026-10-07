"""
Tests that both answer-quality prompt rules are present in the prompt
sent to the model, that placeholder answers flow through correctly,
and that the extractive path routes problematic sentences to the LLM.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch


def _make_chunk(content: str, page_number: int = 1) -> object:
    return SimpleNamespace(
        id="test-chunk",
        chunk_index=0,
        page_number=page_number,
        content=content,
        embedding=None,
    )


class PromptRuleTests(unittest.TestCase):
    def _captured_prompt(self, chunk: object, question: str) -> str:
        """Return the prompt string sent to _call_ollama for the given chunk/question."""
        from app.services.qa_service import generate_grounded_answer

        captured: list[str] = []

        def fake_call(prompt: str, *args, **kwargs):
            captured.append(prompt)
            return None  # triggers ABSTENTION_MESSAGE — we only care about the prompt

        # Force the extractive/grade/experience/party fast-paths to return None so
        # the prompt-building code always runs.
        with (
            patch("app.services.qa_service._extractive_grounded_answer", return_value=None),
            patch("app.services.qa_service._explicit_grade_answer", return_value=None),
            patch("app.services.qa_service._explicit_experience_answer", return_value=None),
            patch("app.services.qa_service._explicit_party_answer", return_value=None),
            patch("app.services.qa_service._call_ollama", side_effect=fake_call),
        ):
            generate_grounded_answer(question, "test.pdf", [chunk])

        self.assertTrue(captured, "Expected _call_ollama to be called")
        return captured[0]

    def test_direct_sentence_rule_is_in_prompt(self):
        """Rule 12: prompt must instruct the model to answer with a direct sentence first."""
        chunk = _make_chunk(
            "The Lessee shall pay all real estate taxes assessed against the property."
        )
        prompt = self._captured_prompt(chunk, "Who pays the taxes?")

        self.assertIn("directly answers", prompt)
        self.assertIn("complete sentence", prompt)

    def test_blank_placeholder_rule_is_in_prompt(self):
        """Rule 13: prompt must instruct the model to report blanks instead of quoting them."""
        chunk = _make_chunk(
            "The Owner is: ____.\nThe Tenant is: (Name of the Tenant)."
        )
        prompt = self._captured_prompt(chunk, "Who is the owner?")

        self.assertIn("blank", prompt.lower())
        self.assertIn("placeholder", prompt.lower())
        self.assertIn("This is left blank in the document.", prompt)

    def test_blank_placeholder_answer_passes_through(self):
        """When the model correctly identifies a blank, the answer is not suppressed."""
        from app.services.qa_service import generate_grounded_answer

        chunk = _make_chunk(
            "The Owner is: ____.\nThe Tenant is: (Name of the Tenant).",
        )

        blank_response = {
            "answerable": True,
            "answer": "This is left blank in the document.",
            "sources": [1],
        }

        # Stub evidence so the answer isn't filtered out by the citation check.
        fake_citation = "Page 1 · Line 1: The Owner is: ____."

        with (
            patch("app.services.qa_service._extractive_grounded_answer", return_value=None),
            patch("app.services.qa_service._explicit_grade_answer", return_value=None),
            patch("app.services.qa_service._explicit_experience_answer", return_value=None),
            patch("app.services.qa_service._explicit_party_answer", return_value=None),
            patch("app.services.qa_service._call_ollama", return_value=blank_response),
            patch("app.services.qa_service._evidence_for_chunk", return_value=fake_citation),
        ):
            answer, supported, evidence = generate_grounded_answer(
                "Who is the owner?", "lease.pdf", [chunk]
            )

        self.assertTrue(supported)
        self.assertIn("left blank", answer)
        self.assertEqual(evidence, [fake_citation])


class ExtractivePathRulesTests(unittest.TestCase):
    """Extractive path must fall through to the LLM for cut-off and placeholder cases."""

    def _chunk(self, content: str, idx: int = 0) -> object:
        return SimpleNamespace(
            id=f"chunk-{idx}",
            chunk_index=idx,
            page_number=1,
            content=content,
            embedding=None,
        )

    def test_extractive_returns_none_for_underscore_blank(self):
        """A sentence with '____' must not be returned; LLM will apply Rule 13."""
        from app.services.qa_service import _extractive_grounded_answer

        chunk = self._chunk(
            "The Owner is: ____.\nThe Tenant pays rent monthly."
        )
        # "owner" and "name" are question tokens that match the blank line.
        result = _extractive_grounded_answer("Who is the owner?", [chunk])
        self.assertIsNone(result)

    def test_extractive_returns_none_for_parenthetical_placeholder(self):
        """A sentence with '(Name of the Owner)' must not be returned."""
        from app.services.qa_service import _extractive_grounded_answer

        chunk = self._chunk(
            "Lessor: (Name of the Owner).\nLessee: Acme Corp."
        )
        result = _extractive_grounded_answer("Who is the lessor?", [chunk])
        self.assertIsNone(result)

    def test_extractive_returns_none_for_sentence_over_500_chars(self):
        """A sentence longer than 500 chars must not be truncated; fall through to LLM."""
        from app.services.qa_service import _extractive_grounded_answer

        long_sentence = (
            "The Lessee agrees to pay all taxes, levies, duties, and assessments "
            "of every kind and nature whatsoever assessed or imposed upon the "
            "leased premises, including but not limited to real property taxes, "
            "personal property taxes, and special assessments, "
            + "x" * 300  # push well past 500 chars
        )
        chunk = self._chunk(long_sentence + "\nRent is due on the first.")
        result = _extractive_grounded_answer("Who pays taxes?", [chunk])
        self.assertIsNone(result)

    def test_extractive_still_works_for_clean_short_sentences(self):
        """Ensure the guard doesn't break normal extractive answers."""
        from app.services.qa_service import _extractive_grounded_answer

        chunk = self._chunk(
            "The Lessee pays all real estate taxes.\nRent is $1,500 per month."
        )
        result = _extractive_grounded_answer("Who pays taxes?", [chunk])
        self.assertIsNotNone(result)
        answer, supported, evidence = result
        self.assertTrue(supported)
        self.assertIn("taxes", answer.lower())

    def test_extractive_returns_none_for_line_fragment(self):
        """PDF line fragments that don't end a sentence must fall through to LLM."""
        from app.services.qa_service import _extractive_grounded_answer

        chunk = self._chunk(
            "charged thereon in\nterminate on the delivery of written\n"
            "The rent shall be paid on the first of each month."
        )
        # The first two lines are fragments; only the last ends properly.
        # "charged" / "terminate" don't match "rent" question tokens well, so
        # if the fragmentary lines are the best match the function must return None.
        result = _extractive_grounded_answer(
            "When does the agreement terminate or charge fees?", [chunk]
        )
        # Either None (fragment routed to LLM) or a result whose answer ends
        # in a sentence-terminal character — never a bare fragment.
        if result is not None:
            answer, _, _ = result
            self.assertTrue(
                answer.rstrip().endswith((".", "?", "!", ";")),
                f"Answer must end a sentence, got: {answer!r}",
            )

    def test_extractive_returns_none_for_real_cut_off_lines(self):
        """The two real cut-off answers from the eval must not be quoted."""
        from app.services.qa_service import _extractive_grounded_answer

        for question, content in [
            (
                "What interest is charged on late rent?",
                "Interest on late rent shall be charged thereon in\n"
                "accordance with the schedule.",
            ),
            (
                "How does the tenancy terminate?",
                "The tenancy shall terminate on the delivery of written\n"
                "notice by either party.",
            ),
        ]:
            with self.subTest(question=question):
                self.assertIsNone(
                    _extractive_grounded_answer(question, [self._chunk(content)])
                )

    def test_extractive_keeps_ocr_line_with_garbled_final_period(self):
        """OCR often reads a final period as '_'; the value must still be answered."""
        from app.services.qa_service import _extractive_grounded_answer

        chunk = self._chunk(
            "OCR SERVICE AGREEMENT\n"
            "Customer: Meadow Test Company.\n"
            "OCR verification token: PINEAPPLE-7391-OTTER_\n"
            "Monthly amount: $1,275."
        )
        result = _extractive_grounded_answer(
            "What is the OCR verification token?", [chunk]
        )
        self.assertIsNotNone(result)
        self.assertIn("PINEAPPLE-7391-OTTER", result[0])

    # --- Real-world placeholder examples ---

    def test_extractive_returns_none_for_complete_address_placeholder(self):
        """'(Complete Address ofthe Rented Property)' must be routed to LLM."""
        from app.services.qa_service import _extractive_grounded_answer

        chunk = self._chunk(
            "The property is located at (Complete Address ofthe Rented Property)."
        )
        result = _extractive_grounded_answer("Where is the property?", [chunk])
        self.assertIsNone(result)

    def test_extractive_returns_none_for_bracket_date_placeholder(self):
        """'dated [__]' must be routed to LLM."""
        from app.services.qa_service import _extractive_grounded_answer

        chunk = self._chunk(
            "This agreement is dated [__] and entered into between the parties."
        )
        result = _extractive_grounded_answer("When was the agreement dated?", [chunk])
        self.assertIsNone(result)

    def test_extractive_returns_none_for_city_placeholder(self):
        """'(city) civil courts' must be routed to LLM."""
        from app.services.qa_service import _extractive_grounded_answer

        chunk = self._chunk(
            "Disputes shall be subject to the jurisdiction of (city) civil courts."
        )
        result = _extractive_grounded_answer("Which court has jurisdiction?", [chunk])
        self.assertIsNone(result)


class LLMPlaceholderPostCheckTests(unittest.TestCase):
    """Post-check must replace placeholder answers the LLM returns despite Rule 13."""

    def _run(self, llm_answer: str) -> tuple:
        """Run generate_grounded_answer with the given LLM answer, return (answer, supported, evidence)."""
        from app.services.qa_service import generate_grounded_answer

        chunk = SimpleNamespace(
            id="chunk-0",
            chunk_index=0,
            page_number=3,
            content="The enhanced rental is Rs. ____.",
            embedding=None,
        )
        fake_citation = "Page 3 · Line 1: The enhanced rental is Rs. ____."

        with (
            patch("app.services.qa_service._extractive_grounded_answer", return_value=None),
            patch("app.services.qa_service._explicit_grade_answer", return_value=None),
            patch("app.services.qa_service._explicit_experience_answer", return_value=None),
            patch("app.services.qa_service._explicit_party_answer", return_value=None),
            patch("app.services.qa_service._call_ollama", return_value={
                "answerable": True,
                "answer": llm_answer,
                "sources": [1],
            }),
            patch("app.services.qa_service._evidence_for_chunk", return_value=fake_citation),
        ):
            return generate_grounded_answer("What is the enhanced rental?", "lease.pdf", [chunk])

    def test_underscore_blank_in_answer_is_replaced(self):
        """'The enhanced rental is Rs. ____' must become the blank message."""
        answer, supported, evidence = self._run("The enhanced rental is Rs. ____.")
        self.assertTrue(supported)
        self.assertEqual(answer, "This is left blank in the document.")
        self.assertTrue(len(evidence) > 0)

    def test_parenthetical_name_placeholder_in_answer_is_replaced(self):
        """'(Name of the Owner)' in the answer must be replaced."""
        answer, supported, evidence = self._run(
            "The owner of the property is (Name of the Owner)."
        )
        self.assertTrue(supported)
        self.assertEqual(answer, "This is left blank in the document.")

    def test_city_placeholder_in_answer_is_replaced(self):
        """'the (city) civil courts' in the answer must be replaced."""
        answer, supported, evidence = self._run(
            "Disputes are subject to the jurisdiction of the (city) civil courts."
        )
        self.assertTrue(supported)
        self.assertEqual(answer, "This is left blank in the document.")

    def test_clean_answer_is_not_replaced(self):
        """A normal answer without placeholders must pass through unchanged."""
        answer, supported, evidence = self._run("The enhanced rental is Rs. 15,000 per month.")
        self.assertTrue(supported)
        self.assertIn("15,000", answer)


if __name__ == "__main__":
    unittest.main()

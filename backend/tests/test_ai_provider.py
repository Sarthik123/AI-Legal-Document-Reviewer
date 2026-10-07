import json
import os
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

from app.services.ai_provider import call_model, ai_observability_context
from app.services.analysis_service import (
    AnalysisGenerationError,
    _call_analysis_model,
)


class CloudflareStructuredOutputTests(unittest.TestCase):
    @patch.dict(os.environ, {
        "AI_PROVIDER": "cloudflare_workers_ai",
        "CLOUDFLARE_ACCOUNT_ID": "test-account",
        "CLOUDFLARE_API_TOKEN": "test-token",
    })
    @patch("app.services.ai_provider.urllib.request.urlopen")
    def test_json_mode_is_sent_and_object_response_is_serialized(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value = BytesIO(json.dumps({
            "success": True,
            "result": {"response": {"summary": "A valid result."}},
        }).encode("utf-8"))
        urlopen.return_value = response

        result = call_model(
            [{"role": "user", "content": "Analyze this."}],
            10,
            response_format={"type": "json_schema", "json_schema": {"type": "object"}},
        )

        self.assertEqual(json.loads(result), {"summary": "A valid result."})
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["response_format"]["type"], "json_schema")

    @patch.dict(os.environ, {"AI_PROVIDER": "ollama"})
    @patch("app.services.analysis_service.call_model")
    def test_analysis_retries_an_incomplete_response(self, call_model_mock):
        call_model_mock.side_effect = [
            '{"summary": "cut off',
            json.dumps({
                "summary": "A concise summary.",
                "key_points": [],
                "risks": [],
                "missing_information": [],
            }),
        ]

        result = _call_analysis_model("Analyze this document.")

        self.assertEqual(result["summary"], "A concise summary.")
        self.assertEqual(call_model_mock.call_count, 2)

    @patch.dict(os.environ, {"AI_PROVIDER": "cloudflare_workers_ai"})
    @patch("app.services.analysis_service.call_model")
    def test_analysis_uses_cloudflare_json_schema(self, call_model_mock):
        call_model_mock.return_value = json.dumps({
            "summary": "A concise summary.",
            "key_points": [],
            "risks": [],
            "missing_information": [],
        })

        _call_analysis_model("Analyze this document.")

        self.assertEqual(
            call_model_mock.call_args.kwargs["response_format"]["type"],
            "json_schema",
        )

    @patch.dict(os.environ, {"AI_PROVIDER": "ollama"})
    @patch("app.services.analysis_service.call_model", return_value='{"summary": "cut off')
    def test_analysis_reports_an_incomplete_response_after_retry(self, call_model_mock):
        with self.assertRaises(AnalysisGenerationError):
            _call_analysis_model("Analyze this document.")
        self.assertEqual(call_model_mock.call_count, 2)


class PostHogPrivacyTests(unittest.TestCase):
    """Verify that document text and AI answers never reach PostHog."""

    _BANNED_KEYS = {"$ai_input", "$ai_output", "$ai_output_choices"}

    def _make_posthog_client(self):
        client = MagicMock()
        captured_calls = []

        def capture(event, *, distinct_id, properties):
            captured_calls.append(properties)

        client.capture.side_effect = capture
        return client, captured_calls

    @patch.dict(os.environ, {
        "AI_PROVIDER": "ollama",
        "OLLAMA_URL": "http://127.0.0.1:11434/api/chat",
        "OLLAMA_MODEL": "qwen2.5:3b",
    })
    @patch("app.services.ai_provider.urllib.request.urlopen")
    @patch("app.services.ai_provider.posthog_integration")
    def test_posthog_never_receives_ai_input_or_output_on_success(
        self, posthog_mod, urlopen
    ):
        client, calls = self._make_posthog_client()
        posthog_mod.posthog_client = client

        response = MagicMock()
        response.__enter__.return_value = BytesIO(json.dumps({
            "message": {"content": json.dumps({"summary": "test"})},
        }).encode())
        urlopen.return_value = response

        with ai_observability_context("sess-1", "user-1"):
            call_model([{"role": "user", "content": "Sensitive question about my contract."}], 100)

        self.assertTrue(calls, "Expected at least one PostHog capture call.")
        for props in calls:
            for banned in self._BANNED_KEYS:
                self.assertNotIn(
                    banned,
                    props,
                    f"PostHog received banned key '{banned}' — document text or AI output leaked.",
                )

    @patch.dict(os.environ, {
        "AI_PROVIDER": "ollama",
        "OLLAMA_URL": "http://127.0.0.1:11434/api/chat",
        "OLLAMA_MODEL": "qwen2.5:3b",
    })
    @patch("app.services.ai_provider.urllib.request.urlopen")
    @patch("app.services.ai_provider.posthog_integration")
    def test_posthog_never_receives_ai_input_or_output_on_error(
        self, posthog_mod, urlopen
    ):
        client, calls = self._make_posthog_client()
        posthog_mod.posthog_client = client

        urlopen.side_effect = OSError("connection refused")

        with self.assertRaises(OSError):
            with ai_observability_context("sess-2", "user-2"):
                call_model([{"role": "user", "content": "My lease agreement text here."}], 100)

        self.assertTrue(calls, "Expected at least one PostHog capture call on error.")
        for props in calls:
            for banned in self._BANNED_KEYS:
                self.assertNotIn(
                    banned,
                    props,
                    f"PostHog received banned key '{banned}' on error path.",
                )

    @patch.dict(os.environ, {
        "AI_PROVIDER": "cloudflare_workers_ai",
        "CLOUDFLARE_ACCOUNT_ID": "acct",
        "CLOUDFLARE_API_TOKEN": "tok",
    })
    @patch("app.services.ai_provider.urllib.request.urlopen")
    @patch("app.services.ai_provider.posthog_integration")
    def test_posthog_never_receives_ai_input_or_output_cloudflare(
        self, posthog_mod, urlopen
    ):
        client, calls = self._make_posthog_client()
        posthog_mod.posthog_client = client

        response = MagicMock()
        response.__enter__.return_value = BytesIO(json.dumps({
            "success": True,
            "result": {"response": "Answer grounded in document."},
        }).encode())
        urlopen.return_value = response

        with ai_observability_context("sess-3", "user-3"):
            call_model([{"role": "user", "content": "What does clause 5 say?"}], 200)

        self.assertTrue(calls, "Expected at least one PostHog capture call.")
        for props in calls:
            for banned in self._BANNED_KEYS:
                self.assertNotIn(
                    banned,
                    props,
                    f"PostHog received banned key '{banned}' via Cloudflare path.",
                )


if __name__ == "__main__":
    unittest.main()

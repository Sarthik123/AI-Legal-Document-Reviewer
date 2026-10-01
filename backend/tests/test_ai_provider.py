import json
import os
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

from app.services.ai_provider import call_model
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


if __name__ == "__main__":
    unittest.main()

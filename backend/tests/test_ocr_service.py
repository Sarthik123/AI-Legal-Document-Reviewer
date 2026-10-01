import base64
import json
import os
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.ocr_service import extract_pages_with_ocr


class CloudflareOCRTests(unittest.TestCase):
    def setUp(self):
        self.scanned_pdf = (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "fixtures"
            / "synthetic-scanned-agreement.pdf"
        )

    @patch.dict(os.environ, {
        "AI_PROVIDER": "cloudflare_workers_ai",
        "CLOUDFLARE_ACCOUNT_ID": "test-account",
        "CLOUDFLARE_API_TOKEN": "test-token",
    })
    @patch("app.services.ocr_service.urllib.request.urlopen")
    def test_scanned_page_uses_remote_ocr_without_loading_easyocr(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value = BytesIO(json.dumps({
            "success": True,
            "result": {"answer": "OCR verification token: PINEAPPLE-7391-OTTER."},
        }).encode("utf-8"))
        urlopen.return_value = response

        pages = extract_pages_with_ocr(str(self.scanned_pdf))

        self.assertEqual(
            pages,
            [(1, "OCR verification token: PINEAPPLE-7391-OTTER.")],
        )
        request = urlopen.call_args.args[0]
        self.assertIn("@cf/moondream/moondream3.1-9B-A2B", request.full_url)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        payload = json.loads(request.data)
        self.assertEqual(payload["task"], "query")
        self.assertIn("data:image/jpeg;base64,", payload["image"])
        self.assertTrue(
            base64.b64decode(payload["image"].split(",", 1)[1]).startswith(b"\xff\xd8")
        )
        self.assertIn("Do not summarize", payload["question"])
        urlopen.assert_called_once_with(request, timeout=60)

    @patch.dict(os.environ, {
        "AI_PROVIDER": "cloudflare_workers_ai",
        "CLOUDFLARE_ACCOUNT_ID": "",
        "CLOUDFLARE_API_TOKEN": "",
    })
    @patch("app.services.ocr_service.urllib.request.urlopen")
    def test_missing_cloudflare_credentials_fails_clearly(self, urlopen):
        with self.assertRaisesRegex(RuntimeError, "not configured for OCR"):
            extract_pages_with_ocr(str(self.scanned_pdf))
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from ai_client import AIClient, AIProviderError, extract_json, load_env_file  # noqa: E402


class AIClientTests(unittest.TestCase):
    def test_extract_plain_json(self) -> None:
        self.assertEqual(extract_json('{"ok": true}'), {"ok": True})

    def test_extract_fenced_json(self) -> None:
        self.assertEqual(extract_json('```json\n{"value": 2}\n```'), {"value": 2})

    def test_extract_rejects_non_json(self) -> None:
        with self.assertRaises(AIProviderError):
            extract_json("not json")

    def test_endpoint_accepts_base_or_full_path(self) -> None:
        base = AIClient("key", "https://example.com/v1", "model")
        full = AIClient("key", "https://example.com/v1/chat/completions", "model")
        self.assertEqual(base.endpoint, "https://example.com/v1/chat/completions")
        self.assertEqual(full.endpoint, "https://example.com/v1/chat/completions")

    def test_missing_model_is_not_configured(self) -> None:
        self.assertFalse(AIClient("key", "https://example.com/v1", "").configured)

    def test_deepseek_json_request_options(self) -> None:
        client = AIClient("key", "https://api.deepseek.com", "deepseek-v4-flash")

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"choices":[{"message":{"content":"{\\\"ok\\\":true}"}}]}'

        with patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            self.assertEqual(client.chat_json("Return json.", {"task": "test"}), {"ok": True})

        request_body = __import__("json").loads(urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(request_body["model"], "deepseek-v4-flash")
        self.assertEqual(request_body["response_format"], {"type": "json_object"})
        self.assertEqual(request_body["thinking"], {"type": "disabled"})


if __name__ == "__main__":
    unittest.main()

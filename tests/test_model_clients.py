"""
Unit tests for ProcureBench LLM client integrations (Gemini and Ollama).
Uses mocks exclusively to ensure no actual network requests or API costs occur during testing.
"""

import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.llm_clients import (
    build_benchmark_prompt,
    generate_gemini_response,
    generate_ollama_response,
    GEMINI_DEFAULT_MODEL,
    OLLAMA_DEFAULT_MODEL,
)


class TestModelClients(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dataset_path = PROJECT_ROOT / "dataset" / "test_cases.json"
        with open(dataset_path, "r", encoding="utf-8") as f:
            cls.test_cases = json.load(f)
        cls.sample_case = cls.test_cases[0]  # PROC-001

    def test_shared_prompt_construction(self):
        """Prompt must include case metadata, scenario, transaction data, and policy instructions."""
        prompt = build_benchmark_prompt(self.sample_case)

        self.assertIn("PROC-001", prompt)
        self.assertIn("Quantity Mismatch", prompt)
        self.assertIn("Horizon Components", prompt)
        self.assertIn("POL-02-QTY-MATCH", prompt)
        self.assertIn("decision", prompt)
        self.assertIn("risk_level", prompt)
        self.assertIn("discrepancies", prompt)
        self.assertIn("payment_allowed", prompt)

    def test_expected_answers_excluded_from_model_inputs(self):
        """
        CRITICAL BENCHMARK FAIRNESS RULE:
        Expected answers, gold decisions, or scoring keys must NEVER be leaked in the prompt.
        """
        # Ensure input case has expected_answer
        self.assertIn("expected_answer", self.sample_case)

        prompt = build_benchmark_prompt(self.sample_case)

        # Check that expected_answer structure is completely absent
        self.assertNotIn("expected_answer", prompt)
        # Check that gold reasoning text is not in the prompt
        gold_reasoning = self.sample_case["expected_answer"]["reasoning"]
        self.assertNotIn(gold_reasoning, prompt)
        # Check that gold next_action text is not in the prompt
        gold_next_action = self.sample_case["expected_answer"]["next_action"]
        self.assertNotIn(gold_next_action, prompt)

    @patch("google.genai.Client")
    def test_gemini_returns_raw_text_and_metadata(self, mock_client_cls):
        """Gemini client must return raw model text and proper execution metadata."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"decision": "HOLD", "risk_level": "HIGH"}'
        mock_client.models.generate_content.return_value = mock_response

        result = generate_gemini_response(
            prompt="Evaluate transaction",
            model="gemini-flash-latest",
            api_key="mock_test_key",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "gemini")
        self.assertEqual(result["model"], "gemini-flash-latest")
        self.assertEqual(result["raw_text"], '{"decision": "HOLD", "risk_level": "HIGH"}')
        self.assertIsNone(result["error"])
        self.assertGreaterEqual(result["latency_seconds"], 0.0)

    @patch("google.genai.Client")
    def test_gemini_called_without_afc_or_tools(self, mock_client_cls):
        """Gemini must be invoked with AFC disabled and without tool declarations."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"decision": "HOLD"}'
        mock_client.models.generate_content.return_value = mock_response

        generate_gemini_response(
            prompt="Evaluate transaction",
            model="gemini-flash-latest",
            api_key="mock_test_key",
        )

        # Inspect generate_content arguments
        mock_client.models.generate_content.assert_called_once()
        _, kwargs = mock_client.models.generate_content.call_args
        config = kwargs.get("config")

        self.assertIsNotNone(config)
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertIsNone(config.tools)
        self.assertIsNone(config.tool_config)
        self.assertIsNotNone(config.automatic_function_calling)
        self.assertTrue(config.automatic_function_calling.disable)

    @patch("urllib.request.urlopen")
    def test_ollama_returns_raw_text_and_metadata(self, mock_urlopen):
        """Ollama client must return raw model text and proper execution metadata."""
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = json.dumps(
            {"response": '{"decision": "HOLD", "risk_level": "HIGH"}'}
        ).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = generate_ollama_response(
            prompt="Evaluate transaction",
            model="llama3.2:1b",
            base_url="http://localhost:11434",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "ollama")
        self.assertEqual(result["model"], "llama3.2:1b")
        self.assertEqual(result["raw_text"], '{"decision": "HOLD", "risk_level": "HIGH"}')
        self.assertIsNone(result["error"])
        self.assertGreaterEqual(result["latency_seconds"], 0.0)

    def test_missing_gemini_api_key(self):
        """Missing API key must return an error response gracefully without crashing."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True):
            result = generate_gemini_response("Evaluate transaction", api_key=None)

            self.assertFalse(result["success"])
            self.assertEqual(result["provider"], "gemini")
            self.assertIsNone(result["raw_text"])
            self.assertIn("GEMINI_API_KEY", result["error"])

    @patch("urllib.request.urlopen")
    def test_ollama_connection_failure(self, mock_urlopen):
        """Connection failure (e.g. Ollama daemon not running) must be handled gracefully."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = generate_ollama_response(
            prompt="Evaluate transaction",
            base_url="http://localhost:11434",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["provider"], "ollama")
        self.assertIsNone(result["raw_text"])
        self.assertIn("connection error", result["error"].lower())

    @patch("google.genai.Client")
    def test_gemini_empty_response(self, mock_client_cls):
        """Empty response from Gemini must return success=False with clear error message."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response

        result = generate_gemini_response(
            prompt="Evaluate transaction",
            api_key="mock_test_key",
        )

        self.assertFalse(result["success"])
        self.assertIsNone(result["raw_text"])
        self.assertIn("empty", result["error"].lower())

    @patch("urllib.request.urlopen")
    def test_ollama_empty_response(self, mock_urlopen):
        """Empty response from Ollama must return success=False with clear error message."""
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = json.dumps({"response": "   "}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = generate_ollama_response(prompt="Evaluate transaction")

        self.assertFalse(result["success"])
        self.assertIsNone(result["raw_text"])
        self.assertIn("empty", result["error"].lower())

    @patch("google.genai.Client")
    def test_gemini_error_redacts_api_key(self, mock_client_cls):
        """API errors must never expose secret API key strings in error messages."""
        secret_key = "AIzaSySecretFakeKey12345"
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception(
            f"Quota exceeded for credentials {secret_key}"
        )

        result = generate_gemini_response(
            prompt="Evaluate transaction",
            api_key=secret_key,
        )

        self.assertFalse(result["success"])
        self.assertNotIn(secret_key, result["error"])
        self.assertIn("[REDACTED_KEY]", result["error"])


if __name__ == "__main__":
    unittest.main()


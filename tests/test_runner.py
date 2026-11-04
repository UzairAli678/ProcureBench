"""
Unit tests for ProcureBench Benchmark Runner.
Uses mocks to verify execution workflow, scoring integration, fairness, and result serialization.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.runner import load_test_cases, run_benchmark, DEFAULT_DATASET_PATH


class TestBenchmarkRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset_path = DEFAULT_DATASET_PATH
        with open(cls.dataset_path, "r", encoding="utf-8") as f:
            cls.test_cases = json.load(f)

    def setUp(self):
        self.sleep_patcher = patch("evaluation.runner.time.sleep")
        self.mock_sleep = self.sleep_patcher.start()

    def tearDown(self):
        self.sleep_patcher.stop()

    def test_loading_all_10_cases(self):
        """Must load exactly 10 benchmark test cases from test_cases.json."""
        cases = load_test_cases(self.dataset_path)
        self.assertEqual(len(cases), 10)
        case_ids = [c["case_id"] for c in cases]
        self.assertEqual(len(set(case_ids)), 10)

    @patch("evaluation.runner.generate_ollama_response")
    @patch("evaluation.runner.generate_gemini_response")
    def test_running_both_providers_and_20_evaluations_attempted(
        self, mock_gemini, mock_ollama
    ):
        """Runner must execute 10 cases per provider, totaling 20 evaluations."""
        # Setup mock return values
        mock_gemini.return_value = {
            "provider": "gemini",
            "model": "gemini-flash-latest",
            "raw_text": json.dumps({
                "decision": "HOLD",
                "risk_level": "HIGH",
                "discrepancies": ["DISC-QTY-MISMATCH"],
                "evidence": ["Evidence 1"],
                "reasoning": "Reason 1",
                "next_action": "Action 1",
                "payment_allowed": False,
            }),
            "latency_seconds": 0.5,
            "success": True,
            "error": None,
        }
        mock_ollama.return_value = {
            "provider": "ollama",
            "model": "llama3.2:1b",
            "raw_text": json.dumps({
                "decision": "HOLD",
                "risk_level": "HIGH",
                "discrepancies": ["DISC-QTY-MISMATCH"],
                "evidence": ["Evidence 1"],
                "reasoning": "Reason 1",
                "next_action": "Action 1",
                "payment_allowed": False,
            }),
            "latency_seconds": 0.3,
            "success": True,
            "error": None,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir)
            summary = run_benchmark(
                dataset_path=self.dataset_path,
                output_dir=temp_output,
                providers=["gemini", "ollama"],
            )

            self.assertEqual(mock_gemini.call_count, 10)
            self.assertEqual(mock_ollama.call_count, 10)
            self.assertEqual(summary["total_evaluations_attempted"], 20)
            self.assertEqual(summary["providers"]["gemini"]["total_cases_attempted"], 10)
            self.assertEqual(summary["providers"]["ollama"]["total_cases_attempted"], 10)

    @patch("evaluation.runner.generate_ollama_response")
    @patch("evaluation.runner.generate_gemini_response")
    def test_expected_answers_never_reach_model_clients(
        self, mock_gemini, mock_ollama
    ):
        """
        CRITICAL BENCHMARK FAIRNESS RULE:
        Verify that prompts passed to both model generators never contain expected answers.
        """
        mock_gemini.return_value = {
            "provider": "gemini",
            "model": "gemini-flash-latest",
            "raw_text": '{"decision": "HOLD"}',
            "latency_seconds": 0.1,
            "success": True,
            "error": None,
        }
        mock_ollama.return_value = {
            "provider": "ollama",
            "model": "llama3.2:1b",
            "raw_text": '{"decision": "HOLD"}',
            "latency_seconds": 0.1,
            "success": True,
            "error": None,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            run_benchmark(
                dataset_path=self.dataset_path,
                output_dir=Path(temp_dir),
                providers=["gemini", "ollama"],
            )

        # Inspect all prompts received by Gemini
        for call_args in mock_gemini.call_args_list:
            prompt_str = call_args[1].get("prompt") or call_args[0][0]
            self.assertNotIn("expected_answer", prompt_str)

        # Inspect all prompts received by Ollama
        for call_args in mock_ollama.call_args_list:
            prompt_str = call_args[1].get("prompt") or call_args[0][0]
            self.assertNotIn("expected_answer", prompt_str)

    @patch("evaluation.runner.generate_ollama_response")
    @patch("evaluation.runner.generate_gemini_response")
    def test_saving_all_three_result_files(self, mock_gemini, mock_ollama):
        """All three result files (raw_results.json, scores.json, summary.json) must be saved."""
        mock_gemini.return_value = {
            "provider": "gemini",
            "model": "gemini-flash-latest",
            "raw_text": json.dumps(self.test_cases[0]["expected_answer"]),
            "latency_seconds": 0.4,
            "success": True,
            "error": None,
        }
        mock_ollama.return_value = {
            "provider": "ollama",
            "model": "llama3.2:1b",
            "raw_text": json.dumps(self.test_cases[0]["expected_answer"]),
            "latency_seconds": 0.2,
            "success": True,
            "error": None,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir)
            summary = run_benchmark(
                dataset_path=self.dataset_path,
                output_dir=temp_output,
                providers=["gemini", "ollama"],
            )

            run_dir = Path(summary["run_dir"])
            self.assertTrue((run_dir / "raw_results.json").exists())
            self.assertTrue((run_dir / "scores.json").exists())
            self.assertTrue((run_dir / "summary.json").exists())

            # Verify files are valid JSON and contain expected records
            with open(run_dir / "raw_results.json", "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                self.assertEqual(len(raw_data), 20)

            with open(run_dir / "scores.json", "r", encoding="utf-8") as f:
                scores_data = json.load(f)
                self.assertEqual(len(scores_data), 20)

            with open(run_dir / "summary.json", "r", encoding="utf-8") as f:
                sum_data = json.load(f)
                self.assertIn("providers", sum_data)
                self.assertIn("gemini", sum_data["providers"])
                self.assertIn("ollama", sum_data["providers"])

    @patch("evaluation.runner.generate_ollama_response")
    @patch("evaluation.runner.generate_gemini_response")
    def test_handling_provider_failures_without_stopping_run(
        self, mock_gemini, mock_ollama
    ):
        """Provider failures (e.g. Gemini quota/network error) must not halt the run."""
        # Gemini always fails
        mock_gemini.return_value = {
            "provider": "gemini",
            "model": "gemini-flash-latest",
            "raw_text": None,
            "latency_seconds": 0.1,
            "success": False,
            "error": "Gemini API quota exceeded or service unavailable",
        }
        # Ollama succeeds
        mock_ollama.return_value = {
            "provider": "ollama",
            "model": "llama3.2:1b",
            "raw_text": json.dumps(self.test_cases[0]["expected_answer"]),
            "latency_seconds": 0.2,
            "success": True,
            "error": None,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run_benchmark(
                dataset_path=self.dataset_path,
                output_dir=Path(temp_dir),
                providers=["gemini", "ollama"],
            )

            self.assertEqual(summary["total_evaluations_attempted"], 20)

            gemini_sum = summary["providers"]["gemini"]
            self.assertEqual(gemini_sum["successful_responses"], 0)
            self.assertEqual(gemini_sum["failed_responses"], 10)
            # Scores must NOT be invented for failed evaluations
            self.assertIsNone(gemini_sum["average_score"])
            self.assertEqual(len(gemini_sum["failed_evaluations"]), 10)

            ollama_sum = summary["providers"]["ollama"]
            self.assertEqual(ollama_sum["successful_responses"], 10)
            self.assertEqual(ollama_sum["failed_responses"], 0)
            self.assertIsNotNone(ollama_sum["average_score"])

    @patch("evaluation.runner.generate_gemini_response")
    def test_correct_summary_calculations(self, mock_gemini):
        """Verify calculation of averages, accuracies, and false approval metrics."""
        # Mock 8 perfect answers and 2 false approval answers
        def mock_gen(prompt, *args, **kwargs):
            if "PROC-001" in prompt:
                # Deliberate false approval: approve when should HOLD
                return {
                    "provider": "gemini",
                    "model": "gemini-flash-latest",
                    "raw_text": json.dumps({
                        "decision": "APPROVE",
                        "risk_level": "LOW",
                        "discrepancies": [],
                        "evidence": ["Everything looks good"],
                        "reasoning": "Approved",
                        "next_action": "Pay immediately",
                        "payment_allowed": True,
                    }),
                    "latency_seconds": 1.0,
                    "success": True,
                    "error": None,
                }
            # Perfect answer for others
            return {
                "provider": "gemini",
                "model": "gemini-flash-latest",
                "raw_text": json.dumps(self.test_cases[0]["expected_answer"]),
                "latency_seconds": 2.0,
                "success": True,
                "error": None,
            }

        mock_gemini.side_effect = mock_gen

        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run_benchmark(
                dataset_path=self.dataset_path,
                output_dir=Path(temp_dir),
                providers=["gemini"],
            )

            g_sum = summary["providers"]["gemini"]
            self.assertEqual(g_sum["total_cases_attempted"], 10)
            self.assertEqual(g_sum["successful_responses"], 10)
            self.assertEqual(g_sum["failed_responses"], 0)
            self.assertGreater(g_sum["false_approval_count"], 0)
            self.assertGreaterEqual(g_sum["average_latency_seconds"], 1.0)
            self.assertIn("average_f1", g_sum["discrepancy_detection_performance"])

    @patch("evaluation.runner.generate_gemini_response")
    def test_gemini_request_pacing_delay(self, mock_gemini):
        """Runner must apply configurable pacing delay (12s default) between Gemini requests."""
        mock_gemini.return_value = {
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "raw_text": json.dumps(self.test_cases[0]["expected_answer"]),
            "latency_seconds": 0.5,
            "success": True,
            "error": None,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            run_benchmark(
                dataset_path=self.dataset_path,
                output_dir=Path(temp_dir),
                providers=["gemini"],
                gemini_delay_seconds=12.0,
            )

            # Exactly 9 delays between 10 requests
            pacing_calls = [call for call in self.mock_sleep.call_args_list if call[0] == (12.0,)]
            self.assertEqual(len(pacing_calls), 9)

    @patch("evaluation.runner.generate_ollama_response")
    def test_ollama_not_delayed_by_pacing(self, mock_ollama):
        """Pacing delay must NOT be applied to Ollama requests."""
        mock_ollama.return_value = {
            "provider": "ollama",
            "model": "llama3.2:1b",
            "raw_text": json.dumps(self.test_cases[0]["expected_answer"]),
            "latency_seconds": 0.5,
            "success": True,
            "error": None,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            run_benchmark(
                dataset_path=self.dataset_path,
                output_dir=Path(temp_dir),
                providers=["ollama"],
                gemini_delay_seconds=12.0,
            )

            # mock_sleep must never be called for Ollama
            pacing_calls = [call for call in self.mock_sleep.call_args_list if call[0] == (12.0,)]
            self.assertEqual(len(pacing_calls), 0)


if __name__ == "__main__":
    unittest.main()

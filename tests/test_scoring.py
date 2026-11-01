"""
Unit tests for ProcureBench Deterministic Scoring Engine.
Tests all criteria, weights, edge cases, and error handling.
"""

import json
from pathlib import Path
import sys
import unittest

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.scoring import (
    score_response,
    score_discrepancies,
    parse_response,
    validate_response,
    WEIGHT_DECISION,
    WEIGHT_RISK_LEVEL,
    WEIGHT_DISCREPANCIES,
    WEIGHT_EVIDENCE,
    WEIGHT_NEXT_ACTION,
    WEIGHT_PAYMENT_ALLOWED,
)


class TestProcureBenchScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dataset_path = PROJECT_ROOT / "dataset" / "test_cases.json"
        with open(dataset_path, "r", encoding="utf-8") as f:
            cls.test_cases = json.load(f)
        # Use PROC-001 as reference benchmark case
        cls.case_001 = cls.test_cases[0]
        cls.expected_001 = cls.case_001["expected_answer"]

    def test_completely_correct_response(self):
        """A perfect response matching expected answer must score exactly 100.0 and be valid."""
        response = dict(self.expected_001)
        result = score_response(response, self.expected_001)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["validation_errors"], [])
        self.assertEqual(result["scores"]["decision"], WEIGHT_DECISION)
        self.assertEqual(result["scores"]["risk_level"], WEIGHT_RISK_LEVEL)
        self.assertEqual(result["scores"]["discrepancies"], WEIGHT_DISCREPANCIES)
        self.assertEqual(result["scores"]["evidence"], WEIGHT_EVIDENCE)
        self.assertEqual(result["scores"]["next_action"], WEIGHT_NEXT_ACTION)
        self.assertEqual(result["scores"]["payment_allowed"], WEIGHT_PAYMENT_ALLOWED)
        self.assertEqual(result["total_score"], 100.0)

    def test_completely_correct_json_string(self):
        """A JSON string format response matching expected answer must parse and score 100.0."""
        response_json = json.dumps(self.expected_001)
        result = score_response(response_json, self.expected_001)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["total_score"], 100.0)

    def test_incorrect_decision(self):
        """An incorrect decision must receive 0 for decision score."""
        response = dict(self.expected_001)
        response["decision"] = "APPROVE"  # Expected is HOLD

        result = score_response(response, self.expected_001)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["scores"]["decision"], 0.0)
        self.assertLessEqual(result["total_score"], 100.0 - WEIGHT_DECISION)
        self.assertEqual(result["total_score"], 65.0)

    def test_missing_discrepancy_codes(self):
        """Missing expected discrepancy codes should lower recall and discrepancy score."""
        # PROC-010 has 3 expected discrepancies
        case_010 = next(c for c in self.test_cases if c["case_id"] == "PROC-010")
        expected_010 = case_010["expected_answer"]

        response = dict(expected_010)
        # Supply only 1 of the 3 discrepancies
        response["discrepancies"] = ["DISC-QTY-MISMATCH"]

        result = score_response(response, expected_010)

        self.assertTrue(result["is_valid"])
        self.assertAlmostEqual(result["metrics"]["discrepancy_precision"], 1.0, places=3)
        self.assertAlmostEqual(result["metrics"]["discrepancy_recall"], 1.0 / 3.0, places=3)
        # F1 = 2 * (1 * 1/3) / (1 + 1/3) = 0.5; score = 0.5 * 25 = 12.5
        self.assertEqual(result["scores"]["discrepancies"], 12.5)
        self.assertLess(result["total_score"], 100.0)

    def test_extra_incorrect_discrepancy_codes(self):
        """Extra incorrect discrepancy codes should lower precision and discrepancy score."""
        response = dict(self.expected_001)
        # Expected is ['DISC-QTY-MISMATCH'], add extra wrong code
        response["discrepancies"] = ["DISC-QTY-MISMATCH", "DISC-FAKE-CODE"]

        result = score_response(response, self.expected_001)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["metrics"]["discrepancy_precision"], 0.5)
        self.assertEqual(result["metrics"]["discrepancy_recall"], 1.0)
        # F1 = 2 * (0.5 * 1.0) / 1.5 = 2/3 = 0.6667; score = round(25 * 2/3, 2) = 16.67
        self.assertEqual(result["scores"]["discrepancies"], 16.67)
        self.assertLess(result["total_score"], 100.0)

    def test_both_discrepancies_empty_awards_zero(self):
        """Rule: Award zero for discrepancy criterion if both lists are empty."""
        p, r, f1, score = score_discrepancies([], [])
        self.assertEqual(score, 0.0)
        self.assertEqual(f1, 0.0)

    def test_invalid_json(self):
        """Invalid JSON should be handled gracefully without crashing, resulting in 0 score and invalid status."""
        malformed_inputs = [
            "{decision: 'HOLD', invalid_json",
            "This is just plain text, not JSON at all.",
            "",
            None,
            12345,
            [],
        ]

        for malformed in malformed_inputs:
            result = score_response(malformed, self.expected_001)
            self.assertFalse(result["is_valid"])
            self.assertGreater(len(result["validation_errors"]), 0)
            self.assertEqual(result["total_score"], 0.0)

    def test_missing_required_fields(self):
        """Missing required fields must mark is_valid as False and report missing fields."""
        incomplete_response = {
            "decision": "HOLD",
            "risk_level": "HIGH",
            # missing: discrepancies, evidence, reasoning, next_action, payment_allowed
        }

        result = score_response(incomplete_response, self.expected_001)

        self.assertFalse(result["is_valid"])
        error_text = " ".join(result["validation_errors"])
        self.assertIn("discrepancies", error_text)
        self.assertIn("evidence", error_text)
        self.assertIn("payment_allowed", error_text)
        # Still scores the valid fields that were present
        self.assertEqual(result["scores"]["decision"], WEIGHT_DECISION)
        self.assertEqual(result["scores"]["risk_level"], WEIGHT_RISK_LEVEL)

    def test_invalid_field_values(self):
        """Invalid domain values for decision and risk level must be detected."""
        response = dict(self.expected_001)
        response["decision"] = "UNKNOWN_DECISION"
        response["risk_level"] = "VERY_HIGH"
        response["payment_allowed"] = "not_a_boolean"

        result = score_response(response, self.expected_001)
        self.assertFalse(result["is_valid"])
        error_text = " ".join(result["validation_errors"])
        self.assertIn("Invalid decision", error_text)
        self.assertIn("Invalid risk_level", error_text)
        self.assertIn("payment_allowed", error_text)

    def test_maximum_score_is_100(self):
        """Total score must never exceed 100.0."""
        response = dict(self.expected_001)
        result = score_response(response, self.expected_001)
        self.assertLessEqual(result["total_score"], 100.0)

    def test_score_never_goes_below_zero(self):
        """Total score must never be negative, even on completely wrong/empty responses."""
        completely_wrong_response = {
            "decision": "REJECT",
            "risk_level": "LOW",
            "discrepancies": ["DISC-NONEXISTENT"],
            "evidence": ["Completely irrelevant content"],
            "reasoning": "Wrong reason",
            "next_action": "Irrelevant action",
            "payment_allowed": True,
        }

        result = score_response(completely_wrong_response, self.expected_001)
        self.assertGreaterEqual(result["total_score"], 0.0)
        self.assertEqual(result["total_score"], 0.0)

    def test_markdown_codeblock_json(self):
        """Handles responses wrapped in markdown codeblocks (```json ... ```) gracefully."""
        markdown_json = f"```json\n{json.dumps(self.expected_001)}\n```"
        result = score_response(markdown_json, self.expected_001)
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["total_score"], 100.0)


if __name__ == "__main__":
    unittest.main()

"""
ProcureBench Deterministic Scoring Engine
Evaluates LLM responses against expected procurement benchmark answers.
"""

from collections import Counter
import json
import re
from typing import Any, Union

# Criterion weights (Total = 100)
WEIGHT_DECISION = 35.0
WEIGHT_RISK_LEVEL = 10.0
WEIGHT_DISCREPANCIES = 25.0
WEIGHT_EVIDENCE = 10.0
WEIGHT_NEXT_ACTION = 10.0
WEIGHT_PAYMENT_ALLOWED = 10.0

MAX_SCORE = 100.0
MIN_SCORE = 0.0

REQUIRED_FIELDS = [
    "decision",
    "risk_level",
    "discrepancies",
    "evidence",
    "reasoning",
    "next_action",
    "payment_allowed",
]

ALLOWED_DECISIONS = {"APPROVE", "HOLD", "REJECT", "ESCALATE"}
ALLOWED_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}


def normalize_text(text: Any) -> list[str]:
    """Tokenizes and normalizes text for deterministic lexical comparison."""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s]", " ", str(text).lower())
    return [w for w in cleaned.split() if w]


def compute_token_f1(predicted_text: Any, target_text: Any) -> tuple[float, float, float]:
    """
    Computes token-level precision, recall, and F1 between two texts.
    Returns (precision, recall, f1).
    """
    pred_tokens = normalize_text(predicted_text)
    target_tokens = normalize_text(target_text)

    if not pred_tokens or not target_tokens:
        if not pred_tokens and not target_tokens:
            return 1.0, 1.0, 1.0
        return 0.0, 0.0, 0.0

    pred_counter = Counter(pred_tokens)
    target_counter = Counter(target_tokens)

    common_tokens = pred_counter & target_counter
    tp = sum(common_tokens.values())

    precision = tp / len(pred_tokens) if pred_tokens else 0.0
    recall = tp / len(target_tokens) if target_tokens else 0.0

    if precision + recall > 0.0:
        f1 = (2.0 * precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    return precision, recall, f1


def parse_response(raw_response: Union[str, dict, Any]) -> tuple[dict[str, Any], list[str]]:
    """
    Safely parses a response into a dictionary.
    Returns (parsed_dict, error_messages).
    """
    if isinstance(raw_response, dict):
        return raw_response, []

    if isinstance(raw_response, str):
        trimmed = raw_response.strip()
        # Handle possible markdown json code blocks ```json ... ```
        if trimmed.startswith("```"):
            lines = trimmed.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            trimmed = "\n".join(lines).strip()

        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict):
                return parsed, []
            return {}, [f"Response JSON must be an object/dict, got {type(parsed).__name__}"]
        except Exception as e:
            return {}, [f"Invalid JSON: {str(e)}"]

    return {}, [f"Response must be a JSON string or dict, got {type(raw_response).__name__}"]


def validate_response(response: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validates required fields and allowed value domains.
    Returns (is_valid, validation_errors).
    """
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in response:
            errors.append(f"Missing required field: '{field}'")

    if "decision" in response:
        dec = str(response["decision"]).strip().upper()
        if dec not in ALLOWED_DECISIONS:
            errors.append(
                f"Invalid decision '{response['decision']}'; allowed: {sorted(ALLOWED_DECISIONS)}"
            )

    if "risk_level" in response:
        risk = str(response["risk_level"]).strip().upper()
        if risk not in ALLOWED_RISK_LEVELS:
            errors.append(
                f"Invalid risk_level '{response['risk_level']}'; allowed: {sorted(ALLOWED_RISK_LEVELS)}"
            )

    if "discrepancies" in response and not isinstance(response["discrepancies"], list):
        errors.append(
            f"'discrepancies' must be a list, got {type(response['discrepancies']).__name__}"
        )

    if "payment_allowed" in response and not isinstance(response["payment_allowed"], bool):
        errors.append(
            f"'payment_allowed' must be a boolean, got {type(response['payment_allowed']).__name__}"
        )

    return (len(errors) == 0, errors)


def score_discrepancies(
    predicted_discrepancies: Any, expected_discrepancies: Any
) -> tuple[float, float, float, float]:
    """
    Evaluates discrepancy codes using precision, recall, and F1.
    Rule: Award zero if both lists are empty.
    Returns (precision, recall, f1, score).
    """
    if not isinstance(predicted_discrepancies, list):
        pred_list = []
    else:
        pred_list = [str(d).strip().upper() for d in predicted_discrepancies if d is not None]

    if not isinstance(expected_discrepancies, list):
        exp_list = []
    else:
        exp_list = [str(d).strip().upper() for d in expected_discrepancies if d is not None]

    pred_set = set(pred_list)
    exp_set = set(exp_list)

    # Specific rule: Award zero if both lists are empty
    if not pred_set and not exp_set:
        return 0.0, 0.0, 0.0, 0.0

    if not pred_set or not exp_set:
        return 0.0, 0.0, 0.0, 0.0

    tp = len(pred_set & exp_set)
    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(exp_set) if exp_set else 0.0

    if precision + recall > 0.0:
        f1 = (2.0 * precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    score = round(f1 * WEIGHT_DISCREPANCIES, 2)
    return precision, recall, f1, score


def score_response(
    response: Union[str, dict[str, Any]], expected: dict[str, Any]
) -> dict[str, Any]:
    """
    Evaluates a model response against expected answer.
    Handles malformed responses, invalid JSON, and missing fields gracefully without crashing.
    """
    # If a full case dictionary was passed instead of expected_answer, extract expected_answer
    if "expected_answer" in expected and isinstance(expected["expected_answer"], dict):
        expected_ans = expected["expected_answer"]
    else:
        expected_ans = expected

    parsed_response, parse_errors = parse_response(response)

    if parse_errors:
        return {
            "is_valid": False,
            "validation_errors": parse_errors,
            "scores": {
                "decision": 0.0,
                "risk_level": 0.0,
                "discrepancies": 0.0,
                "evidence": 0.0,
                "next_action": 0.0,
                "payment_allowed": 0.0,
            },
            "metrics": {
                "discrepancy_precision": 0.0,
                "discrepancy_recall": 0.0,
                "discrepancy_f1": 0.0,
                "evidence_f1": 0.0,
                "next_action_f1": 0.0,
            },
            "total_score": 0.0,
        }

    is_valid, validation_errors = validate_response(parsed_response)

    # 1. Decision Correctness (35 pts)
    decision_score = 0.0
    if "decision" in parsed_response:
        pred_decision = str(parsed_response["decision"]).strip().upper()
        exp_decision = str(expected_ans.get("decision", "")).strip().upper()
        if pred_decision == exp_decision:
            decision_score = WEIGHT_DECISION

    # 2. Risk Level Correctness (10 pts)
    risk_score = 0.0
    if "risk_level" in parsed_response:
        pred_risk = str(parsed_response["risk_level"]).strip().upper()
        exp_risk = str(expected_ans.get("risk_level", "")).strip().upper()
        if pred_risk == exp_risk:
            risk_score = WEIGHT_RISK_LEVEL

    # 3. Discrepancy Identification (25 pts)
    p_disc, r_disc, f1_disc, disc_score = score_discrepancies(
        parsed_response.get("discrepancies"), expected_ans.get("discrepancies")
    )

    # 4. Evidence Matching (10 pts)
    exp_evidence = expected_ans.get("evidence", [])
    if isinstance(exp_evidence, list):
        target_ev_text = " ".join(str(e) for e in exp_evidence)
    else:
        target_ev_text = str(exp_evidence)

    pred_evidence = parsed_response.get("evidence", [])
    if isinstance(pred_evidence, list):
        pred_ev_text = " ".join(str(e) for e in pred_evidence)
    else:
        pred_ev_text = str(pred_evidence)

    _, _, ev_f1 = compute_token_f1(pred_ev_text, target_ev_text)
    evidence_score = round(ev_f1 * WEIGHT_EVIDENCE, 2)

    # 5. Next Action Matching (10 pts)
    target_action = str(expected_ans.get("next_action", ""))
    pred_action = str(parsed_response.get("next_action", ""))
    _, _, action_f1 = compute_token_f1(pred_action, target_action)
    next_action_score = round(action_f1 * WEIGHT_NEXT_ACTION, 2)

    # 6. Payment Permission Correctness (10 pts)
    payment_score = 0.0
    if "payment_allowed" in parsed_response and isinstance(
        parsed_response["payment_allowed"], bool
    ):
        pred_payment = parsed_response["payment_allowed"]
        exp_payment = expected_ans.get("payment_allowed")
        if pred_payment == exp_payment:
            payment_score = WEIGHT_PAYMENT_ALLOWED

    # Calculate total and clamp
    raw_total = (
        decision_score
        + risk_score
        + disc_score
        + evidence_score
        + next_action_score
        + payment_score
    )
    total_score = max(MIN_SCORE, min(MAX_SCORE, round(raw_total, 2)))

    return {
        "is_valid": is_valid,
        "validation_errors": validation_errors,
        "scores": {
            "decision": decision_score,
            "risk_level": risk_score,
            "discrepancies": disc_score,
            "evidence": evidence_score,
            "next_action": next_action_score,
            "payment_allowed": payment_score,
        },
        "metrics": {
            "discrepancy_precision": round(p_disc, 4),
            "discrepancy_recall": round(r_disc, 4),
            "discrepancy_f1": round(f1_disc, 4),
            "evidence_f1": round(ev_f1, 4),
            "next_action_f1": round(action_f1, 4),
        },
        "total_score": total_score,
    }


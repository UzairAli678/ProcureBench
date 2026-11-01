"""
ProcureBench Benchmark Runner
Executes benchmark evaluations across multiple LLMs using standardized test cases and scoring.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Optional

from evaluation.scoring import score_response
from models.llm_clients import (
    build_benchmark_prompt,
    generate_gemini_response,
    generate_ollama_response,
)

# Default paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_PATH = PROJECT_ROOT / "dataset" / "test_cases.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "runs"


def load_test_cases(dataset_path: Path) -> list[dict[str, Any]]:
    """Loads benchmark test cases from JSON dataset."""
    if not dataset_path.exists():
        raise FileNotFoundError(f"Benchmark dataset not found at: {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    if not isinstance(cases, list) or len(cases) == 0:
        raise ValueError(f"Expected non-empty list of test cases in {dataset_path}")

    return cases


def calculate_provider_summary(
    provider_name: str,
    raw_results: list[dict[str, Any]],
    score_results: list[dict[str, Any]],
    test_cases_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculates aggregate metrics for a single provider.
    Never invents scores for failed evaluations; reports failures separately.
    """
    total_attempted = len(raw_results)
    successful_raw = [r for r in raw_results if r["success"] and r["raw_response"]]
    successful_scores = [s for s in score_results if s["status"] == "EVALUATED" and s["scores"] is not None]

    failed_evals = [
        {
            "case_id": r["case_id"],
            "error": r["error"] or "Unknown error",
        }
        for r in raw_results
        if not r["success"]
    ]

    # Model name from first result or default
    model_name = raw_results[0]["model"] if raw_results else "unknown"

    # Average latency across all attempted runs
    total_latency = sum(r["latency_seconds"] for r in raw_results)
    avg_latency = round(total_latency / total_attempted, 3) if total_attempted > 0 else 0.0

    # Scores and accuracies computed ONLY on successful evaluations
    num_successful = len(successful_scores)
    if num_successful > 0:
        avg_score = round(sum(s["total_score"] for s in successful_scores) / num_successful, 2)

        # Decision correctness: max decision score is 35.0
        correct_decisions = sum(1 for s in successful_scores if s["scores"]["decision"] == 35.0)
        decision_accuracy = round(correct_decisions / num_successful, 4)

        # Risk level correctness: max risk score is 10.0
        correct_risks = sum(1 for s in successful_scores if s["scores"]["risk_level"] == 10.0)
        risk_level_accuracy = round(correct_risks / num_successful, 4)

        # Critical discrepancy detection metrics
        avg_precision = round(
            sum(s["metrics"]["discrepancy_precision"] for s in successful_scores) / num_successful,
            4,
        )
        avg_recall = round(
            sum(s["metrics"]["discrepancy_recall"] for s in successful_scores) / num_successful,
            4,
        )
        avg_f1 = round(
            sum(s["metrics"]["discrepancy_f1"] for s in successful_scores) / num_successful,
            4,
        )

        # False approval count: model approved or allowed payment when expected payment_allowed was False
        false_approvals = 0
        for s in successful_scores:
            cid = s["case_id"]
            expected = test_cases_by_id[cid]["expected_answer"]
            exp_pay_allowed = expected.get("payment_allowed", False)

            # Match raw response
            matched_raw = next((r for r in raw_results if r["case_id"] == cid), None)
            if matched_raw and matched_raw["raw_response"]:
                try:
                    parsed = json.loads(matched_raw["raw_response"])
                    mod_decision = str(parsed.get("decision", "")).strip().upper()
                    mod_pay_allowed = parsed.get("payment_allowed")
                    if not exp_pay_allowed and (mod_decision == "APPROVE" or mod_pay_allowed is True):
                        false_approvals += 1
                except Exception:
                    pass
    else:
        avg_score = None
        decision_accuracy = 0.0
        risk_level_accuracy = 0.0
        avg_precision = 0.0
        avg_recall = 0.0
        avg_f1 = 0.0
        false_approvals = 0

    return {
        "provider": provider_name,
        "model": model_name,
        "total_cases_attempted": total_attempted,
        "successful_responses": num_successful,
        "failed_responses": len(failed_evals),
        "average_score": avg_score,
        "average_latency_seconds": avg_latency,
        "decision_accuracy": decision_accuracy,
        "risk_level_accuracy": risk_level_accuracy,
        "false_approval_count": false_approvals,
        "discrepancy_detection_performance": {
            "average_precision": avg_precision,
            "average_recall": avg_recall,
            "average_f1": avg_f1,
        },
        "failed_evaluations": failed_evals,
    }


def run_benchmark(
    dataset_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    providers: Optional[list[str]] = None,
    gemini_model: Optional[str] = None,
    ollama_model: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
) -> dict[str, Any]:
    """
    Executes the benchmark evaluation across all test cases and providers.
    Saves raw_results.json, scores.json, and summary.json under results/runs/run_<timestamp>/.
    """
    resolved_dataset_path = dataset_path or DEFAULT_DATASET_PATH
    resolved_output_dir = output_dir or DEFAULT_OUTPUT_DIR
    resolved_providers = providers or ["gemini", "ollama"]

    test_cases = load_test_cases(resolved_dataset_path)
    test_cases_by_id = {c["case_id"]: c for c in test_cases}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    run_dir = resolved_output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    all_raw_results: list[dict[str, Any]] = []
    all_scores: list[dict[str, Any]] = []

    # Map provider generator functions
    provider_dispatch = {
        "gemini": lambda prompt: generate_gemini_response(
            prompt=prompt,
            model=gemini_model,
            api_key=gemini_api_key,
        ),
        "ollama": lambda prompt: generate_ollama_response(
            prompt=prompt,
            model=ollama_model,
            base_url=ollama_base_url,
        ),
    }

    # Evaluate each provider
    for provider in resolved_providers:
        generator = provider_dispatch.get(provider)
        if not generator:
            continue

        for case in test_cases:
            case_id = case["case_id"]

            # CRITICAL FAIRNESS RULE:
            # build_benchmark_prompt strictly excludes expected_answer
            prompt = build_benchmark_prompt(case)

            # Generate response (catches errors internally and returns structured result)
            try:
                gen_result = generator(prompt)
            except Exception as e:
                gen_result = {
                    "provider": provider,
                    "model": "unknown",
                    "raw_text": None,
                    "latency_seconds": 0.0,
                    "success": False,
                    "error": f"Unhandled client error: {str(e)}",
                }

            # Record raw result
            raw_record = {
                "case_id": case_id,
                "provider": gen_result["provider"],
                "model": gen_result["model"],
                "raw_response": gen_result["raw_text"],
                "latency_seconds": gen_result["latency_seconds"],
                "success": gen_result["success"],
                "error": gen_result["error"],
            }
            all_raw_results.append(raw_record)

            # Score response
            if gen_result["success"] and gen_result["raw_text"]:
                try:
                    score_res = score_response(
                        response=gen_result["raw_text"],
                        expected=case["expected_answer"],
                    )
                    score_record = {
                        "case_id": case_id,
                        "provider": gen_result["provider"],
                        "model": gen_result["model"],
                        "status": "EVALUATED",
                        "is_valid": score_res["is_valid"],
                        "validation_errors": score_res["validation_errors"],
                        "scores": score_res["scores"],
                        "metrics": score_res["metrics"],
                        "total_score": score_res["total_score"],
                    }
                except Exception as e:
                    score_record = {
                        "case_id": case_id,
                        "provider": gen_result["provider"],
                        "model": gen_result["model"],
                        "status": "FAILED",
                        "is_valid": False,
                        "validation_errors": [f"Scoring exception: {str(e)}"],
                        "scores": None,
                        "metrics": None,
                        "total_score": None,
                    }
            else:
                # Failed evaluation: record failure without inventing scores
                score_record = {
                    "case_id": case_id,
                    "provider": gen_result["provider"],
                    "model": gen_result["model"],
                    "status": "FAILED",
                    "is_valid": False,
                    "validation_errors": [gen_result["error"] or "Model generation failed"],
                    "scores": None,
                    "metrics": None,
                    "total_score": None,
                }
            all_scores.append(score_record)

    # Compute provider summaries
    summary_providers = {}
    for provider in resolved_providers:
        prov_raw = [r for r in all_raw_results if r["provider"] == provider]
        prov_scores = [s for s in all_scores if s["provider"] == provider]
        summary_providers[provider] = calculate_provider_summary(
            provider_name=provider,
            raw_results=prov_raw,
            score_results=prov_scores,
            test_cases_by_id=test_cases_by_id,
        )

    summary = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "total_evaluations_attempted": len(all_raw_results),
        "providers": summary_providers,
    }

    # Save output files
    with open(run_dir / "raw_results.json", "w", encoding="utf-8") as f:
        json.dump(all_raw_results, f, indent=2)

    with open(run_dir / "scores.json", "w", encoding="utf-8") as f:
        json.dump(all_scores, f, indent=2)

    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    summary["run_dir"] = str(run_dir)
    return summary


if __name__ == "__main__":
    print("ProcureBench Runner loaded.")


"""
ProcureBench LLM Client Interface
Provides unified, decoupled client integrations for Gemini and Ollama.
"""

import json
import os
import time
from typing import Any, Optional
import urllib.error
import urllib.request

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

GEMINI_DEFAULT_MODEL = "gemini-flash-latest"
OLLAMA_DEFAULT_MODEL = "llama3.2:1b"
OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"

# Standard discrepancy codes defined by ProcureBench
VALID_DISCREPANCY_CODES = [
    "DISC-QTY-MISMATCH",
    "DISC-DUP-INVOICE",
    "DISC-INACTIVE-SUPPLIER",
    "DISC-MISSING-PO",
    "DISC-UNAUTH-APPROVAL",
    "DISC-AMOUNT-MISMATCH",
    "DISC-PARTIAL-RECEIPT",
    "DISC-BANK-MISMATCH",
    "DISC-CURRENCY-MISMATCH",
]


def build_benchmark_prompt(case: dict[str, Any]) -> str:
    """
    Constructs the standardized benchmark evaluation prompt for a test case.

    CRITICAL BENCHMARK FAIRNESS RULE:
    Never include 'expected_answer' or reference scoring data in the prompt.
    Only pass: case_id, title, category, difficulty, scenario, transaction_data, and applicable_policies.
    """
    case_id = case.get("case_id", "UNKNOWN")
    title = case.get("title", "Untitled")
    category = case.get("category", "General")
    difficulty = case.get("difficulty", "Medium")
    scenario = case.get("scenario", "")
    applicable_policies = case.get("applicable_policies", [])
    transaction_data = case.get("transaction_data", {})

    prompt = f"""You are an enterprise procurement compliance evaluator for ProcureBench.
Your task is to analyze the provided procurement scenario, transaction data, and applicable policies to determine compliance and payment authorization.

### Instructions:
1. Act as a rigorous enterprise compliance evaluator.
2. Evaluate all facts in the transaction data against the applicable policies.
3. Base your decision strictly on the provided facts and policies; do not assume or invent missing evidence.
4. Output MUST be a single, valid JSON object matching the exact schema below. Do not wrap with conversational text.

### Allowed Values:
- decision: Must be one of ["APPROVE", "HOLD", "REJECT", "ESCALATE"]
- risk_level: Must be one of ["LOW", "MEDIUM", "HIGH"]
- discrepancies: Array of identified discrepancy codes. You must use ONLY these standard codes if present:
{json.dumps(VALID_DISCREPANCY_CODES, indent=2)}
  If no discrepancies exist, return an empty array [].
- payment_allowed: Boolean (true or false).

### Output Schema:
{{
  "decision": "APPROVE | HOLD | REJECT | ESCALATE",
  "risk_level": "LOW | MEDIUM | HIGH",
  "discrepancies": ["DISC-..."],
  "evidence": ["Factual observations directly extracted from transaction data"],
  "reasoning": "Concise policy-grounded justification for your determination",
  "next_action": "Concrete recommended action for procurement/finance personnel",
  "payment_allowed": true | false
}}

### Benchmark Case:
Case ID: {case_id}
Title: {title}
Category: {category}
Difficulty: {difficulty}
Scenario: {scenario}

Applicable Policies:
{json.dumps(applicable_policies, indent=2)}

Transaction Data:
{json.dumps(transaction_data, indent=2)}
"""
    return prompt.strip()


def generate_gemini_response(
    prompt: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generates a response from Gemini using google-genai.
    Returns raw text and metadata without scoring.
    """
    start_time = time.perf_counter()
    resolved_model = model or os.getenv("GEMINI_MODEL", GEMINI_DEFAULT_MODEL)
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")

    if not resolved_key or not resolved_key.strip():
        latency = round(time.perf_counter() - start_time, 3)
        return {
            "provider": "gemini",
            "model": resolved_model,
            "raw_text": None,
            "latency_seconds": latency,
            "success": False,
            "error": "Missing GEMINI_API_KEY. Set it in your environment or .env file.",
        }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=resolved_key)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = client.models.generate_content(
            model=resolved_model,
            contents=prompt,
            config=config,
        )

        latency = round(time.perf_counter() - start_time, 3)
        raw_text = response.text if response and response.text else None

        if not raw_text or not raw_text.strip():
            return {
                "provider": "gemini",
                "model": resolved_model,
                "raw_text": None,
                "latency_seconds": latency,
                "success": False,
                "error": "Received empty response from Gemini API.",
            }

        return {
            "provider": "gemini",
            "model": resolved_model,
            "raw_text": raw_text.strip(),
            "latency_seconds": latency,
            "success": True,
            "error": None,
        }
    except Exception as e:
        latency = round(time.perf_counter() - start_time, 3)
        # Sanitize error message to prevent accidental key exposure
        safe_error = str(e)
        if resolved_key and resolved_key in safe_error:
            safe_error = safe_error.replace(resolved_key, "[REDACTED_KEY]")
        return {
            "provider": "gemini",
            "model": resolved_model,
            "raw_text": None,
            "latency_seconds": latency,
            "success": False,
            "error": f"Gemini API error: {safe_error}",
        }


def generate_ollama_response(
    prompt: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """
    Generates a response from local Ollama instance using Python standard library HTTP.
    Returns raw text and metadata without scoring.
    """
    start_time = time.perf_counter()
    resolved_model = model or os.getenv("OLLAMA_MODEL", OLLAMA_DEFAULT_MODEL)
    resolved_base_url = (base_url or os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_BASE_URL)).rstrip("/")
    endpoint = f"{resolved_base_url}/api/generate"

    payload = {
        "model": resolved_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    try:
        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=json_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")

        latency = round(time.perf_counter() - start_time, 3)

        if status_code != 200:
            return {
                "provider": "ollama",
                "model": resolved_model,
                "raw_text": None,
                "latency_seconds": latency,
                "success": False,
                "error": f"Ollama HTTP {status_code}: {response_body}",
            }

        parsed = json.loads(response_body)
        raw_text = parsed.get("response", "")

        if not raw_text or not raw_text.strip():
            return {
                "provider": "ollama",
                "model": resolved_model,
                "raw_text": None,
                "latency_seconds": latency,
                "success": False,
                "error": "Received empty response from Ollama.",
            }

        return {
            "provider": "ollama",
            "model": resolved_model,
            "raw_text": raw_text.strip(),
            "latency_seconds": latency,
            "success": True,
            "error": None,
        }

    except urllib.error.URLError as e:
        latency = round(time.perf_counter() - start_time, 3)
        return {
            "provider": "ollama",
            "model": resolved_model,
            "raw_text": None,
            "latency_seconds": latency,
            "success": False,
            "error": f"Ollama connection error (is Ollama running at {resolved_base_url}?): {e.reason}",
        }
    except Exception as e:
        latency = round(time.perf_counter() - start_time, 3)
        return {
            "provider": "ollama",
            "model": resolved_model,
            "raw_text": None,
            "latency_seconds": latency,
            "success": False,
            "error": f"Ollama request error: {str(e)}",
        }


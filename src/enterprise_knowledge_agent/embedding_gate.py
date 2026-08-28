from __future__ import annotations

import re
from typing import Any


COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
ALLOWED_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause"}
METRIC_KEYS = ("case_count", "status_accuracy", "top1_accuracy", "abstention_accuracy", "blocked_request_accuracy")


def assess_embedding_candidate(candidate: dict[str, Any], baseline_metrics: dict[str, float]) -> dict[str, Any]:
    """Gate a proposed local embedding candidate before any dependency install."""
    required = {"repository", "version", "commit", "license", "decision", "code_adopted", "reason"}
    if not isinstance(candidate, dict) or required.difference(candidate):
        raise ValueError("embedding candidate metadata is incomplete")
    if not str(candidate["repository"]).startswith("https://github.com/"):
        raise ValueError("embedding candidate repository must use a GitHub HTTPS URL")
    if not COMMIT_PATTERN.fullmatch(str(candidate["commit"])):
        raise ValueError("embedding candidate commit must be a full SHA")
    if candidate["license"] not in ALLOWED_LICENSES:
        raise ValueError("embedding candidate license is not allowlisted")
    if candidate["decision"] not in {"adopted", "rejected"} or not isinstance(candidate["code_adopted"], bool):
        raise ValueError("embedding candidate decision metadata is invalid")
    if (candidate["decision"] == "adopted") != candidate["code_adopted"]:
        raise ValueError("embedding candidate decision and code_adopted must agree")
    if candidate["decision"] == "rejected":
        return {"status": "screened_not_adopted", "eligible_for_install": False, "reason": str(candidate["reason"]), "external_action_executed": False}
    if candidate.get("model_artifact_available") is not True:
        return {"status": "blocked_missing_model_artifact", "eligible_for_install": False, "reason": "An adopted candidate must provide a reviewed local model artifact before installation.", "external_action_executed": False}
    benchmark = candidate.get("benchmark")
    if not isinstance(benchmark, dict) or any(key not in benchmark for key in METRIC_KEYS):
        return {"status": "blocked_missing_benchmark", "eligible_for_install": False, "reason": "An adopted candidate must be compared on the knowledge-owner-reviewed benchmark.", "external_action_executed": False}
    if benchmark["case_count"] < baseline_metrics["case_count"]:
        return {"status": "blocked_smaller_benchmark", "eligible_for_install": False, "reason": "Candidate benchmark must be at least as large as the lexical baseline.", "external_action_executed": False}
    regressions = [key for key in METRIC_KEYS[1:] if float(benchmark[key]) < float(baseline_metrics[key])]
    if regressions:
        return {"status": "blocked_benchmark_regression", "eligible_for_install": False, "regressions": regressions, "reason": "Candidate must not regress any safety or retrieval metric.", "external_action_executed": False}
    return {"status": "eligible_for_bounded_pilot", "eligible_for_install": True, "reason": "Candidate passed metadata and benchmark gates; installation still requires separate approval.", "external_action_executed": False}

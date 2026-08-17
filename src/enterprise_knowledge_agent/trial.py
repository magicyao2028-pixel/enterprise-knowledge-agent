from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from .agent import KnowledgeAgent
from .corpus import load_documents


FEEDBACK_CLASSES = {"defect", "requirement", "usability", "performance", "safety", "documentation"}
SOURCE_TYPES = {"real", "synthetic"}
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def validate_evidence_index(root: Path, payload: dict[str, Any]) -> list[dict[str, Any]]:
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("Evidence index must contain claims")
    root = root.resolve()
    checked: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict) or not claim.get("claim_id") or not claim.get("statement"):
            raise ValueError("Every evidence claim needs claim_id and statement")
        if claim["claim_id"] in seen_ids:
            raise ValueError(f"Duplicate evidence claim_id: {claim['claim_id']}")
        seen_ids.add(claim["claim_id"])
        artifacts = claim.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError(f"{claim['claim_id']} must link at least one artifact")
        paths: list[str] = []
        for artifact in artifacts:
            relative = str(artifact.get("path", "")) if isinstance(artifact, dict) else ""
            if not isinstance(artifact, dict) or not str(artifact.get("kind", "")).strip():
                raise ValueError(f"{claim['claim_id']} has an untyped artifact")
            target = (root / relative).resolve()
            if not relative or not target.is_relative_to(root) or not target.is_file():
                raise ValueError(f"Missing or unsafe evidence path: {relative}")
            paths.append(relative)
        checked.append({"claim_id": claim["claim_id"], "artifact_paths": paths, "passed": True})
    return checked


def validate_external_intake(payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        date.fromisoformat(str(payload["reviewed_on"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("External intake reviewed_on must be an ISO-8601 date") from exc
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("External intake must contain screened candidates")
    checked: list[dict[str, Any]] = []
    for candidate in candidates:
        required = {"repository", "version", "commit", "license", "decision", "reason"}
        if not isinstance(candidate, dict) or required.difference(candidate):
            raise ValueError("External candidate metadata is incomplete")
        if any(not str(candidate[key]).strip() for key in required):
            raise ValueError("External candidate metadata must not be blank")
        if not str(candidate["repository"]).startswith("https://github.com/"):
            raise ValueError("External repository must use a GitHub HTTPS URL")
        if not COMMIT_PATTERN.fullmatch(str(candidate["commit"])):
            raise ValueError("External candidate commit must be a full SHA")
        if candidate["decision"] not in {"adopted", "rejected"}:
            raise ValueError("External candidate decision must be adopted or rejected")
        if not isinstance(candidate.get("code_adopted"), bool):
            raise ValueError("External candidate code_adopted must be boolean")
        if (candidate["decision"] == "adopted") != candidate["code_adopted"]:
            raise ValueError("External decision and code_adopted must agree")
        checked.append({"repository": candidate["repository"], "decision": candidate["decision"], "passed": True})
    return checked


def validate_feedback(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "feedback_id", "source_type", "recorded_on", "classification", "summary", "reproduction",
        "decision", "acceptance_test", "implementation", "release_result",
    }
    if required.difference(payload):
        raise ValueError("Feedback record is incomplete")
    if any(not str(payload[key]).strip() for key in required):
        raise ValueError("Feedback fields must not be blank")
    try:
        date.fromisoformat(str(payload["recorded_on"]))
    except ValueError as exc:
        raise ValueError("Feedback recorded_on must be an ISO-8601 date") from exc
    if payload["source_type"] not in SOURCE_TYPES:
        raise ValueError("Feedback source_type must be real or synthetic")
    if payload["classification"] not in FEEDBACK_CLASSES:
        raise ValueError("Feedback classification is unsupported")
    if payload["decision"] != "accepted":
        raise ValueError("Trial feedback case must record an accepted decision")
    for key in ("acceptance_test", "implementation"):
        target = (root.resolve() / str(payload[key])).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            raise ValueError(f"Feedback {key} path is missing or unsafe")
    return {"feedback_id": payload["feedback_id"], "source_type": payload["source_type"], "passed": True}


def run_trial(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = load_json_object(root / "evidence" / "evidence_index.json")
    external = load_json_object(root / "evidence" / "external_intake.json")
    feedback = load_json_object(root / "evidence" / "feedback_case.json")
    evidence_checks = validate_evidence_index(root, manifest)
    external_checks = validate_external_intake(external)
    feedback_check = validate_feedback(root, feedback)

    sample_path = (root / str(manifest["trial"]["sample_input"])).resolve()
    if not sample_path.is_relative_to(root) or not sample_path.is_file():
        raise ValueError("Trial sample input is missing or unsafe")
    documents = load_documents(sample_path)
    agent = KnowledgeAgent(documents)
    core = agent.ask(
        manifest["trial"]["question"],
        as_of_date=manifest["trial"]["as_of_date"],
    )
    expected = manifest["trial"]["expected"]
    core_passed = (
        core["status"] == expected["status"]
        and core["citations"]
        and core["citations"][0]["document_id"] == expected["top_document_id"]
        and expected["answer_contains"] in core["answer"]
    )

    no_evidence = agent.ask("What is the office parking policy?", as_of_date=manifest["trial"]["as_of_date"])
    abstention_check = {
        "passed": no_evidence["status"] == "no_evidence" and no_evidence["citations"] == [] and no_evidence["needs_human_review"],
        "status": no_evidence["status"],
    }
    feedback_runtime = agent.ask(feedback["reproduction"], as_of_date=manifest["trial"]["as_of_date"])
    feedback_regression = {
        **feedback_check,
        "passed": feedback_check["passed"] and feedback_runtime["status"] == "blocked" and feedback_runtime["citations"] == [],
        "status": feedback_runtime["status"],
        "citations": feedback_runtime["citations"],
    }

    all_checks = [
        core_passed,
        abstention_check["passed"],
        feedback_regression["passed"],
        all(item["passed"] for item in evidence_checks),
        all(item["passed"] for item in external_checks),
    ]
    return {
        "schema_version": "1.0",
        "trial_id": manifest["trial"]["trial_id"],
        "source_data": "synthetic",
        "overall_passed": all(all_checks),
        "core_flow": {
            "passed": core_passed,
            "status": core["status"],
            "top_document_id": core["citations"][0]["document_id"] if core["citations"] else None,
            "citation_count": len(core["citations"]),
        },
        "failure_path": abstention_check,
        "feedback_regression": feedback_regression,
        "external_intake": external_checks,
        "evidence_index": evidence_checks,
        "boundaries": manifest["boundaries"],
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Trial Readiness Report",
        "",
        "> Synthetic, offline verification. This is not evidence of production adoption or enterprise accuracy.",
        "",
        f"- Overall: **{'PASS' if report['overall_passed'] else 'FAIL'}**",
        f"- Citation-first answer: {'PASS' if report['core_flow']['passed'] else 'FAIL'}",
        f"- Missing-evidence abstention: {'PASS' if report['failure_path']['passed'] else 'FAIL'}",
        f"- Punctuated-secret regression: {'PASS' if report['feedback_regression']['passed'] else 'FAIL'}",
        f"- Evidence claims checked: {len(report['evidence_index'])}",
        f"- External candidates screened: {len(report['external_intake'])}",
        "",
        "## Pilot boundary",
        "",
        *[f"- {item}" for item in report["boundaries"]],
        "",
    ])


def write_trial_report(root: Path, json_output: Path, markdown_output: Path) -> dict[str, Any]:
    report = run_trial(root)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_output.write_text(render_markdown(report), encoding="utf-8")
    return report

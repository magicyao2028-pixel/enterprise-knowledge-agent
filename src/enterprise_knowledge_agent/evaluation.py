from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent import KnowledgeAgent
from .corpus import load_documents


def load_query_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Evaluation query set must be a non-empty JSON array")
    identifiers: set[str] = set()
    for case in payload:
        if not isinstance(case, dict):
            raise ValueError("Each evaluation case must be an object")
        missing = {"case_id", "query", "expected_status"}.difference(case)
        if missing:
            raise ValueError(f"Evaluation case is missing: {', '.join(sorted(missing))}")
        if case["case_id"] in identifiers:
            raise ValueError("case_id values must be unique")
        identifiers.add(case["case_id"])
        if case["expected_status"] == "answered" and not case.get("expected_document_id"):
            raise ValueError(f"{case['case_id']} requires expected_document_id")
    return payload


def evaluate_queries(
    corpus_path: Path,
    query_path: Path,
) -> dict[str, Any]:
    agent = KnowledgeAgent(load_documents(corpus_path))
    cases = load_query_cases(query_path)
    results: list[dict[str, Any]] = []
    status_correct = 0
    answerable_total = 0
    top1_correct = 0
    top3_correct = 0
    reciprocal_rank_total = 0.0
    no_evidence_total = 0
    no_evidence_correct = 0
    blocked_total = 0
    blocked_correct = 0

    for case in cases:
        response = agent.ask(case["query"], as_of_date="2026-08-14")
        expected_status = case["expected_status"]
        actual_status = str(response["status"])
        status_matches = actual_status == expected_status
        status_correct += int(status_matches)
        retrieved_ids = [str(item["document_id"]) for item in response.get("retrieved", [])]
        expected_document = case.get("expected_document_id")
        rank = None

        if expected_status == "answered":
            answerable_total += 1
            if expected_document in retrieved_ids:
                rank = retrieved_ids.index(expected_document) + 1
                reciprocal_rank_total += 1 / rank
            top1_correct += int(rank == 1)
            top3_correct += int(rank is not None and rank <= 3)
        elif expected_status == "no_evidence":
            no_evidence_total += 1
            no_evidence_correct += int(actual_status == "no_evidence")
        elif expected_status == "blocked":
            blocked_total += 1
            blocked_correct += int(actual_status == "blocked")

        passed = status_matches and (expected_status != "answered" or rank == 1)
        results.append(
            {
                "case_id": case["case_id"],
                "query": case["query"],
                "expected_status": expected_status,
                "actual_status": actual_status,
                "expected_document_id": expected_document,
                "retrieved_document_ids": retrieved_ids,
                "expected_document_rank": rank,
                "passed": passed,
            }
        )

    passed_cases = sum(1 for item in results if item["passed"])
    return {
        "fixture_type": "synthetic reviewed query set",
        "as_of_date": "2026-08-14",
        "summary": {
            "case_count": len(results),
            "passed_cases": passed_cases,
            "case_pass_rate": round(passed_cases / len(results), 4),
            "status_accuracy": round(status_correct / len(results), 4),
            "answerable_queries": answerable_total,
            "top1_accuracy": round(top1_correct / answerable_total, 4) if answerable_total else 1.0,
            "top3_recall": round(top3_correct / answerable_total, 4) if answerable_total else 1.0,
            "mean_reciprocal_rank": round(reciprocal_rank_total / answerable_total, 4) if answerable_total else 1.0,
            "abstention_accuracy": round(no_evidence_correct / no_evidence_total, 4) if no_evidence_total else 1.0,
            "blocked_request_accuracy": round(blocked_correct / blocked_total, 4) if blocked_total else 1.0,
        },
        "cases": results,
        "interpretation": [
            "The query set and corpus are synthetic and intentionally small.",
            "Scores are regression evidence for this fixture, not production retrieval accuracy.",
            "A private, knowledge-owner-reviewed dataset is required before business claims.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Retrieval Evaluation Baseline",
        "",
        "> Synthetic reviewed query set. Results are regression evidence, not production accuracy claims.",
        "",
        "## Summary",
        "",
        "| Metric | Result |",
        "| --- | --- |",
        f"| Cases passed | {summary['passed_cases']}/{summary['case_count']} |",
        f"| Status accuracy | {summary['status_accuracy']:.0%} |",
        f"| Top-1 document accuracy | {summary['top1_accuracy']:.0%} |",
        f"| Top-3 document recall | {summary['top3_recall']:.0%} |",
        f"| Mean reciprocal rank | {summary['mean_reciprocal_rank']:.3f} |",
        f"| Abstention accuracy | {summary['abstention_accuracy']:.0%} |",
        f"| Blocked-request accuracy | {summary['blocked_request_accuracy']:.0%} |",
        "",
        "## Cases",
        "",
        "| Case | Expected | Actual | Expected source rank | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        rank = case["expected_document_rank"] if case["expected_document_rank"] is not None else "—"
        lines.append(
            f"| `{case['case_id']}` | {case['expected_status']} | {case['actual_status']} | {rank} | "
            f"{'PASS' if case['passed'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "- The corpus contains four synthetic documents and the questions were reviewed against those documents.",
            "- A perfect fixture score can reveal regressions but cannot estimate production performance.",
            "- Real deployment requires permission-aware retrieval, larger private test sets and knowledge-owner review.",
            "",
        ]
    )
    return "\n".join(lines)


def write_evaluation_report(
    corpus_path: Path,
    query_path: Path,
    json_output: Path,
    markdown_output: Path,
) -> dict[str, Any]:
    report = evaluate_queries(corpus_path, query_path)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_output.write_text(render_markdown(report), encoding="utf-8")
    return report

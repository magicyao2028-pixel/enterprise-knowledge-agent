from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any


_DECISIONS = {"renew", "escalate", "defer"}


def summarize_owner_review_history(queue: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize synthetic owner decisions without editing documents or retrieval state."""
    if not isinstance(queue, dict) or queue.get("review_only") is not True:
        raise ValueError("Owner review history requires a review-only queue")
    if queue.get("evidence_mutated") is not False or queue.get("external_action_executed") is not False:
        raise ValueError("Owner review queue must remain non-writing")
    items = queue.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Owner review queue must contain items")
    queue_documents = {str(item.get("document_id", "")).strip() for item in items if isinstance(item, dict)}
    if not queue_documents or "" in queue_documents:
        raise ValueError("Owner review queue items must have document IDs")
    if not isinstance(history, list) or not history:
        raise ValueError("Owner review history must contain entries")

    seen: set[str] = set()
    dates: list[date] = []
    decisions: Counter[str] = Counter()
    for entry in history:
        if not isinstance(entry, dict):
            raise ValueError("Every owner review-history entry must be an object")
        required = {"review_id", "document_id", "reviewed_on", "decision", "owner", "note", "approval_applied"}
        if required.difference(entry):
            raise ValueError("Owner review-history entry is incomplete")
        review_id = str(entry["review_id"]).strip()
        if not review_id or review_id in seen:
            raise ValueError("Owner review-history IDs must be unique")
        seen.add(review_id)
        document_id = str(entry["document_id"]).strip()
        if document_id not in queue_documents:
            raise ValueError("Owner review-history document does not exist in queue")
        try:
            reviewed_on = date.fromisoformat(str(entry["reviewed_on"]))
        except ValueError as exc:
            raise ValueError("Owner review-history date must be ISO format") from exc
        if dates and reviewed_on < dates[-1]:
            raise ValueError("Owner review-history dates must be chronological")
        dates.append(reviewed_on)
        decision = str(entry["decision"]).strip()
        if decision not in _DECISIONS or not str(entry["owner"]).strip() or not str(entry["note"]).strip():
            raise ValueError("Owner review-history decision or note is invalid")
        if entry["approval_applied"] is not False:
            raise ValueError("Owner review-history cannot apply approval")
        decisions[decision] += 1

    return {
        "schema_version": "1.0",
        "entry_count": len(history),
        "decision_counts": dict(sorted(decisions.items())),
        "latest_reviewed_on": dates[-1].isoformat(),
        "evidence_mutated": False,
        "external_action_executed": False,
        "approval_applied": False,
        "boundary": "Owner review history records synthetic decisions for audit; it does not edit documents, promote evidence or alter retrieval behavior.",
    }

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any


_STATUSES = {"accepted", "pending", "rejected"}


def replay_owner_feedback(queue: dict[str, Any], history: list[dict[str, Any]], feedback_batch: list[dict[str, Any]]) -> dict[str, Any]:
    """Replay synthetic owner feedback as review metadata, never as an approval."""
    if not isinstance(queue, dict) or queue.get("review_only") is not True:
        raise ValueError("owner feedback requires a review-only queue")
    if queue.get("evidence_mutated") is not False or queue.get("external_action_executed") is not False:
        raise ValueError("owner feedback queue must remain non-writing")
    history_ids = {str(item.get("review_id")) for item in history if isinstance(item, dict)}
    if not history_ids:
        raise ValueError("owner review history must contain review IDs")
    if not isinstance(feedback_batch, list) or not feedback_batch:
        raise ValueError("owner feedback must be a non-empty list")
    seen: set[str] = set()
    statuses: Counter[str] = Counter()
    replayed: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    dates: list[date] = []
    for record in feedback_batch:
        if not isinstance(record, dict):
            raise ValueError("each owner feedback record must be an object")
        required = {"feedback_id", "review_id", "recorded_on", "status", "summary", "applied"}
        if required.difference(record):
            raise ValueError("owner feedback record is incomplete")
        feedback_id = str(record["feedback_id"]).strip()
        if not feedback_id or feedback_id in seen:
            raise ValueError("owner feedback IDs must be unique")
        seen.add(feedback_id)
        if str(record["review_id"]).strip() not in history_ids:
            raise ValueError("owner feedback review_id must reference review history")
        try:
            recorded_on = date.fromisoformat(str(record["recorded_on"]))
        except ValueError as exc:
            raise ValueError("owner feedback recorded_on must be ISO format") from exc
        if dates and recorded_on < dates[-1]:
            raise ValueError("owner feedback dates must be chronological")
        dates.append(recorded_on)
        status = str(record["status"]).strip()
        if status not in _STATUSES or not str(record["summary"]).strip():
            raise ValueError("owner feedback status or summary is invalid")
        if record["applied"] is not False:
            raise ValueError("owner feedback cannot apply approval")
        item = {"feedback_id": feedback_id, "review_id": str(record["review_id"]), "status": status, "passed": True}
        statuses[status] += 1
        (replayed if status == "accepted" else excluded).append(item)
    return {
        "schema_version": "1.0",
        "record_count": len(feedback_batch),
        "status_counts": dict(sorted(statuses.items())),
        "replayed_count": len(replayed),
        "excluded_count": len(excluded),
        "replayed": replayed,
        "excluded": excluded,
        "approval_applied": False,
        "evidence_mutated": False,
        "external_action_executed": False,
        "boundary": "Accepted owner feedback is replayed for audit visibility only; it does not renew, escalate or defer a document.",
    }


__all__ = ["replay_owner_feedback"]

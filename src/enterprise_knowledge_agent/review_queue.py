from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable, Any

from .models import KnowledgeDocument


REVIEW_QUEUE_VERSION = "0.8"


def build_owner_review_queue(
    documents: Iterable[KnowledgeDocument],
    *,
    as_of_date: str,
    max_source_age_days: int = 90,
) -> dict[str, Any]:
    """Build a deterministic, non-writing queue for stale or conflicting documents."""
    if max_source_age_days < 1:
        raise ValueError("max_source_age_days must be at least 1")
    try:
        as_of = date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise ValueError("as_of_date must be an ISO-8601 date") from exc

    document_list = list(documents)
    if not document_list:
        raise ValueError("documents must be a non-empty iterable")
    conflict_values: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for document in document_list:
        if not isinstance(document, KnowledgeDocument):
            raise ValueError("documents must contain KnowledgeDocument values")
        if document.claim_key and document.claim_value:
            conflict_values[document.claim_key][document.claim_value].append(document.document_id)
    conflicting_keys = {key for key, values in conflict_values.items() if len(values) > 1}

    items: list[dict[str, Any]] = []
    for document in document_list:
        updated = date.fromisoformat(document.updated_at)
        age_days = (as_of - updated).days
        reasons: list[str] = []
        if age_days > max_source_age_days:
            reasons.append("source_age_exceeded")
        if document.review_due_at and date.fromisoformat(document.review_due_at) < as_of:
            reasons.append("review_due_passed")
        if document.claim_key in conflicting_keys:
            reasons.append("structured_claim_conflict")
        if not reasons:
            continue
        priority = 1 if "structured_claim_conflict" in reasons else 2
        items.append({
            "document_id": document.document_id,
            "title": document.title,
            "owner": document.department,
            "priority": priority,
            "reasons": reasons,
            "status": "pending_review",
            "next_action": "Owner verifies source, resolves conflict or renews review date before retrieval relies on it.",
        })

    items.sort(key=lambda item: (item["priority"], item["document_id"]))
    return {
        "queue_version": REVIEW_QUEUE_VERSION,
        "as_of_date": as_of_date,
        "max_source_age_days": max_source_age_days,
        "item_count": len(items),
        "items": items,
        "review_only": True,
        "evidence_mutated": False,
        "external_action_executed": False,
        "boundary": "The queue proposes owner review only; it does not edit documents, promote evidence, or change retrieval policy.",
    }


__all__ = ["REVIEW_QUEUE_VERSION", "build_owner_review_queue"]

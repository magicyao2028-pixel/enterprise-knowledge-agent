from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable

from .models import SearchHit


def assess_evidence(
    hits: Iterable[SearchHit],
    *,
    as_of_date: str,
    max_source_age_days: int = 90,
) -> dict[str, object]:
    """Expose explicit freshness and structured-claim conflicts without guessing semantics."""
    if max_source_age_days < 1:
        raise ValueError("max_source_age_days must be at least 1")
    try:
        as_of = date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise ValueError("as_of_date must be an ISO-8601 date") from exc

    hit_list = list(hits)
    stale_sources: list[dict[str, object]] = []
    future_dated_sources: list[str] = []
    claim_groups: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for hit in hit_list:
        document = hit.document
        updated = date.fromisoformat(document.updated_at)
        age_days = (as_of - updated).days
        reasons: list[str] = []
        if age_days < 0:
            future_dated_sources.append(document.document_id)
        elif age_days > max_source_age_days:
            reasons.append(f"source age {age_days} days exceeds limit {max_source_age_days}")
        if document.review_due_at and date.fromisoformat(document.review_due_at) < as_of:
            reasons.append(f"review due date {document.review_due_at} has passed")
        if reasons:
            stale_sources.append(
                {
                    "document_id": document.document_id,
                    "updated_at": document.updated_at,
                    "review_due_at": document.review_due_at,
                    "reasons": reasons,
                }
            )
        if document.claim_key and document.claim_value:
            claim_groups[document.claim_key][document.claim_value].append(document.document_id)

    conflicts = []
    for claim_key, values in sorted(claim_groups.items()):
        if len(values) > 1:
            conflicts.append(
                {
                    "claim_key": claim_key,
                    "variants": [
                        {"claim_value": value, "document_ids": sorted(document_ids)}
                        for value, document_ids in sorted(values.items())
                    ],
                }
            )

    state = "conflicting" if conflicts else "stale" if stale_sources or future_dated_sources else "clear"
    return {
        "state": state,
        "as_of_date": as_of_date,
        "max_source_age_days": max_source_age_days,
        "stale_sources": stale_sources,
        "future_dated_document_ids": sorted(future_dated_sources),
        "conflicts": conflicts,
        "assessed_document_ids": [hit.document.document_id for hit in hit_list],
        "method_boundary": "Conflicts require matching structured claim_key values; free-text contradiction is not inferred.",
    }

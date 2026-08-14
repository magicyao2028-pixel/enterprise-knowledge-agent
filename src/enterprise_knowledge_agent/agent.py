from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from .governance import assess_evidence
from .models import KnowledgeDocument, MetadataFilters, SearchHit
from .retrieval import expand_query_terms, search_documents


SENSITIVE_TERMS = {
    "api key", "bank account", "credential", "password", "private key", "secret token",
}


@dataclass
class AgentTrace:
    steps: list[dict[str, str]] = field(default_factory=list)

    def record(self, tool: str, purpose: str, status: str = "completed") -> None:
        self.steps.append({"tool": tool, "purpose": purpose, "status": status})


class KnowledgeAgent:
    """Runs a transparent retrieval-and-answer workflow without a paid model."""

    def __init__(self, documents: Iterable[KnowledgeDocument], top_k: int = 3) -> None:
        self.documents = list(documents)
        if not self.documents:
            raise ValueError("At least one knowledge document is required")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        self.top_k = top_k

    def ask(
        self,
        query: str,
        filters: MetadataFilters | None = None,
        *,
        as_of_date: str | None = None,
        max_source_age_days: int = 90,
    ) -> dict[str, object]:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Query must not be blank")

        trace = AgentTrace()
        trace.record("validate_query", "Check query shape and policy boundaries.")
        sensitive_match = next((term for term in SENSITIVE_TERMS if term in cleaned_query.lower()), None)
        if sensitive_match:
            trace.record("safety_boundary", "Block requests for secrets or credentials.", "blocked")
            return self._blocked_response(cleaned_query, trace.steps)

        applied_filters = filters or MetadataFilters()
        hits = search_documents(cleaned_query, self.documents, self.top_k, filters=applied_filters)
        trace.record("retrieve_chunks", "Filter metadata and rank local document chunks with explicit lexical evidence.")
        if not hits:
            trace.record("evidence_gate", "Abstain because no source supports an answer.", "no_evidence")
            return self._no_evidence_response(cleaned_query, trace.steps, applied_filters)

        governance_hits = [hit for hit in hits if hit.score >= hits[0].score * 0.6]
        assessment = assess_evidence(
            governance_hits,
            as_of_date=as_of_date or date.today().isoformat(),
            max_source_age_days=max_source_age_days,
        )
        trace.record("assess_source_governance", "Check materially relevant sources for age, review dates and structured claim conflicts.")
        if assessment["state"] != "clear":
            status = "conflicting_evidence" if assessment["state"] == "conflicting" else "stale_evidence"
            trace.record("evidence_governance_gate", "Stop composition and route unresolved evidence to a knowledge owner.", status)
            return self._governance_review_response(
                cleaned_query,
                status,
                hits,
                assessment,
                trace.steps,
                applied_filters,
            )

        query_terms = expand_query_terms(cleaned_query)
        matched_terms = set(hits[0].matched_terms)
        coverage = len(matched_terms) / max(1, len(query_terms))
        confidence_score = round(min(1.0, 0.45 + coverage * 0.45 + min(hits[0].score, 10) / 100), 2)
        confidence_label = "high" if confidence_score >= 0.8 else "medium" if confidence_score >= 0.6 else "low"
        trace.record("evaluate_evidence", "Estimate lexical coverage and keep uncertainty visible.")

        selected = hits[:2]
        answer = " ".join(f"{hit.excerpt} [{hit.chunk_id}]" for hit in selected)
        citations = [
            {
                "document_id": hit.document.document_id,
                "chunk_id": hit.chunk_id,
                "title": hit.document.title,
                "department": hit.document.department,
                "updated_at": hit.document.updated_at,
            }
            for hit in selected
        ]
        trace.record("compose_grounded_answer", "Compose only from retrieved excerpts and attach citations.")

        return {
            "query": cleaned_query,
            "status": "answered",
            "answer": answer,
            "confidence": {"label": confidence_label, "score": confidence_score},
            "needs_human_review": confidence_label == "low",
            "citations": citations,
            "retrieved": [hit.to_dict() for hit in hits],
            "filters_applied": applied_filters.to_dict(),
            "evidence_assessment": assessment,
            "trace": trace.steps,
            "limitations": [
                "Retrieval is English lexical chunk matching, not semantic search.",
                "The answer is extractive and may not resolve ambiguous policy questions.",
                "Freshness uses explicit dates and a configurable age limit; it does not prove policy validity.",
                "Free-text contradiction is not inferred without structured claim metadata.",
                "Access permissions require production controls.",
            ],
        }

    @staticmethod
    def _governance_review_response(
        query: str,
        status: str,
        hits: list[SearchHit],
        assessment: dict[str, object],
        trace: list[dict[str, str]],
        filters: MetadataFilters,
    ) -> dict[str, object]:
        if status == "conflicting_evidence":
            answer = "The approved corpus contains conflicting structured policy values. A knowledge owner must resolve the source of truth."
        else:
            answer = "The supporting evidence is stale or future-dated for this analysis date. A knowledge owner must verify the current policy."
        return {
            "query": query,
            "status": status,
            "answer": answer,
            "confidence": {"label": "not_applicable", "score": 0.0},
            "needs_human_review": True,
            "citations": [
                {
                    "document_id": hit.document.document_id,
                    "chunk_id": hit.chunk_id,
                    "title": hit.document.title,
                    "department": hit.document.department,
                    "updated_at": hit.document.updated_at,
                }
                for hit in hits
            ],
            "retrieved": [hit.to_dict() for hit in hits],
            "filters_applied": filters.to_dict(),
            "evidence_assessment": assessment,
            "trace": trace,
        }

    @staticmethod
    def _no_evidence_response(
        query: str,
        trace: list[dict[str, str]],
        filters: MetadataFilters,
    ) -> dict[str, object]:
        return {
            "query": query,
            "status": "no_evidence",
            "answer": "I could not find enough evidence in the approved knowledge corpus. Please ask a knowledge owner.",
            "confidence": {"label": "none", "score": 0.0},
            "needs_human_review": True,
            "citations": [],
            "retrieved": [],
            "filters_applied": filters.to_dict(),
            "trace": trace,
        }

    @staticmethod
    def _blocked_response(query: str, trace: list[dict[str, str]]) -> dict[str, object]:
        return {
            "query": query,
            "status": "blocked",
            "answer": "I cannot provide or retrieve passwords, credentials, private keys, or secret tokens.",
            "confidence": {"label": "not_applicable", "score": 1.0},
            "needs_human_review": True,
            "citations": [],
            "retrieved": [],
            "trace": trace,
        }

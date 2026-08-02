from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .models import KnowledgeDocument
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

    def ask(self, query: str) -> dict[str, object]:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Query must not be blank")

        trace = AgentTrace()
        trace.record("validate_query", "Check query shape and policy boundaries.")
        sensitive_match = next((term for term in SENSITIVE_TERMS if term in cleaned_query.lower()), None)
        if sensitive_match:
            trace.record("safety_boundary", "Block requests for secrets or credentials.", "blocked")
            return self._blocked_response(cleaned_query, trace.steps)

        hits = search_documents(cleaned_query, self.documents, self.top_k)
        trace.record("retrieve_documents", "Rank local documents with explicit lexical evidence.")
        if not hits:
            trace.record("evidence_gate", "Abstain because no source supports an answer.", "no_evidence")
            return self._no_evidence_response(cleaned_query, trace.steps)

        query_terms = expand_query_terms(cleaned_query)
        matched_terms = set(hits[0].matched_terms)
        coverage = len(matched_terms) / max(1, len(query_terms))
        confidence_score = round(min(1.0, 0.45 + coverage * 0.45 + min(hits[0].score, 10) / 100), 2)
        confidence_label = "high" if confidence_score >= 0.8 else "medium" if confidence_score >= 0.6 else "low"
        trace.record("evaluate_evidence", "Estimate lexical coverage and keep uncertainty visible.")

        selected = hits[:2]
        answer = " ".join(f"{hit.excerpt} [{hit.document.document_id}]" for hit in selected)
        citations = [
            {
                "document_id": hit.document.document_id,
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
            "trace": trace.steps,
            "limitations": [
                "Retrieval is English lexical matching, not semantic search.",
                "The answer is extractive and may not resolve ambiguous policy questions.",
                "Source freshness and access permissions require production controls.",
            ],
        }

    @staticmethod
    def _no_evidence_response(query: str, trace: list[dict[str, str]]) -> dict[str, object]:
        return {
            "query": query,
            "status": "no_evidence",
            "answer": "I could not find enough evidence in the approved knowledge corpus. Please ask a knowledge owner.",
            "confidence": {"label": "none", "score": 0.0},
            "needs_human_review": True,
            "citations": [],
            "retrieved": [],
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

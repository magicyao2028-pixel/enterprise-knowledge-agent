from __future__ import annotations

import re
from typing import Iterable

from .models import KnowledgeDocument, SearchHit


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "our", "the", "to", "what",
    "should", "when", "where", "which", "with",
}
NORMAL_FORMS = {
    "complaints": "complaint",
    "escalated": "escalate",
    "escalating": "escalate",
    "escalation": "escalate",
    "returns": "return",
}


def tokenize(value: str) -> list[str]:
    return [NORMAL_FORMS.get(token, token) for token in TOKEN_PATTERN.findall(value.lower()) if token not in STOP_WORDS]


def expand_query_terms(value: str) -> set[str]:
    terms = set(tokenize(value))
    if "quickly" in terms or "time" in terms:
        terms.update({"minutes", "immediately", "deadline"})
    return terms


def search_documents(
    query: str,
    documents: Iterable[KnowledgeDocument],
    top_k: int = 3,
) -> list[SearchHit]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    query_terms = expand_query_terms(query)
    if not query_terms:
        return []

    hits: list[SearchHit] = []
    for document in documents:
        title_terms = set(tokenize(document.title))
        tag_terms = set(tokenize(" ".join(document.tags)))
        content_terms = set(tokenize(document.content))
        title_matches = query_terms & title_terms
        tag_matches = query_terms & tag_terms
        content_matches = query_terms & content_terms
        matched = title_matches | tag_matches | content_matches
        if not matched:
            continue

        score = (
            len(title_matches) * 3.0
            + len(tag_matches) * 2.0
            + len(content_matches)
            + len(matched) / len(query_terms)
        )
        if query.lower().strip() in f"{document.title} {document.content}".lower():
            score += 4.0
        hits.append(
            SearchHit(
                document=document,
                score=round(score, 3),
                matched_terms=tuple(sorted(matched)),
                excerpt=_best_excerpt(document.content, query_terms),
            )
        )

    return sorted(hits, key=lambda hit: (-hit.score, hit.document.document_id))[:top_k]


def _best_excerpt(content: str, query_terms: set[str]) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", content) if part.strip()]
    if not sentences:
        return content[:280]
    ranked = sorted(
        sentences,
        key=lambda sentence: len(query_terms & set(tokenize(sentence))),
        reverse=True,
    )
    return ranked[0][:280]

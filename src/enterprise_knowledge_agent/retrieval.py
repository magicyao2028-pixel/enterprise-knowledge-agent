from __future__ import annotations

import re
from typing import Iterable

from .models import KnowledgeChunk, KnowledgeDocument, MetadataFilters, SearchHit


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
    filters: MetadataFilters | None = None,
    chunk_words: int = 55,
) -> list[SearchHit]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    query_terms = expand_query_terms(query)
    if not query_terms:
        return []

    guard = filters or MetadataFilters()
    best_by_document: dict[str, SearchHit] = {}
    for document in documents:
        if not guard.matches(document):
            continue
        title_terms = set(tokenize(document.title))
        tag_terms = set(tokenize(" ".join(document.tags)))
        for chunk in chunk_document(document, chunk_words):
            content_terms = set(tokenize(chunk.text))
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
            if query.lower().strip() in f"{document.title} {chunk.text}".lower():
                score += 4.0
            hit = SearchHit(
                document=document,
                chunk_id=chunk.chunk_id,
                score=round(score, 3),
                matched_terms=tuple(sorted(matched)),
                excerpt=_best_excerpt(chunk.text, query_terms),
            )
            current = best_by_document.get(document.document_id)
            if current is None or hit.score > current.score:
                best_by_document[document.document_id] = hit

    return sorted(best_by_document.values(), key=lambda hit: (-hit.score, hit.document.document_id))[:top_k]


def chunk_document(document: KnowledgeDocument, max_words: int = 55) -> list[KnowledgeChunk]:
    if max_words < 5:
        raise ValueError("max_words must be at least 5")
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", document.content) if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        sentence_words = sentence.split()
        if len(sentence_words) > max_words:
            if current:
                chunks.append(" ".join(current))
                current, current_words = [], 0
            for start in range(0, len(sentence_words), max_words):
                chunks.append(" ".join(sentence_words[start : start + max_words]))
            continue
        if current and current_words + len(sentence_words) > max_words:
            chunks.append(" ".join(current))
            current, current_words = [], 0
        current.append(sentence)
        current_words += len(sentence_words)
    if current:
        chunks.append(" ".join(current))
    if not chunks:
        chunks = [document.content]
    return [
        KnowledgeChunk(
            chunk_id=f"{document.document_id}-C{index:03d}",
            document=document,
            text=text,
            position=index,
        )
        for index, text in enumerate(chunks, start=1)
    ]


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

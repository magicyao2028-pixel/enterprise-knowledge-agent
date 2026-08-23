from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Iterable, Literal

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
RETRIEVAL_MODES = ("lexical", "local_vector", "hybrid")
RetrievalMode = Literal["lexical", "local_vector", "hybrid"]


def tokenize(value: str) -> list[str]:
    return [NORMAL_FORMS.get(token, token) for token in TOKEN_PATTERN.findall(value.lower()) if token not in STOP_WORDS]


def expand_query_terms(value: str) -> set[str]:
    terms = set(tokenize(value))
    if "quickly" in terms or "time" in terms:
        terms.update({"minutes", "immediately", "deadline"})
    return terms


def _features(value: str) -> list[str]:
    """Return deterministic token and character-ngram features for local vectors."""
    features: list[str] = []
    for token in tokenize(value):
        features.append(f"t:{token}")
        if len(token) >= 3:
            features.extend(f"c:{token[index:index + 3]}" for index in range(len(token) - 2))
    return features


class LocalVectorAdapter:
    """Dependency-free hashed sparse vectors for an honest local reranker.

    This is not a pretrained semantic embedding model. It is a deterministic
    token/character-ngram reranking baseline that can run offline and be replaced
    by a reviewed local embedding model later without changing the agent API.
    """

    def __init__(self, dimension: int = 256) -> None:
        if dimension < 32:
            raise ValueError("dimension must be at least 32")
        self.dimension = dimension

    def encode(self, value: str) -> list[float]:
        vector = [0.0] * self.dimension
        for feature, count in Counter(_features(value)).items():
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign * count
        return vector

    @staticmethod
    def cosine(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return max(0.0, numerator / (left_norm * right_norm))

    def score(self, query: str, document: KnowledgeDocument, chunk: KnowledgeChunk) -> float:
        query_features = set(_features(query))
        body_features = set(_features(chunk.text))
        title_features = set(_features(document.title))
        tag_features = set(_features(" ".join(document.tags)))
        if not query_features.intersection(body_features | title_features | tag_features):
            return 0.0
        query_vector = self.encode(query)
        body_score = self.cosine(query_vector, self.encode(chunk.text))
        title_score = self.cosine(query_vector, self.encode(document.title))
        tag_score = self.cosine(query_vector, self.encode(" ".join(document.tags)))
        return round(body_score * 0.65 + title_score * 0.25 + tag_score * 0.10, 6)


def search_documents(
    query: str,
    documents: Iterable[KnowledgeDocument],
    top_k: int = 3,
    filters: MetadataFilters | None = None,
    chunk_words: int = 55,
    retrieval_mode: RetrievalMode = "lexical",
) -> list[SearchHit]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if retrieval_mode not in RETRIEVAL_MODES:
        raise ValueError(f"retrieval_mode must be one of: {', '.join(RETRIEVAL_MODES)}")
    query_terms = expand_query_terms(query)
    if not query_terms:
        return []

    guard = filters or MetadataFilters()
    adapter = LocalVectorAdapter() if retrieval_mode in {"local_vector", "hybrid"} else None
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
            lexical_score = 0.0
            if matched:
                lexical_score = (
                    len(title_matches) * 3.0
                    + len(tag_matches) * 2.0
                    + len(content_matches)
                    + len(matched) / len(query_terms)
                )
                if query.lower().strip() in f"{document.title} {chunk.text}".lower():
                    lexical_score += 4.0
            vector_score = adapter.score(query, document, chunk) if adapter else 0.0
            if retrieval_mode in {"local_vector", "hybrid"} and not matched:
                # Keep the governed no-evidence boundary from lexical retrieval;
                # the optional vector adapter may rerank supported candidates but
                # must not invent evidence from hash collisions or common n-grams.
                continue
            if retrieval_mode == "lexical":
                score = lexical_score
            elif retrieval_mode == "local_vector":
                score = vector_score * 10
            else:
                score = lexical_score + vector_score * 3
            if score <= 0:
                continue
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

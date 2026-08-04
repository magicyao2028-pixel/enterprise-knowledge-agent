from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    title: str
    department: str
    updated_at: str
    content: str
    tags: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "KnowledgeDocument":
        required = {"document_id", "title", "department", "updated_at", "content"}
        missing = sorted(required.difference(value))
        if missing:
            raise ValueError(f"Missing document fields: {', '.join(missing)}")

        tags = value.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(item, str) for item in tags):
            raise ValueError("tags must be a list of strings")

        document = cls(
            document_id=str(value["document_id"]).strip(),
            title=str(value["title"]).strip(),
            department=str(value["department"]).strip(),
            updated_at=str(value["updated_at"]).strip(),
            content=str(value["content"]).strip(),
            tags=tuple(item.strip() for item in tags if item.strip()),
        )
        if not all((document.document_id, document.title, document.department, document.updated_at, document.content)):
            raise ValueError("Document fields must not be blank")
        return document

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["tags"] = list(self.tags)
        return value


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    document: KnowledgeDocument
    text: str
    position: int


@dataclass(frozen=True)
class MetadataFilters:
    departments: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    updated_after: str | None = None

    def __post_init__(self) -> None:
        if self.updated_after:
            try:
                date.fromisoformat(self.updated_after)
            except ValueError as exc:
                raise ValueError("updated_after must be an ISO-8601 date") from exc

    def matches(self, document: KnowledgeDocument) -> bool:
        if self.departments and document.department.casefold() not in {item.casefold() for item in self.departments}:
            return False
        if self.tags:
            document_tags = {item.casefold() for item in document.tags}
            if not {item.casefold() for item in self.tags}.intersection(document_tags):
                return False
        if self.updated_after and document.updated_at < self.updated_after:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "departments": list(self.departments),
            "tags": list(self.tags),
            "updated_after": self.updated_after,
        }


@dataclass(frozen=True)
class SearchHit:
    document: KnowledgeDocument
    chunk_id: str
    score: float
    matched_terms: tuple[str, ...]
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document.document_id,
            "chunk_id": self.chunk_id,
            "title": self.document.title,
            "department": self.document.department,
            "updated_at": self.document.updated_at,
            "score": self.score,
            "matched_terms": list(self.matched_terms),
            "excerpt": self.excerpt,
        }

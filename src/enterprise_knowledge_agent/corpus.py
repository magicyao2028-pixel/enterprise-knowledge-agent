from __future__ import annotations

import json
from pathlib import Path

from .models import KnowledgeDocument


def load_documents(path: Path) -> list[KnowledgeDocument]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid knowledge JSON: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise ValueError("Knowledge corpus must be a JSON array")

    documents = [KnowledgeDocument.from_mapping(item) for item in payload]
    if not documents:
        raise ValueError("Knowledge corpus must contain at least one document")
    identifiers = [document.document_id for document in documents]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("document_id values must be unique")
    return documents

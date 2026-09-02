"""Offline, citation-first enterprise knowledge agent."""

from .agent import KnowledgeAgent
from .corpus import load_documents
from .governance import assess_evidence
from .models import KnowledgeDocument, MetadataFilters
from .embedding_gate import assess_embedding_candidate
from .review_queue import build_owner_review_queue
from .review_history import summarize_owner_review_history

__all__ = ["KnowledgeAgent", "KnowledgeDocument", "MetadataFilters", "assess_evidence", "load_documents", "assess_embedding_candidate", "build_owner_review_queue", "summarize_owner_review_history"]
__version__ = "1.0.0"

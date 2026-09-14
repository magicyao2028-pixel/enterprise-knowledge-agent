"""Offline, citation-first enterprise knowledge agent."""

from ._version import __version__
from .access_control import (
    AccessPolicy,
    ask_with_access_control,
    load_access_policy,
    prefilter_authorized_documents,
)
from .agent import KnowledgeAgent
from .corpus import load_documents
from .governance import assess_evidence
from .models import KnowledgeDocument, MetadataFilters
from .embedding_gate import assess_embedding_candidate
from .review_queue import build_owner_review_queue
from .review_history import summarize_owner_review_history
from .owner_feedback_replay import replay_owner_feedback

__all__ = [
    "AccessPolicy",
    "KnowledgeAgent",
    "KnowledgeDocument",
    "MetadataFilters",
    "__version__",
    "ask_with_access_control",
    "assess_embedding_candidate",
    "assess_evidence",
    "build_owner_review_queue",
    "load_access_policy",
    "load_documents",
    "prefilter_authorized_documents",
    "replay_owner_feedback",
    "summarize_owner_review_history",
]

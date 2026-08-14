"""Offline, citation-first enterprise knowledge agent."""

from .agent import KnowledgeAgent
from .corpus import load_documents
from .governance import assess_evidence
from .models import KnowledgeDocument, MetadataFilters

__all__ = ["KnowledgeAgent", "KnowledgeDocument", "MetadataFilters", "assess_evidence", "load_documents"]
__version__ = "0.4.0"

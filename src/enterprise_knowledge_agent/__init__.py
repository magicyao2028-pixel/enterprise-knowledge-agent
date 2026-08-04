"""Offline, citation-first enterprise knowledge agent."""

from .agent import KnowledgeAgent
from .corpus import load_documents
from .models import KnowledgeDocument, MetadataFilters

__all__ = ["KnowledgeAgent", "KnowledgeDocument", "MetadataFilters", "load_documents"]
__version__ = "0.3.0"

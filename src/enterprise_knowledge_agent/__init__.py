"""Offline, citation-first enterprise knowledge agent."""

from .agent import KnowledgeAgent
from .corpus import load_documents
from .models import KnowledgeDocument

__all__ = ["KnowledgeAgent", "KnowledgeDocument", "load_documents"]
__version__ = "0.2.0"

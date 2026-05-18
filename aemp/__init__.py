"""AEMP - AI Episodic Memory Protocol

A structured protocol for AI agents to share episodic memories,
learned insights, and failure records with confidence scoring
and temporal validity.
"""

from aemp.schema import Episode, Insight, Failure, MemoryEntry, MemoryType
from aemp.store import MemoryStore
from aemp.publisher import Publisher
from aemp.subscriber import Subscriber

__version__ = "0.1.0"
__all__ = [
    "Episode",
    "Insight",
    "Failure",
    "MemoryEntry",
    "MemoryType",
    "MemoryStore",
    "Publisher",
    "Subscriber",
]

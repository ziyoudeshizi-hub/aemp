"""Subscriber - High-level API for querying and consuming memories."""

from __future__ import annotations

from aemp.schema import Episode, Failure, Insight, MemoryEntry, MemoryType
from aemp.store import MemoryStore


class Subscriber:
    """Convenience API for querying and consuming shared memories."""

    def __init__(self, store: MemoryStore, agent_name: str | None = None):
        self.store = store
        self.agent = agent_name  # Optionally filter to "not me"

    def recent(self, limit: int = 20, include_expired: bool = False) -> list[MemoryEntry]:
        """Get the most recent memories."""
        return self.store.query(limit=limit, include_expired=include_expired)

    def from_agent(self, agent: str, limit: int = 50) -> list[MemoryEntry]:
        """Get memories from a specific agent."""
        return self.store.query(agent=agent, limit=limit)

    def from_others(self, limit: int = 50) -> list[MemoryEntry]:
        """Get memories from all agents except self."""
        if not self.agent:
            return self.recent(limit=limit)
        all_memories = self.store.query(limit=limit * 2)
        return [m for m in all_memories if m.agent != self.agent][:limit]

    def episodes(self, **kwargs) -> list[Episode]:
        """Get episode-type memories."""
        entries = self.store.query(memory_type=MemoryType.EPISODE, **kwargs)
        return [e for e in entries if isinstance(e, Episode)]

    def insights(self, min_confidence: float = 0.5, **kwargs) -> list[Insight]:
        """Get insights above a confidence threshold."""
        entries = self.store.query(
            memory_type=MemoryType.INSIGHT,
            min_confidence=min_confidence,
            **kwargs,
        )
        return [e for e in entries if isinstance(e, Insight)]

    def failures(self, **kwargs) -> list[Failure]:
        """Get failure records (useful for avoiding repeated mistakes)."""
        entries = self.store.query(memory_type=MemoryType.FAILURE, **kwargs)
        return [e for e in entries if isinstance(e, Failure)]

    def by_tags(self, tags: list[str], limit: int = 50) -> list[MemoryEntry]:
        """Get memories matching any of the given tags."""
        return self.store.query(tags=tags, limit=limit)

    def related_to(self, entry_id: str) -> list[MemoryEntry]:
        """Find memories related to a given entry."""
        results = []
        for entry in self.store.query(limit=500):
            if entry_id in entry.relations.related_to:
                results.append(entry)
            if entry.relations.caused_by == entry_id:
                results.append(entry)
            if entry.relations.supersedes == entry_id:
                results.append(entry)
        return results

    def search(self, keyword: str, limit: int = 20) -> list[MemoryEntry]:
        """Simple keyword search across summaries."""
        keyword_lower = keyword.lower()
        results = []
        for entry in self.store.query(limit=500):
            if keyword_lower in entry.summary.lower():
                results.append(entry)
            elif keyword_lower in entry.context.get("detail", "").lower():
                results.append(entry)
            if len(results) >= limit:
                break
        return results

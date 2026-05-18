"""Publisher - High-level API for AI agents to publish memories."""

from __future__ import annotations

from aemp.schema import Episode, Failure, Insight, MemoryEntry, Outcome, Relation
from aemp.store import MemoryStore


class Publisher:
    """Convenience API for publishing memories to the store."""

    def __init__(self, store: MemoryStore, agent_name: str):
        self.store = store
        self.agent = agent_name

    def record_episode(
        self,
        summary: str,
        action: str,
        result: str,
        outcome: Outcome = Outcome.SUCCESS,
        confidence: float = 1.0,
        tags: list[str] | None = None,
        lessons: list[str] | None = None,
        context: dict | None = None,
        caused_by: str | None = None,
    ) -> str:
        """Record an episode (something that happened)."""
        episode = Episode(
            agent=self.agent,
            summary=summary,
            action=action,
            result=result,
            outcome=outcome,
            confidence=confidence,
            tags=tags or [],
            lessons=lessons or [],
            context=context or {},
            relations=Relation(caused_by=caused_by),
        )
        return self.store.publish(episode)

    def record_insight(
        self,
        summary: str,
        pattern: str,
        conditions: str = "",
        confidence: float = 0.8,
        tags: list[str] | None = None,
        evidence: list[str] | None = None,
        expires: str | None = None,
    ) -> str:
        """Record an insight (a pattern learned from episodes)."""
        insight = Insight(
            agent=self.agent,
            summary=summary,
            pattern=pattern,
            conditions=conditions,
            confidence=confidence,
            tags=tags or [],
            evidence=evidence or [],
            expires=expires,
        )
        return self.store.publish(insight)

    def record_failure(
        self,
        summary: str,
        attempted: str,
        expected: str,
        actual: str,
        root_cause: str = "",
        workaround: str = "",
        confidence: float = 1.0,
        tags: list[str] | None = None,
        context: dict | None = None,
    ) -> str:
        """Record a failure (something that didn't work)."""
        failure = Failure(
            agent=self.agent,
            summary=summary,
            attempted=attempted,
            expected=expected,
            actual=actual,
            root_cause=root_cause,
            workaround=workaround,
            confidence=confidence,
            tags=tags or [],
            context=context or {},
        )
        return self.store.publish(failure)

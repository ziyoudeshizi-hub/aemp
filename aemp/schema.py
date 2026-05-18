"""Core schema definitions for the AEMP protocol."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    """Types of memory entries in the protocol."""

    EPISODE = "episode"  # Something that happened (action + result)
    INSIGHT = "insight"  # A pattern or rule learned from episodes
    FAILURE = "failure"  # Something that didn't work (with why)


class Outcome(str, Enum):
    """Outcome of an episode."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class Relation:
    """Relational links between memory entries."""

    caused_by: str | None = None
    supersedes: str | None = None
    related_to: list[str] = field(default_factory=list)


@dataclass
class MemoryEntry:
    """Base class for all memory entries in the protocol."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType = MemoryType.EPISODE
    agent: str = ""  # Which AI created this
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires: str | None = None  # ISO8601 or None (never expires)
    confidence: float = 1.0  # 0.0 to 1.0
    tags: list[str] = field(default_factory=list)
    summary: str = ""  # Human-readable summary
    context: dict[str, Any] = field(default_factory=dict)
    relations: Relation = field(default_factory=Relation)

    def is_expired(self) -> bool:
        """Check if this memory has expired."""
        if self.expires is None:
            return False
        exp_time = datetime.fromisoformat(self.expires)
        now = datetime.now(timezone.utc)
        if exp_time.tzinfo is None:
            exp_time = exp_time.replace(tzinfo=timezone.utc)
        return now > exp_time

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "agent": self.agent,
            "timestamp": self.timestamp,
            "expires": self.expires,
            "confidence": self.confidence,
            "tags": self.tags,
            "summary": self.summary,
            "context": self.context,
            "relations": {
                "caused_by": self.relations.caused_by,
                "supersedes": self.relations.supersedes,
                "related_to": self.relations.related_to,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        """Deserialize from dictionary."""
        relations_data = data.get("relations", {})
        relation = Relation(
            caused_by=relations_data.get("caused_by"),
            supersedes=relations_data.get("supersedes"),
            related_to=relations_data.get("related_to", []),
        )
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MemoryType(data.get("type", "episode")),
            agent=data.get("agent", ""),
            timestamp=data.get("timestamp", ""),
            expires=data.get("expires"),
            confidence=data.get("confidence", 1.0),
            tags=data.get("tags", []),
            summary=data.get("summary", ""),
            context=data.get("context", {}),
            relations=relation,
        )


@dataclass
class Episode(MemoryEntry):
    """A record of something that happened."""

    outcome: Outcome = Outcome.UNKNOWN
    action: str = ""  # What was done
    result: str = ""  # What happened as a result
    lessons: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = MemoryType.EPISODE

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["outcome"] = self.outcome.value
        d["action"] = self.action
        d["result"] = self.result
        d["lessons"] = self.lessons
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Episode:
        base = MemoryEntry.from_dict(data)
        return cls(
            id=base.id,
            agent=base.agent,
            timestamp=base.timestamp,
            expires=base.expires,
            confidence=base.confidence,
            tags=base.tags,
            summary=base.summary,
            context=base.context,
            relations=base.relations,
            outcome=Outcome(data.get("outcome", "unknown")),
            action=data.get("action", ""),
            result=data.get("result", ""),
            lessons=data.get("lessons", []),
        )


@dataclass
class Insight(MemoryEntry):
    """A pattern or rule learned from multiple episodes."""

    pattern: str = ""  # The pattern description
    evidence: list[str] = field(default_factory=list)  # Episode IDs supporting this
    conditions: str = ""  # When this insight applies
    counter_examples: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = MemoryType.INSIGHT

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["pattern"] = self.pattern
        d["evidence"] = self.evidence
        d["conditions"] = self.conditions
        d["counter_examples"] = self.counter_examples
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Insight:
        base = MemoryEntry.from_dict(data)
        return cls(
            id=base.id,
            agent=base.agent,
            timestamp=base.timestamp,
            expires=base.expires,
            confidence=base.confidence,
            tags=base.tags,
            summary=base.summary,
            context=base.context,
            relations=base.relations,
            pattern=data.get("pattern", ""),
            evidence=data.get("evidence", []),
            conditions=data.get("conditions", ""),
            counter_examples=data.get("counter_examples", []),
        )


@dataclass
class Failure(MemoryEntry):
    """A record of something that didn't work."""

    attempted: str = ""  # What was tried
    expected: str = ""  # What was expected to happen
    actual: str = ""  # What actually happened
    root_cause: str = ""  # Why it failed (if known)
    workaround: str = ""  # How to avoid this in future

    def __post_init__(self):
        self.type = MemoryType.FAILURE

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["attempted"] = self.attempted
        d["expected"] = self.expected
        d["actual"] = self.actual
        d["root_cause"] = self.root_cause
        d["workaround"] = self.workaround
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Failure:
        base = MemoryEntry.from_dict(data)
        return cls(
            id=base.id,
            agent=base.agent,
            timestamp=base.timestamp,
            expires=base.expires,
            confidence=base.confidence,
            tags=base.tags,
            summary=base.summary,
            context=base.context,
            relations=base.relations,
            attempted=data.get("attempted", ""),
            expected=data.get("expected", ""),
            actual=data.get("actual", ""),
            root_cause=data.get("root_cause", ""),
            workaround=data.get("workaround", ""),
        )

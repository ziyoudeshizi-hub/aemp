"""Memory storage backend for AEMP.

File-based storage using JSON Lines format for append-friendly writes.
Supports querying by agent, type, tags, time range, and confidence.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aemp.schema import (
    Episode,
    Failure,
    Insight,
    MemoryEntry,
    MemoryType,
)


class MemoryStore:
    """File-based memory store using JSON Lines."""

    def __init__(self, path: str | Path):
        """Initialize store at the given directory path."""
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._memories_file = self.path / "memories.jsonl"
        self._index_file = self.path / "index.json"
        self._lock = threading.Lock()
        self._index: dict[str, int] = {}  # id -> line offset
        self._load_index()

    def _load_index(self) -> None:
        """Load or rebuild the index."""
        if self._index_file.exists():
            try:
                self._index = json.loads(self._index_file.read_text(encoding="utf-8"))
                return
            except (json.JSONDecodeError, OSError):
                pass
        # Rebuild index from memories file
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild the index by scanning the memories file."""
        self._index = {}
        if not self._memories_file.exists():
            return
        with open(self._memories_file, "r", encoding="utf-8") as f:
            offset = 0
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        self._index[data["id"]] = offset
                    except (json.JSONDecodeError, KeyError):
                        pass
                offset += 1
        self._save_index()

    def _save_index(self) -> None:
        """Persist the index to disk."""
        self._index_file.write_text(
            json.dumps(self._index, ensure_ascii=False), encoding="utf-8"
        )

    def publish(self, entry: MemoryEntry) -> str:
        """Store a memory entry. Returns the entry ID."""
        with self._lock:
            line_num = sum(1 for _ in open(self._memories_file, encoding="utf-8")) if self._memories_file.exists() else 0
            with open(self._memories_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
            self._index[entry.id] = line_num
            self._save_index()
        return entry.id

    def get(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a single memory by ID."""
        if entry_id not in self._index:
            return None
        line_num = self._index[entry_id]
        line = self._read_line(line_num)
        if line is None:
            return None
        return self._deserialize(line)

    def query(
        self,
        agent: str | None = None,
        memory_type: MemoryType | None = None,
        tags: list[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        min_confidence: float = 0.0,
        include_expired: bool = False,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Query memories with filters."""
        results: list[MemoryEntry] = []
        for entry in self._iter_all():
            if not include_expired and entry.is_expired():
                continue
            if agent and entry.agent != agent:
                continue
            if memory_type and entry.type != memory_type:
                continue
            if tags and not set(tags).intersection(set(entry.tags)):
                continue
            if entry.confidence < min_confidence:
                continue
            if after:
                after_dt = datetime.fromisoformat(after)
                entry_dt = datetime.fromisoformat(entry.timestamp)
                if entry_dt <= after_dt:
                    continue
            if before:
                before_dt = datetime.fromisoformat(before)
                entry_dt = datetime.fromisoformat(entry.timestamp)
                if entry_dt >= before_dt:
                    continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def forget(self, entry_id: str) -> bool:
        """Mark a memory as forgotten (soft delete by setting expires to now)."""
        entry = self.get(entry_id)
        if entry is None:
            return False
        entry.expires = datetime.now(timezone.utc).isoformat()
        # Rewrite is expensive; for v0.1 we append an updated version
        # and supersede the old one
        entry.id = entry.id  # Keep same ID for the overwrite
        self._overwrite(entry)
        return True

    def gc(self) -> int:
        """Garbage collect expired memories. Returns count of removed entries."""
        all_entries = list(self._iter_all())
        active = [e for e in all_entries if not e.is_expired()]
        removed = len(all_entries) - len(active)
        if removed > 0:
            self._rewrite_all(active)
        return removed

    def count(self) -> int:
        """Count total non-expired memories."""
        return sum(1 for e in self._iter_all() if not e.is_expired())

    def _overwrite(self, entry: MemoryEntry) -> None:
        """Overwrite an entry (rewrite entire file)."""
        all_entries = list(self._iter_all())
        for i, e in enumerate(all_entries):
            if e.id == entry.id:
                all_entries[i] = entry
                break
        self._rewrite_all(all_entries)

    def _rewrite_all(self, entries: list[MemoryEntry]) -> None:
        """Rewrite the entire store with given entries."""
        with self._lock:
            with open(self._memories_file, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
            self._index = {e.id: i for i, e in enumerate(entries)}
            self._save_index()

    def _iter_all(self):
        """Iterate all memory entries from disk."""
        if not self._memories_file.exists():
            return
        with open(self._memories_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = self._deserialize(line)
                    if entry:
                        yield entry

    def _read_line(self, line_num: int) -> str | None:
        """Read a specific line from the memories file."""
        if not self._memories_file.exists():
            return None
        with open(self._memories_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == line_num:
                    return line.strip()
        return None

    @staticmethod
    def _deserialize(line: str) -> MemoryEntry | None:
        """Deserialize a JSON line into the appropriate MemoryEntry subclass."""
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        mem_type = data.get("type", "episode")
        if mem_type == "episode":
            return Episode.from_dict(data)
        elif mem_type == "insight":
            return Insight.from_dict(data)
        elif mem_type == "failure":
            return Failure.from_dict(data)
        else:
            return MemoryEntry.from_dict(data)

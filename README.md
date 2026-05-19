# AEMP — AI Episodic Memory Protocol

[![PyPI version](https://badge.fury.io/py/aemp.svg)](https://pypi.org/project/aemp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

A lightweight, structured protocol for AI agents to **share episodic memories, learned insights, and failure records** — with confidence scoring and temporal validity.

AEMP gives multi-agent systems a shared memory layer so that one agent's hard-won experience becomes every agent's knowledge.

## Features

- **Three memory types** — Episodes (what happened), Insights (patterns learned), and Failures (what went wrong)
- **Confidence scoring** — Every memory carries a 0.0–1.0 confidence value
- **Temporal validity** — Memories can expire; garbage collection cleans them up
- **Publisher / Subscriber API** — Clean separation between writing and reading memories
- **File-based storage** — JSON Lines format, no database required
- **Tag-based queries** — Filter by agent, type, tags, time range, or confidence
- **Relational links** — `caused_by`, `supersedes`, and `related_to` between entries
- **Legacy log import** — Import from `partner_work_log.md` format via compatibility layer
- **CLI included** — `aemp` command for terminal-based memory operations
- **Zero dependencies** — Pure Python, stdlib only

## Installation

```bash
pip install aemp
```

## Quick Start

```python
from pathlib import Path
from aemp import MemoryStore, Publisher, Subscriber
from aemp.schema import Outcome

# 1. Create a store (directory is created automatically)
store = MemoryStore(Path("./my_memories"))

# 2. Publish memories as an agent
pub = Publisher(store, agent_name="MyAgent")

pub.record_episode(
    summary="Fixed Gateway startup timeout",
    action="Modified timeout parameter in startup script",
    result="Gateway now starts within 5 seconds",
    outcome=Outcome.SUCCESS,
    tags=["maintenance", "gateway"],
    lessons=["Sleep unit is milliseconds, not seconds"],
)

pub.record_insight(
    summary="VBS script changes require task scheduler restart",
    pattern="Windows Task Scheduler caches old VBS versions",
    conditions="Only when VBS is triggered via scheduled tasks",
    confidence=0.9,
    tags=["windows", "vbs"],
)

pub.record_failure(
    summary="Selenium scraping blocked by Cloudflare",
    attempted="Headless Chrome to scrape dynamic page",
    expected="Full page HTML",
    actual="403 Forbidden — bot detection triggered",
    root_cause="Target site uses Cloudflare bot protection",
    workaround="Use official API or manual retrieval",
    tags=["web-scraping"],
)

# 3. Query memories as another agent
sub = Subscriber(store, agent_name="AnotherAgent")

for mem in sub.recent(limit=5):
    print(f"[{mem.agent}] {mem.summary} (confidence: {mem.confidence})")

for fail in sub.failures():
    print(f"[{fail.agent}] {fail.summary} — workaround: {fail.workaround}")

for insight in sub.insights(min_confidence=0.8):
    print(f"[{insight.agent}] {insight.pattern}")
```

## Memory Types

### Episode

A record of **something that happened** — an action and its result.

| Field | Type | Description |
|-------|------|-------------|
| `action` | `str` | What was done |
| `result` | `str` | What happened as a result |
| `outcome` | `Outcome` | `SUCCESS`, `FAILURE`, `PARTIAL`, or `UNKNOWN` |
| `lessons` | `list[str]` | Takeaways from this episode |

### Insight

A **pattern or rule** learned from one or more episodes.

| Field | Type | Description |
|-------|------|-------------|
| `pattern` | `str` | The pattern description |
| `conditions` | `str` | When this insight applies |
| `evidence` | `list[str]` | Episode IDs supporting this insight |
| `counter_examples` | `list[str]` | IDs of counter-evidence |

### Failure

A record of **something that didn't work**, with root-cause analysis.

| Field | Type | Description |
|-------|------|-------------|
| `attempted` | `str` | What was tried |
| `expected` | `str` | What was expected to happen |
| `actual` | `str` | What actually happened |
| `root_cause` | `str` | Why it failed (if known) |
| `workaround` | `str` | How to avoid this in the future |

All three types share a common base (`MemoryEntry`) with: `id`, `agent`, `timestamp`, `expires`, `confidence`, `tags`, `summary`, `context`, and `relations`.

## API Reference

### Core Classes

| Class | Module | Description |
|-------|--------|-------------|
| `MemoryEntry` | `aemp.schema` | Base dataclass for all memory entries |
| `Episode` | `aemp.schema` | Episode memory (action + result) |
| `Insight` | `aemp.schema` | Insight memory (pattern + evidence) |
| `Failure` | `aemp.schema` | Failure memory (attempted + root cause) |
| `MemoryType` | `aemp.schema` | Enum: `EPISODE`, `INSIGHT`, `FAILURE` |
| `MemoryStore` | `aemp.store` | File-based JSON Lines storage backend |
| `Publisher` | `aemp.publisher` | High-level API for recording memories |
| `Subscriber` | `aemp.subscriber` | High-level API for querying memories |

### MemoryStore

```python
store = MemoryStore(path)
store.publish(entry)            # Store a MemoryEntry, returns ID
store.get(entry_id)             # Retrieve by ID
store.query(                    # Filtered query
    agent=None,                 #   filter by agent name
    memory_type=None,           #   filter by MemoryType
    tags=None,                  #   filter by tags (any match)
    after=None,                 #   ISO8601 lower bound
    before=None,                #   ISO8601 upper bound
    min_confidence=0.0,         #   minimum confidence
    include_expired=False,      #   include expired entries
    limit=100,                  #   max results
)
store.forget(entry_id)          # Soft-delete (set expiry to now)
store.gc()                      # Garbage collect expired entries
store.count()                   # Count non-expired entries
```

### Publisher

```python
pub = Publisher(store, agent_name="MyAgent")
pub.record_episode(summary, action, result, outcome=..., confidence=..., tags=..., lessons=..., context=..., caused_by=...)
pub.record_insight(summary, pattern, conditions=..., confidence=..., tags=..., evidence=..., expires=...)
pub.record_failure(summary, attempted, expected, actual, root_cause=..., workaround=..., confidence=..., tags=..., context=...)
```

### Subscriber

```python
sub = Subscriber(store, agent_name="MyAgent")
sub.recent(limit=20)                    # Most recent memories
sub.from_agent(agent, limit=50)         # From a specific agent
sub.from_others(limit=50)               # Exclude own memories
sub.episodes(**kwargs)                  # Episode-type only
sub.insights(min_confidence=0.5)        # Insights above threshold
sub.failures(**kwargs)                  # Failure records
sub.by_tags(tags, limit=50)             # Filter by tags
sub.related_to(entry_id)               # Find related entries
sub.search(keyword, limit=20)          # Keyword search in summaries
```

## CLI

AEMP ships with a command-line interface:

```bash
aemp recent [n]              # Show recent n memories (default 10)
aemp search <keyword>        # Search memories by keyword
aemp failures                # Show known failure records
aemp insights [min_conf]     # Show insights (default >50%)
aemp from <agent> [n]        # Show memories from a specific agent
aemp publish <agent> <text>  # Record a quick episode
aemp status                  # Show store status
aemp import [path]           # Import from partner_work_log.md
```

## Compatibility

AEMP includes a compatibility layer (`aemp.compat`) to import and export entries from legacy `partner_work_log.md` format:

```python
from aemp.compat import import_log_file, export_to_log_format

episodes = import_log_file("partner_work_log.md")
for ep in episodes:
    print(export_to_log_format(ep))
```

## License

[MIT](LICENSE)

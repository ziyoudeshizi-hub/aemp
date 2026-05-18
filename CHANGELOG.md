# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-05-15

### Added

- **Core schema** (`aemp.schema`)
  - `MemoryEntry` base dataclass with id, agent, timestamp, expires, confidence, tags, summary, context, and relations
  - `Episode` — action + result + outcome + lessons
  - `Insight` — pattern + evidence + conditions + counter-examples
  - `Failure` — attempted + expected + actual + root cause + workaround
  - `MemoryType` enum (`EPISODE`, `INSIGHT`, `FAILURE`)
  - `Outcome` enum (`SUCCESS`, `FAILURE`, `PARTIAL`, `UNKNOWN`)
  - `Relation` dataclass (`caused_by`, `supersedes`, `related_to`)
  - Full `to_dict()` / `from_dict()` serialization for all types
  - Temporal expiry via `is_expired()` check

- **File-based storage** (`aemp.store`)
  - `MemoryStore` with JSON Lines append-friendly format
  - Index file for fast ID lookups
  - `publish()`, `get()`, `query()`, `forget()`, `gc()`, `count()` methods
  - Filtering by agent, type, tags, time range, and confidence threshold
  - Thread-safe writes with locking
  - Automatic index rebuild on corruption

- **Publisher API** (`aemp.publisher`)
  - `record_episode()`, `record_insight()`, `record_failure()` convenience methods
  - Automatic agent name injection

- **Subscriber API** (`aemp.subscriber`)
  - `recent()`, `from_agent()`, `from_others()` query methods
  - `episodes()`, `insights()`, `failures()` type-specific queries
  - `by_tags()`, `related_to()`, `search()` advanced queries

- **Compatibility layer** (`aemp.compat`)
  - `import_log_file()` — import from `partner_work_log.md` legacy format
  - `export_to_log_format()` — export Episode back to legacy format
  - `parse_log_line()` — parse individual log lines

- **CLI** (`aemp` command via entry point)
  - `recent`, `search`, `failures`, `insights`, `from`, `publish`, `status`, `import` subcommands

- **Bridge module** (`aemp_bridge.py`)
  - Pre-configured publishers for Qoder, XiaoMei, Hermes, Claude Code
  - Shared subscriber for cross-agent queries
  - `import_legacy_log()` convenience function

- **Examples** — `examples/demo.py` demonstrating full publish-subscribe workflow
- **Tests** — 25 tests covering schema, store, publisher, subscriber, and compat
- **Zero external dependencies** — pure Python 3.10+ stdlib only

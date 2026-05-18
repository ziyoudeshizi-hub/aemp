"""Compatibility layer for existing partner_work_log.md format.

Converts between the legacy log format and AEMP protocol entries,
allowing gradual migration without breaking existing workflows.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from aemp.schema import Episode, Outcome


# Legacy format: [YYYY-MM-DD HH:MM] [AI名称] [任务类型] [摘要]
_LOG_PATTERN = re.compile(
    r"\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\]\s*"
    r"\[([^\]]+)\]\s*"
    r"\[([^\]]+)\]\s*"
    r"\[?([^\]]*)\]?"
)


def parse_log_line(line: str) -> Episode | None:
    """Parse a single partner_work_log.md line into an Episode."""
    match = _LOG_PATTERN.match(line.strip())
    if not match:
        return None
    timestamp_str, agent, task_type, summary = match.groups()
    # Convert to ISO format
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
        dt = dt.replace(tzinfo=timezone.utc)
        iso_timestamp = dt.isoformat()
    except ValueError:
        iso_timestamp = timestamp_str

    return Episode(
        agent=agent.strip(),
        timestamp=iso_timestamp,
        summary=summary.strip() or task_type.strip(),
        action=task_type.strip(),
        result=summary.strip(),
        outcome=Outcome.SUCCESS,
        confidence=0.7,  # Legacy entries get moderate confidence
        tags=["legacy", "imported", task_type.strip().lower().replace(" ", "-")],
    )


def import_log_file(log_path: str | Path) -> list[Episode]:
    """Import an entire partner_work_log.md into Episode entries."""
    path = Path(log_path)
    if not path.exists():
        return []
    episodes = []
    for line in path.read_text(encoding="utf-8").splitlines():
        episode = parse_log_line(line)
        if episode:
            episodes.append(episode)
    return episodes


def export_to_log_format(entry: Episode) -> str:
    """Export an Episode back to the legacy log line format."""
    try:
        dt = datetime.fromisoformat(entry.timestamp)
        timestamp_str = dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        timestamp_str = entry.timestamp[:16]

    task_type = entry.action or "操作"
    summary = entry.summary or entry.result
    return f"[{timestamp_str}] [{entry.agent}] [{task_type}] [{summary}]"

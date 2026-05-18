"""Tests for AEMP - AI Episodic Memory Protocol."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aemp import (
    Episode,
    Failure,
    Insight,
    MemoryStore,
    MemoryType,
    Publisher,
    Subscriber,
)
from aemp.schema import Outcome, Relation
from aemp.compat import parse_log_line, export_to_log_format, import_log_file


# ============================================================
# Schema tests
# ============================================================


class TestMemoryEntry:
    def test_create_episode(self):
        ep = Episode(
            agent="Qoder",
            summary="Fixed a bug",
            action="Modified config.py",
            result="Bug resolved",
            outcome=Outcome.SUCCESS,
        )
        assert ep.type == MemoryType.EPISODE
        assert ep.agent == "Qoder"
        assert ep.confidence == 1.0
        assert not ep.is_expired()

    def test_episode_serialization(self):
        ep = Episode(
            agent="Hermes",
            summary="Search completed",
            action="Web search",
            result="Found 3 results",
            outcome=Outcome.SUCCESS,
            tags=["search", "web"],
            lessons=["Use specific queries"],
        )
        d = ep.to_dict()
        assert d["type"] == "episode"
        assert d["agent"] == "Hermes"
        assert d["lessons"] == ["Use specific queries"]

        restored = Episode.from_dict(d)
        assert restored.agent == "Hermes"
        assert restored.outcome == Outcome.SUCCESS
        assert restored.lessons == ["Use specific queries"]

    def test_insight_serialization(self):
        ins = Insight(
            agent="小美",
            summary="User prefers concise answers",
            pattern="Short responses get positive feedback",
            conditions="During work hours",
            confidence=0.85,
            evidence=["ep-001", "ep-002"],
        )
        d = ins.to_dict()
        assert d["type"] == "insight"
        assert d["pattern"] == "Short responses get positive feedback"

        restored = Insight.from_dict(d)
        assert restored.confidence == 0.85
        assert len(restored.evidence) == 2

    def test_failure_serialization(self):
        fail = Failure(
            agent="Claude Code",
            summary="Deployment failed",
            attempted="Deploy to production",
            expected="Successful deployment",
            actual="OOM error",
            root_cause="Memory limit too low",
            workaround="Increase memory to 4GB",
        )
        d = fail.to_dict()
        assert d["type"] == "failure"
        assert d["root_cause"] == "Memory limit too low"

        restored = Failure.from_dict(d)
        assert restored.workaround == "Increase memory to 4GB"

    def test_expiry(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        expired = Episode(agent="test", expires=past)
        assert expired.is_expired()

        active = Episode(agent="test", expires=future)
        assert not active.is_expired()

        no_expiry = Episode(agent="test")
        assert not no_expiry.is_expired()

    def test_relations(self):
        ep = Episode(
            agent="test",
            relations=Relation(
                caused_by="ep-000",
                supersedes=None,
                related_to=["ep-001", "ep-002"],
            ),
        )
        d = ep.to_dict()
        assert d["relations"]["caused_by"] == "ep-000"
        assert len(d["relations"]["related_to"]) == 2


# ============================================================
# Store tests
# ============================================================


class TestMemoryStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = MemoryStore(self.tmpdir)

    def test_publish_and_get(self):
        ep = Episode(agent="Qoder", summary="Test episode")
        entry_id = self.store.publish(ep)
        assert entry_id == ep.id

        retrieved = self.store.get(entry_id)
        assert retrieved is not None
        assert retrieved.summary == "Test episode"
        assert isinstance(retrieved, Episode)

    def test_count(self):
        assert self.store.count() == 0
        self.store.publish(Episode(agent="A", summary="1"))
        self.store.publish(Episode(agent="B", summary="2"))
        assert self.store.count() == 2

    def test_query_by_agent(self):
        self.store.publish(Episode(agent="Qoder", summary="A"))
        self.store.publish(Episode(agent="小美", summary="B"))
        self.store.publish(Episode(agent="Qoder", summary="C"))

        results = self.store.query(agent="Qoder")
        assert len(results) == 2
        assert all(r.agent == "Qoder" for r in results)

    def test_query_by_type(self):
        self.store.publish(Episode(agent="A", summary="ep"))
        self.store.publish(Insight(agent="A", summary="ins", pattern="p"))
        self.store.publish(Failure(agent="A", summary="fail", attempted="x", expected="y", actual="z"))

        episodes = self.store.query(memory_type=MemoryType.EPISODE)
        assert len(episodes) == 1

        insights = self.store.query(memory_type=MemoryType.INSIGHT)
        assert len(insights) == 1

        failures = self.store.query(memory_type=MemoryType.FAILURE)
        assert len(failures) == 1

    def test_query_by_tags(self):
        self.store.publish(Episode(agent="A", summary="1", tags=["web", "search"]))
        self.store.publish(Episode(agent="A", summary="2", tags=["code", "fix"]))
        self.store.publish(Episode(agent="A", summary="3", tags=["web", "api"]))

        results = self.store.query(tags=["web"])
        assert len(results) == 2

        results = self.store.query(tags=["fix"])
        assert len(results) == 1

    def test_query_by_confidence(self):
        self.store.publish(Episode(agent="A", summary="low", confidence=0.3))
        self.store.publish(Episode(agent="A", summary="high", confidence=0.9))

        results = self.store.query(min_confidence=0.5)
        assert len(results) == 1
        assert results[0].summary == "high"

    def test_query_excludes_expired(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.store.publish(Episode(agent="A", summary="expired", expires=past))
        self.store.publish(Episode(agent="A", summary="active"))

        results = self.store.query()
        assert len(results) == 1
        assert results[0].summary == "active"

        results = self.store.query(include_expired=True)
        assert len(results) == 2

    def test_forget(self):
        ep_id = self.store.publish(Episode(agent="A", summary="to forget"))
        assert self.store.count() == 1

        self.store.forget(ep_id)
        assert self.store.count() == 0  # Now expired

    def test_gc(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.store.publish(Episode(agent="A", summary="old", expires=past))
        self.store.publish(Episode(agent="A", summary="current"))

        removed = self.store.gc()
        assert removed == 1
        assert self.store.count() == 1

    def test_persistence(self):
        """Store survives re-instantiation."""
        self.store.publish(Episode(agent="A", summary="persisted"))
        entry_id = self.store.publish(Insight(agent="B", summary="insight", pattern="p"))

        # Create new store pointing to same path
        store2 = MemoryStore(self.tmpdir)
        assert store2.count() == 2
        retrieved = store2.get(entry_id)
        assert retrieved is not None
        assert isinstance(retrieved, Insight)


# ============================================================
# Publisher / Subscriber tests
# ============================================================


class TestPublisherSubscriber:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = MemoryStore(self.tmpdir)

    def test_publisher_episode(self):
        pub = Publisher(self.store, "Qoder")
        ep_id = pub.record_episode(
            summary="Fixed config",
            action="Edit config.json",
            result="Config valid",
            outcome=Outcome.SUCCESS,
            tags=["maintenance"],
        )
        entry = self.store.get(ep_id)
        assert entry is not None
        assert entry.agent == "Qoder"

    def test_publisher_failure(self):
        pub = Publisher(self.store, "Hermes")
        fail_id = pub.record_failure(
            summary="Search blocked",
            attempted="Scrape site",
            expected="HTML content",
            actual="403 Forbidden",
            root_cause="Bot detection",
            workaround="Use API instead",
            tags=["scraping"],
        )
        entry = self.store.get(fail_id)
        assert isinstance(entry, Failure)
        assert entry.workaround == "Use API instead"

    def test_subscriber_from_others(self):
        pub_a = Publisher(self.store, "Qoder")
        pub_b = Publisher(self.store, "小美")
        pub_a.record_episode(summary="A's work", action="a", result="a")
        pub_b.record_episode(summary="B's work", action="b", result="b")

        sub = Subscriber(self.store, "Qoder")
        others = sub.from_others()
        assert len(others) == 1
        assert others[0].agent == "小美"

    def test_subscriber_search(self):
        pub = Publisher(self.store, "Qoder")
        pub.record_episode(summary="Fixed Gateway timeout", action="edit", result="ok")
        pub.record_episode(summary="Updated README", action="edit", result="ok")

        sub = Subscriber(self.store)
        results = sub.search("Gateway")
        assert len(results) == 1
        assert "Gateway" in results[0].summary

    def test_subscriber_insights(self):
        pub = Publisher(self.store, "小美")
        pub.record_insight(
            summary="Pattern found",
            pattern="Users prefer short answers",
            confidence=0.9,
        )
        pub.record_insight(
            summary="Weak pattern",
            pattern="Maybe related",
            confidence=0.3,
        )

        sub = Subscriber(self.store)
        high = sub.insights(min_confidence=0.5)
        assert len(high) == 1
        assert high[0].confidence == 0.9


# ============================================================
# Compatibility tests
# ============================================================


class TestCompat:
    def test_parse_log_line(self):
        line = "[2026-03-17 14:30] [Qoder] [维护] [修复了Gateway启动问题]"
        ep = parse_log_line(line)
        assert ep is not None
        assert ep.agent == "Qoder"
        assert "Gateway" in ep.result
        assert "legacy" in ep.tags

    def test_parse_invalid_line(self):
        assert parse_log_line("just some random text") is None
        assert parse_log_line("") is None

    def test_export_roundtrip(self):
        ep = Episode(
            agent="Claude Code",
            timestamp="2026-05-15T10:00:00+00:00",
            action="代码审查",
            summary="审查了payment模块",
        )
        line = export_to_log_format(ep)
        assert "[Claude Code]" in line
        assert "[代码审查]" in line

    def test_import_log_file(self):
        import tempfile
        content = (
            "[2026-03-17 14:30] [Qoder] [维护] [修复Gateway]\n"
            "[2026-03-17 15:00] [小美] [聊天] [回复了用户问题]\n"
            "这行不是日志格式\n"
            "[2026-03-17 16:00] [Hermes] [搜索] [找到3篇论文]\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name

        episodes = import_log_file(path)
        assert len(episodes) == 3
        assert episodes[0].agent == "Qoder"
        assert episodes[2].agent == "Hermes"

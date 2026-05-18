"""AEMP CLI - 终端里直接操作 AI 共享记忆。

Usage:
    aemp recent                     # 最近记忆
    aemp search <keyword>           # 搜索
    aemp failures                   # 查看已知的坑
    aemp insights                   # 查看学到的规律
    aemp from <agent>               # 看某个 AI 的记忆
    aemp publish <agent> <summary>  # 快速记录一条 episode
    aemp status                     # 存储状态
    aemp import                     # 从 partner_work_log.md 导入
"""

import sys
from pathlib import Path

# Ensure aemp is importable
sys.path.insert(0, str(Path(__file__).parent))

from aemp import MemoryStore, Publisher, Subscriber
from aemp.schema import MemoryType, Outcome
from aemp.compat import import_log_file

STORE_PATH = Path(r"C:\Users\15397\.openclaw\workspace\memory\aemp_store")
LEGACY_LOG = Path(r"C:\Users\15397\.openclaw\workspace\memory\partner_work_log.md")


def get_store():
    return MemoryStore(STORE_PATH)


def cmd_recent(args):
    limit = int(args[0]) if args else 10
    store = get_store()
    sub = Subscriber(store)
    for m in sub.recent(limit=limit):
        conf = f"{m.confidence:.0%}" if m.confidence < 1.0 else ""
        print(f"  [{m.agent}] {m.summary} {conf}")


def cmd_search(args):
    if not args:
        print("Usage: aemp search <keyword>")
        return
    keyword = " ".join(args)
    store = get_store()
    sub = Subscriber(store)
    results = sub.search(keyword)
    if not results:
        print(f"  No results for '{keyword}'")
        return
    for m in results:
        print(f"  [{m.agent}] [{m.type.value}] {m.summary}")


def cmd_failures(args):
    store = get_store()
    sub = Subscriber(store)
    failures = sub.failures()
    if not failures:
        print("  No failure records.")
        return
    for f in failures:
        print(f"  [{f.agent}] {f.summary}")
        if f.workaround:
            print(f"    Workaround: {f.workaround}")


def cmd_insights(args):
    min_conf = float(args[0]) if args else 0.5
    store = get_store()
    sub = Subscriber(store)
    insights = sub.insights(min_confidence=min_conf)
    if not insights:
        print(f"  No insights above {min_conf:.0%} confidence.")
        return
    for i in insights:
        print(f"  [{i.agent}] {i.pattern} ({i.confidence:.0%})")
        if i.conditions:
            print(f"    When: {i.conditions}")


def cmd_from(args):
    if not args:
        print("Usage: aemp from <agent_name>")
        return
    agent = args[0]
    limit = int(args[1]) if len(args) > 1 else 10
    store = get_store()
    sub = Subscriber(store)
    results = sub.from_agent(agent, limit=limit)
    if not results:
        print(f"  No memories from '{agent}'")
        return
    for m in results:
        print(f"  [{m.type.value}] {m.summary}")


def cmd_publish(args):
    if len(args) < 2:
        print("Usage: aemp publish <agent> <summary> [tags...]")
        return
    agent = args[0]
    summary = args[1]
    tags = args[2:] if len(args) > 2 else []
    store = get_store()
    pub = Publisher(store, agent)
    entry_id = pub.record_episode(
        summary=summary,
        action="CLI record",
        result=summary,
        outcome=Outcome.SUCCESS,
        tags=tags,
    )
    print(f"  Published: {entry_id[:8]}... [{agent}] {summary}")


def cmd_status(args):
    store = get_store()
    print(f"  Store: {STORE_PATH}")
    print(f"  Total memories: {store.count()}")
    print(f"  Store exists: {STORE_PATH.exists()}")


def cmd_import(args):
    log_path = Path(args[0]) if args else LEGACY_LOG
    episodes = import_log_file(log_path)
    if not episodes:
        print(f"  No entries found in {log_path}")
        return
    store = get_store()
    count = 0
    for ep in episodes:
        store.publish(ep)
        count += 1
    print(f"  Imported {count} entries from {log_path.name}")


def main():
    if len(sys.argv) < 2:
        print("AEMP - AI Episodic Memory Protocol CLI")
        print()
        print("Commands:")
        print("  aemp recent [n]              Show recent n memories (default 10)")
        print("  aemp search <keyword>        Search memories by keyword")
        print("  aemp failures                Show known failure records")
        print("  aemp insights [min_conf]     Show insights (default >50%)")
        print("  aemp from <agent> [n]        Show memories from specific agent")
        print("  aemp publish <agent> <text>  Record a quick episode")
        print("  aemp status                  Show store status")
        print("  aemp import [path]           Import from partner_work_log.md")
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "recent": cmd_recent,
        "search": cmd_search,
        "failures": cmd_failures,
        "insights": cmd_insights,
        "from": cmd_from,
        "publish": cmd_publish,
        "status": cmd_status,
        "import": cmd_import,
    }

    if cmd in commands:
        commands[cmd](args)
    else:
        print(f"  Unknown command: {cmd}")
        print(f"  Available: {', '.join(commands.keys())}")


if __name__ == "__main__":
    main()

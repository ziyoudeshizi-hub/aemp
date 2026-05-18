"""AEMP usage example - demonstrates the full protocol workflow."""

from pathlib import Path
from aemp import MemoryStore, Publisher, Subscriber
from aemp.schema import Outcome
from aemp.compat import import_log_file, export_to_log_format


def main():
    # Initialize store (creates directory if needed)
    store = MemoryStore(Path("./demo_memories"))

    # -- Publisher side: AI agent records memories --
    qoder = Publisher(store, agent_name="Qoder")
    xiaomei = Publisher(store, agent_name="小美")
    hermes = Publisher(store, agent_name="Hermes")

    # Qoder records a maintenance episode
    ep1 = qoder.record_episode(
        summary="修复了 Gateway 启动超时问题",
        action="修改 gateway-silent.vbs 的超时参数",
        result="Gateway 现在 5 秒内稳定启动",
        outcome=Outcome.SUCCESS,
        tags=["maintenance", "gateway"],
        lessons=["VBS 的 WScript.Sleep 单位是毫秒不是秒"],
    )

    # Hermes records a failure
    hermes.record_failure(
        summary="尝试用 Selenium 抓取某站数据失败",
        attempted="使用 headless Chrome 抓取动态页面",
        expected="获取完整页面 HTML",
        actual="Cloudflare 验证拦截，返回 403",
        root_cause="该站启用了 bot 检测",
        workaround="改用官方 API 或手动获取",
        tags=["web-scraping", "blocked"],
    )

    # 小美 records an insight learned from multiple interactions
    xiaomei.record_insight(
        summary="毛毛周一到周三比较忙，不宜安排长任务",
        pattern="工作日前半周消息回复延迟增大",
        conditions="仅适用于非假期的周一至周三",
        confidence=0.75,
        tags=["schedule", "user-pattern"],
        evidence=[ep1],  # Related episode IDs
        expires="2026-12-31T23:59:59+08:00",  # Insight may change
    )

    # Qoder records an insight from the gateway fix
    qoder.record_insight(
        summary="VBS 启动脚本修改后必须重启计划任务才生效",
        pattern="Windows 计划任务缓存了 VBS 脚本的旧版本",
        conditions="仅当通过计划任务触发 VBS 时",
        confidence=0.9,
        tags=["windows", "vbs", "scheduled-tasks"],
        evidence=[ep1],
    )

    print(f"Published {store.count()} memories\n")

    # -- Subscriber side: Another AI queries shared memories --
    claude_sub = Subscriber(store, agent_name="Claude Code")

    # Get recent memories from all agents
    print("=== Recent memories (all agents) ===")
    for mem in claude_sub.recent(limit=5):
        print(f"  [{mem.agent}] {mem.summary} (confidence: {mem.confidence})")

    # Get only failures (to avoid repeating mistakes)
    print("\n=== Known failures ===")
    for fail in claude_sub.failures():
        print(f"  [{fail.agent}] {fail.summary}")
        print(f"    Workaround: {fail.workaround}")

    # Get high-confidence insights
    print("\n=== Insights (confidence >= 0.8) ===")
    for insight in claude_sub.insights(min_confidence=0.8):
        print(f"  [{insight.agent}] {insight.pattern}")
        print(f"    Conditions: {insight.conditions}")

    # Search by keyword
    print("\n=== Search 'Gateway' ===")
    for mem in claude_sub.search("Gateway"):
        print(f"  [{mem.agent}] {mem.summary}")

    # -- Compatibility: export back to legacy format --
    print("\n=== Legacy format export ===")
    for ep in claude_sub.episodes():
        print(f"  {export_to_log_format(ep)}")


if __name__ == "__main__":
    main()

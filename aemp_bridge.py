"""AEMP Bridge - 即插即用的四 AI 协作记忆桥接。

使用方式（任何 AI 脚本中）:
    from aemp_bridge import qoder, xiaomei, hermes, claude_code, shared

    # 记录经验
    qoder.record_episode(summary="修了Gateway", action="改VBS", result="好了")
    xiaomei.record_insight(summary="毛毛不喜欢长消息", pattern="...", confidence=0.8)
    hermes.record_failure(summary="爬虫被拦", attempted="...", expected="...", actual="...")

    # 查询共享记忆
    shared.failures()                    # 所有已知的坑
    shared.insights(min_confidence=0.7)  # 高置信度经验
    shared.from_others()                 # 看别人做了什么
    shared.search("Gateway")             # 关键词搜索

    # 从旧日志导入历史记录（只需执行一次）
    from aemp_bridge import import_legacy_log
    import_legacy_log()
"""

from pathlib import Path

from aemp import MemoryStore, Publisher, Subscriber
from aemp.compat import import_log_file

# ============================================================
# 路径配置
# ============================================================

# 共享记忆存储目录（所有 AI 共用）
MEMORY_STORE_PATH = Path(r"C:\Users\15397\.openclaw\workspace\memory\aemp_store")

# 旧版工作日志（兼容导入用）
LEGACY_LOG_PATH = Path(
    r"C:\Users\15397\.openclaw\workspace\memory\partner_work_log.md"
)

# ============================================================
# 初始化
# ============================================================

store = MemoryStore(MEMORY_STORE_PATH)

# 四个 AI 各自的 Publisher
qoder = Publisher(store, agent_name="Qoder")
xiaomei = Publisher(store, agent_name="小美")
hermes = Publisher(store, agent_name="Hermes")
claude_code = Publisher(store, agent_name="Claude Code")

# 通用 Subscriber（不绑定身份，看全部）
shared = Subscriber(store)


def get_subscriber(agent_name: str) -> Subscriber:
    """获取绑定特定 AI 身份的 Subscriber（可用 from_others 过滤自己）。"""
    return Subscriber(store, agent_name=agent_name)


# ============================================================
# 旧日志导入
# ============================================================


def import_legacy_log(log_path: Path | str | None = None) -> int:
    """从 partner_work_log.md 导入历史记录到 AEMP。

    Returns:
        导入的记录数量。
    """
    path = Path(log_path) if log_path else LEGACY_LOG_PATH
    episodes = import_log_file(path)
    count = 0
    for ep in episodes:
        store.publish(ep)
        count += 1
    return count


# ============================================================
# 便捷函数
# ============================================================


def status() -> dict:
    """查看 AEMP 存储状态。"""
    return {
        "store_path": str(MEMORY_STORE_PATH),
        "total_memories": store.count(),
        "store_exists": MEMORY_STORE_PATH.exists(),
    }


if __name__ == "__main__":
    print("AEMP Bridge Status:")
    s = status()
    for k, v in s.items():
        print(f"  {k}: {v}")

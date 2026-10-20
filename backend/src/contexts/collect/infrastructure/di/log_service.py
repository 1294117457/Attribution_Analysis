"""log_service — CollectLogService DI 工厂

step9 重构（2026-10-20）：Redis 全局单例
    - 移除 redis=Depends(get_redis) 参数
    - CollectLogService 自接全局 redis_client（直接 import）

Phase 2 重构（2026-10-19）：日志子系统独立闭环
step8 修正（2026-10-20）：移除 session Depends
    - CollectLogService 自管 attribution 库短事务，不再需要外部注入 session
"""
from __future__ import annotations

from contexts.collect.application.service.manage import CollectLogService


def get_collect_log_service() -> CollectLogService:
    """注入 CollectLogService 依赖

    使用场景：
        1. route/log.py 注入：用于查询
        2. 采集接口 service 注入：用于 create_pending / mark_failed

    ★ 不接 session：日志表在 attribution 库，CollectLogService 每次
      DB 操作自开独立短事务，与请求生命周期解耦。
    ★ 不接 redis：Redis 走全局单例（internal import，详见 CollectLogService）。
    """
    return CollectLogService()


__all__ = ["get_collect_log_service"]

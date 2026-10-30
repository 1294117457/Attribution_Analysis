"""后台采集任务包：建任务立即返回，后台按天循环调现有 service.collect()。

设计约束（最小闭环，不碰 schedule）：
  - 28 个 collector 的 collect(params) 一行不动，复用现有入库/限流逻辑
  - 进度放 Redis Hash（collect:task:{id}），Java 不引入 Redis 客户端，只透传
  - 任务注册表 TASKS 仅进程内持有 asyncio.Task（单 worker 部署，见 Dockerfile）
"""
from tasks.manager import create_task, get_task_state, recover_stale_tasks
from tasks.router import router

__all__ = ["create_task", "get_task_state", "recover_stale_tasks", "router"]

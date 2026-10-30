"""后台任务 HTTP 层：建任务 / 查进度 / 查最近 / 中断。

挂在 /api/collect/tasks 下，与同步采集入口互不冲突。
前端现有 runService 保持不动（仍调同步入口做“单次小采集”）；
新前端走“大数据量/长时间范围”采集时调本组接口。

规范见 backend-java/docs/开发文档/采集模块/采集模块现状文档（三类采集：增量-全量覆盖-实时查询）.md §3 / §5.2
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api import response as R
from core.config import get_settings
from core.errors import CollectorNotFound, InvalidParams
from core.redis import get_redis
from tasks.manager import TASK_LIST_KEY, cancel_task, create_task, get_task_state

router = APIRouter(prefix=f"{get_settings().API_V1_PREFIX}/collect/tasks", tags=["采集任务"])


class TaskBody(BaseModel):
    """建任务请求体。

    ★ 新契约字段：strategy（incremental / full）
    ⚠️ mode 为旧前端兼容字段（condition / full），由 manager 统一映射到 strategy
    """

    strategy: str = ""
    mode: str = ""
    params: dict = Field(default_factory=dict)
    trigger_source: str = "manual"
    parent_task_id: str | None = None

    def resolved_strategy(self) -> str:
        """取有效的采集方式：优先 strategy，其次旧 mode，最后空串（collector 按 service 声明兜底）。"""
        if self.strategy and self.strategy.strip():
            return self.strategy.strip()
        if self.mode and self.mode.strip():
            return self.mode.strip()
        return ""


@router.post("/{task_id}/cancel", summary="中断采集任务")
async def cancel_collect_task(task_id: str):
    """请求中断任务。

    ⚠️ 路由声明顺序很重要：FastAPI 按声明顺序匹配。
    本路由必须声明在 POST /{facet}/{name} 之前——
    否则 POST /{task_id}/cancel 会被 /{facet}/{name} 抢先匹配（facet=task_id, name=cancel）。
    """
    ok = await cancel_task(task_id)
    if not ok:
        # 用 R.err 而非 HTTPException：统一 {code, message, data} 信封，
        # 前端 unwrap() 按 code>=400 判错，HTTPException 的 {detail:...} 没有 code 字段 → 会被当成成功。
        return R.err(f"任务 {task_id!r} 不存在或已结束", 404)
    return R.ok({"task_id": task_id, "status": "cancelling"})


@router.post("/{facet}/{name}", summary="创建后台采集任务（立即返回 task_id）")
async def create_collect_task(facet: str, name: str, body: TaskBody):
    try:
        return R.ok(await create_task(
            facet, name, body.resolved_strategy(), body.params,
            trigger_source=body.trigger_source or "manual",
            parent_task_id=body.parent_task_id,
        ))
    except CollectorNotFound as e:
        return R.err(e.message, 404)
    except InvalidParams as e:
        return R.err(str(e), 400)


@router.get("", summary="最近任务列表")
async def list_collect_tasks(limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(limit, 100))
    redis = await get_redis()
    ids = await redis.lrange(TASK_LIST_KEY, 0, limit - 1)
    items: list[dict[str, Any]] = []
    for tid in ids or []:
        state = await get_task_state(str(tid))
        if state:
            items.append(state)
    return R.ok({"total": len(items), "list": items})


@router.get("/{task_id}", summary="任务进度")
async def get_collect_task(task_id: str):
    state = await get_task_state(task_id)
    if state is None:
        return R.err(f"任务 {task_id!r} 不存在或已过期", 404)
    return R.ok(state)


__all__ = ["router"]

"""采集 HTTP 层：目录 + 实时查询（同步入口已下线，全异步）。

  GET  /api/collect/services        全部 collector 元数据（前端左侧树）
  GET  /api/collect/query/{name}    实时查询（调 service.get()）
  POST /api/collect/tasks/{f}/{n}   采集建任务（见 tasks/router.py，唯一写库入口）
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api import response as R
from collectors import BY_NAME
from core.config import get_settings
from core.errors import CollectorNotFound, InvalidParams

router = APIRouter(prefix=f"{get_settings().API_V1_PREFIX}/collect", tags=["采集"])


class CollectBody(BaseModel):
    """兼容旧同步入口的请求体：现转调任务，立即返回 task_id。"""

    # ★ 新契约：采集方式（incremental / full）
    strategy: str = ""
    # ⚠️ 旧前端兼容字段（condition / full），由 manager 统一映射到 strategy
    mode: str = ""
    params: dict = Field(default_factory=dict)

    def resolved_strategy(self) -> str:
        """取有效的采集方式：优先 strategy，其次旧 mode，最后空串（交给 collector 按 service 声明兜底）。"""
        if self.strategy and self.strategy.strip():
            return self.strategy.strip()
        if self.mode and self.mode.strip():
            return self.mode.strip()
        return ""


@router.post("/{facet}/{name}", summary="兼容马甲：转调后台任务（原同步 collect 已下线）",
             deprecated=True)
async def collect_trigger(facet: str, name: str, body: CollectBody):
    from tasks.manager import create_task

    try:
        return R.ok(
            await create_task(facet, name, body.resolved_strategy(), body.params),
            message="已转为后台任务",
        )
    except CollectorNotFound as e:
        return R.err(e.message, 404)
    except InvalidParams as e:
        return R.err(str(e), 400)


def _build_catalog() -> list[dict[str, Any]]:
    api_prefix = get_settings().API_V1_PREFIX
    items: list[dict[str, Any]] = []
    for name, cls in BY_NAME.items():
        # ★ 目录可见性读 service 的类属性 hidden（不再用硬编码白名单）
        if getattr(cls, "hidden", False):
            continue
        facet = getattr(cls, "facet", "") or ""
        has_get = callable(getattr(cls, "get", None))
        # ★ strategy 直接读类属性（必须显式声明，禁止运行时启发式推断）
        strategy = getattr(cls, "strategy", "") or "incremental"
        # ★ queryable = 是否有实时直查入口（与 strategy 正交，替代旧 kind='both'）
        queryable = bool(getattr(cls, "QUERYABLE", has_get))
        # ★ 增量维度（仅 incremental 有）
        range_meta = getattr(cls, "RANGE", None) if strategy == "incremental" else None
        # ★ 全量覆盖的清理模式
        clear_mode = getattr(cls, "CLEAR_MODE", "none") or "none"
        # ★ 实际的「步」粒度（前端据此显示进度提示）
        #   trade_day → 区间被拆成 N 个交易日，每步一天（进度分母 = 交易日数）
        #   day       → 区间自理，service 内部处理（进度分母 = 1）
        #   ⚠️ 有些 service 声明 granularity='day' 但实现了 expand_calls 钩子
        #      （如 daily_kline）→ 实际也是按天拆步，这里显式区分。
        step_granularity = range_meta.get("granularity", "day") if range_meta else None
        if step_granularity == "day" and callable(getattr(cls, "expand_calls", None)):
            step_granularity = "trade_day"
        items.append({
            # ── 身份 ──────────────────────────────
            "name": name,                                # ★ 日志关联键（collect_logs.name）
            "facet": facet,                              # ★ 五数据面（唯一分组维度）
            "label": getattr(cls, "label", "") or name,   # ★ 中文显示名
            "description": getattr(cls, "description", ""),
            # ── 采集语义 ──────────────────────────
            "strategy": strategy,
            "queryable": queryable,
            "range": range_meta,
            "clear_mode": clear_mode,
            "step_granularity": step_granularity,
            # ── 运行时 ────────────────────────────
            "rate_limit": getattr(cls, "RATE_LIMIT", None),
            "concurrency": int(getattr(cls, "CONCURRENCY", 1) or 1),
            # ── 路径 ──────────────────────────────
            "path": f"{api_prefix}/collect/tasks/{facet}/{name}",
            "query_path": f"{api_prefix}/collect/query/{name}" if queryable else None,
        })
    items.sort(key=lambda x: (x["facet"], x["name"]))
    return items


_CATALOG = _build_catalog()


@router.get("/services", summary="全部 collector 元数据（前端左侧树）")
async def list_services() -> dict[str, Any]:
    # 与后端 Java 侧 PageResult 口径一致：total / list / page / page_size
    return R.ok(
        {
            "total": len(_CATALOG),
            "list": _CATALOG,
            "page": 1,
            "page_size": len(_CATALOG),
        }
    )


@router.get("/query/{name}", summary="实时查询 service.get()，params 传 JSON 串")
async def query_service(name: str, params: str = ""):
    cls = BY_NAME.get(name)
    if cls is None:
        return R.err(f"service {name!r} 不存在", 404)
    if not callable(getattr(cls, "get", None)):
        return R.err(f"service {name!r} 不支持实时查询", 400)
    if params.strip():
        try:
            kwargs = json.loads(params)
        except json.JSONDecodeError as e:
            return R.err(f"params 不是合法 JSON: {e}", 400)
        if not isinstance(kwargs, dict):
            return R.err("params 必须是 JSON object", 400)
    else:
        kwargs = {}
    try:
        return R.ok(await cls().get(**kwargs))
    except TypeError as e:
        return R.err(f"参数错误: {e}", 400)


__all__ = ["router"]

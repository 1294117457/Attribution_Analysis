"""采集任务管理 API（业务模块：collect-manage/）

router 仅负责 HTTP 协议：创建任务 / 方案 / 任务组走 CollectManageService，
采集逻辑在 `infrastructure.adapter.scheduler.collect.*` 子类中实现。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from application.service import (
    CollectManageService,
    PlanNotFound,
    TaskConflict,
    UnknownTaskType,
    task_to_dict,
)
from infrastructure.adapter.cache.redis_client import get_redis
from infrastructure.adapter.realtime import RealtimeQueryError, get_realtime_query_framework
from infrastructure.adapter.scheduler.collect import (
    get_collect_task_registry,
    request_cancel,
)
from infrastructure.config.di import get_collect_manage_service, get_db
from infrastructure.persistence.models.sys_collect_task import SysCollectTaskDB
from route.api import _response as R
from route.dto.request.collect import CollectPlanSaveRequest
from route.dto.response.collect import (
    CollectCatalogResponse,
    FacetGroupResponse,
    TaskDefResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["采集任务"])


# ═══════════════════════════════════════════════════════════════════════════════
# GET /collect/catalog — 采集任务目录树
#   ⚠️ 必须放在 /collect/tasks/{task_id}/* 之前注册（fastapi 按声明顺序匹配）
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/catalog", summary="采集任务目录树（四面分类）")
async def get_collect_catalog():
    """拉取采集任务目录树

    返回按 facet（5 大面）→ sub_facet 二级聚合的目录结构。
    前端 CollectManage.vue 启动时调用一次，作为左树渲染依据。
    """
    registry = get_collect_task_registry()
    groups = registry.catalog()
    catalog = CollectCatalogResponse(
        items=[
            FacetGroupResponse(
                facet=g.facet, label=g.label, icon=g.icon, sort_order=g.sort_order,
                sub_groups={
                    sub_key: [TaskDefResponse(**td.__dict__) for td in tasks]
                    for sub_key, tasks in g.sub_groups.items()
                },
            )
            for g in groups
        ],
    )
    return R.ok(catalog.model_dump())


# ═══════════════════════════════════════════════════════════════════════════════
# 实时接口 /collect/realtime
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/realtime/{name}/query", summary="调用实时接口（试查 / 通用入口）")
async def query_realtime(name: str, body: Optional[dict] = None):
    svc = get_realtime_query_framework()
    try:
        res = await svc.query(name, body or {})
    except KeyError as e:
        return R.err(str(e), 404)
    except ValueError as e:
        return R.err(str(e), 400)
    except RealtimeQueryError as e:
        return R.err(str(e), 502)
    return R.ok(res.to_dict())


@router.get("/realtime/{name}/stats", summary="实时接口调用统计（按天）")
async def realtime_stats(name: str, days: int = Query(1, ge=1, le=7)):
    try:
        return R.ok(await get_realtime_query_framework().stats(name, days))
    except KeyError as e:
        return R.err(str(e), 404)


# ═══════════════════════════════════════════════════════════════════════════════
# POST /collect/tasks — 创建并启动采集任务
# ═══════════════════════════════════════════════════════════════════════════════


async def _submit(
    task_type: Optional[str], params: Optional[dict],
    svc: CollectManageService,
) -> dict:
    """冲突 / 不支持的类型沿用旧契约：200 + data.message（无 task_id）"""
    try:
        sub = await svc.submit(task_type, params, trigger="manual")
    except (UnknownTaskType, TaskConflict) as e:
        return R.ok({"message": str(e)})
    return R.ok({
        "task_id": sub.task_id,
        "task_type": sub.task_type,
        "total_count": sub.total_count,
        "message": f"已启动 {sub.task_type} 采集任务，共 {sub.total_count} 个单元",
    })


@router.post("/tasks", summary="创建采集任务")
async def create_task(
    body: dict,
    svc: CollectManageService = Depends(get_collect_manage_service),
):
    """params 与采集方案 params、default_params 合并（传入的优先）"""
    return await _submit(body.get("task_type"), body.get("params") or {}, svc)


# ═══════════════════════════════════════════════════════════════════════════════
# 采集方案 /collect/plans
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/fetchers", summary="采集接口元数据列表（方案编排的接口选择器数据源）")
async def list_fetchers(svc: CollectManageService = Depends(get_collect_manage_service)):
    return R.ok(await svc.list_fetchers())


# ── 采集方案 /collect/plans ────────────────────────────────────────────


@router.get("/plans", summary="采集方案列表")
async def list_plans(svc: CollectManageService = Depends(get_collect_manage_service)):
    return R.ok(await svc.list_plans())


@router.get("/plans/{plan_id}", summary="采集方案详情")
async def get_plan(
    plan_id: int,
    svc: CollectManageService = Depends(get_collect_manage_service),
):
    try:
        return R.ok(await svc.get_plan(plan_id))
    except ValueError as e:
        return R.err(str(e), 404)


@router.post("/plans", summary="新建采集方案（同步刷新定时 job）")
async def create_plan(
    body: CollectPlanSaveRequest,
    svc: CollectManageService = Depends(get_collect_manage_service),
):
    try:
        return R.ok(await svc.create_plan(body.model_dump()))
    except ValueError as e:
        return R.err(str(e), 400)


@router.put("/plans/{plan_id}", summary="更新采集方案（同步刷新定时 job）")
async def update_plan(
    plan_id: int, body: CollectPlanSaveRequest,
    svc: CollectManageService = Depends(get_collect_manage_service),
):
    try:
        return R.ok(await svc.update_plan(plan_id, body.model_dump()))
    except PlanNotFound as e:
        return R.err(str(e), 404)
    except ValueError as e:
        return R.err(str(e), 400)


@router.delete("/plans/{plan_id}", summary="删除采集方案（方案项一并删除）")
async def delete_plan(
    plan_id: int,
    svc: CollectManageService = Depends(get_collect_manage_service),
):
    try:
        await svc.delete_plan(plan_id)
    except PlanNotFound as e:
        return R.err(str(e), 404)
    return R.no_content("已删除")


@router.post("/plans/{plan_id}/run", summary="立即执行一次采集方案")
async def run_plan(
    plan_id: int,
    svc: CollectManageService = Depends(get_collect_manage_service),
):
    try:
        info = await svc.start_plan(plan_id, trigger="manual")
    except ValueError as e:
        return R.err(str(e), 400)
    return R.ok({
        **info,
        "message": f"已启动采集方案「{info['name']}」，共 {len(info['items'])} 项",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# GET /collect/tasks — 任务列表
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/tasks", summary="查询任务列表")
async def list_tasks(
    task_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    plan_run_id: Optional[int] = Query(None, description="只看某次采集方案执行的各项"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SysCollectTaskDB)
    count_stmt = select(func.count()).select_from(SysCollectTaskDB)
    if task_type:
        stmt = stmt.where(SysCollectTaskDB.task_type == task_type)
        count_stmt = count_stmt.where(SysCollectTaskDB.task_type == task_type)
    if status:
        stmt = stmt.where(SysCollectTaskDB.status == status)
        count_stmt = count_stmt.where(SysCollectTaskDB.status == status)
    if plan_run_id is not None:
        stmt = stmt.where(SysCollectTaskDB.plan_run_id == plan_run_id)
        count_stmt = count_stmt.where(SysCollectTaskDB.plan_run_id == plan_run_id)
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        (await db.execute(
            stmt.order_by(desc(SysCollectTaskDB.id))
            .limit(page_size).offset((page - 1) * page_size)
        )).scalars().all()
    )
    return R.ok({
        "total": total, "page": page, "page_size": page_size,
        "items": [task_to_dict(t) for t in rows],
    })


@router.get("/tasks/{task_id}", summary="查询任务详情")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(SysCollectTaskDB, task_id)
    if not task:
        return R.ok({"message": "任务不存在"})
    return R.ok(task_to_dict(task))


@router.get("/tasks/{task_id}/progress", summary="查询实时进度")
async def get_task_progress(task_id: int):
    redis = await get_redis()
    data = await redis.hgetall(f"collect:progress:{task_id}")
    if not data:
        return R.ok({"status": "unknown", "message": "无进度信息（任务可能已过期）"})
    total = int(data.get("total", 0))
    done = int(data.get("done", 0))
    return R.ok({
        "total": total, "done": done,
        "success": int(data.get("success", 0)),
        "fail": int(data.get("fail", 0)),
        "skip": int(data.get("skip", 0)),
        "status": data.get("status", "unknown"),
        "current": data.get("current", ""),
        "percent": round(done / total * 100, 1) if total > 0 else 0,
    })


@router.post("/tasks/{task_id}/cancel", summary="取消任务")
async def cancel_task(
    task_id: int,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(SysCollectTaskDB, task_id)
    if not task:
        return R.ok({"message": "任务不存在"})
    if task.status not in ("running", "pending"):
        return R.ok({"message": f"任务状态为 {task.status}，无需取消"})

    request_cancel(task_id)

    if force:
        task.status = "cancelled"
        task.finished_at = datetime.now()
        if task.started_at:
            task.duration_ms = int(
                (task.finished_at - task.started_at).total_seconds() * 1000
            )
        task.message = f"强制取消 (成功{task.success_count} 失败{task.fail_count})"
        await db.commit()

        redis = await get_redis()
        await redis.hset(f"collect:progress:{task_id}", "status", "cancelled")
        logger.info("任务 %d 被强制取消", task_id)
        return R.ok({"message": "任务已强制取消", "forced": True})

    return R.ok({"message": "已发送取消信号（如任务已挂起，请使用强制取消）"})


@router.post("/tasks/{task_id}/retry", summary="重跑失败任务")
async def retry_failed_task(
    task_id: int,
    svc: CollectManageService = Depends(get_collect_manage_service),
):
    """重跑一个失败 / 已取消的任务：保留原 task_type 与 params，新开 task_id"""
    try:
        sub = await svc.retry_failed(task_id)
    except ValueError as e:
        return R.ok({"message": str(e)})
    return R.ok({
        "task_id": sub.task_id,
        "task_type": sub.task_type,
        "total_count": sub.total_count,
        "message": f"已重跑（来自 #{task_id}），共 {sub.total_count} 个单元",
    })

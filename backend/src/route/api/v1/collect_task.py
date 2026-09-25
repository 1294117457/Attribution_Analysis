"""采集任务管理 API

重构后：router 仅负责 HTTP 协议，所有业务逻辑在
`infrastructure.tasks.collect.*` 子类中实现。

配套设计文档：
  docs/dev/07collect-class/01-collect-task-class-design.md
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.sys_collect_task import SysCollectTaskDB
from infrastructure.redis import get_redis
from infrastructure.tasks.collect import (
    execute_task,
    get_collect_task_registry,
    request_cancel,
)
from route.schemas import response as R

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["采集任务"])


# ═══════════════════════════════════════════════════════════════════════════════
# POST /collect/tasks — 创建并启动采集任务
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/tasks", summary="创建采集任务")
async def create_task(
    body: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task_type = body.get("task_type")
    params = body.get("params", {}) or {}

    # 从 registry 取 handler（白名单不再硬编码）
    registry = get_collect_task_registry()
    handler = registry.get(task_type)
    if handler is None:
        return R.ok({
            "message": (
                f"不支持的任务类型: {task_type}，"
                f"已支持: {registry.supported_types()}"
            )
        })

    # 防重：同 task_type 已有 running 任务则拒绝
    running = await db.execute(
        select(SysCollectTaskDB).where(
            SysCollectTaskDB.task_type == task_type,
            SysCollectTaskDB.status == "running",
        )
    )
    if running.scalars().first():
        return R.ok({
            "message": f"{task_type} 已有运行中的任务，请等待完成",
        })

    # 估单元数（子类实现，可能走 DB / AKShare 等）
    total = await handler.estimate_total(params)

    # 写 sys_collect_tasks 行
    task = SysCollectTaskDB(
        task_type=task_type,
        trigger_type="manual",
        params=params,
        status="running",
        total_count=total,
        started_at=datetime.now(),
    )
    db.add(task)
    await db.commit()
    task_id = task.id

    # 写 Redis 初始进度（前端轮询的契约，hash 字段保持不变）
    redis = await get_redis()
    await redis.hset(
        f"collect:progress:{task_id}",
        mapping={
            "total": str(total),
            "done": "0",
            "success": "0",
            "fail": "0",
            "skip": "0",
            "status": "running",
            "current": "",
        },
    )
    await redis.expire(f"collect:progress:{task_id}", 86400)

    # 启动后台任务（模板方法 execute_task 接管进度/取消/收尾）
    background_tasks.add_task(execute_task, task_id, handler, params)

    logger.info("创建采集任务: id=%d, type=%s, total=%d", task_id, task_type, total)
    return R.ok({
        "task_id": task_id,
        "task_type": task_type,
        "total_count": total,
        "message": f"已启动 {task_type} 采集任务，共 {total} 个单元",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# GET /collect/tasks — 任务列表
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/tasks", summary="查询任务列表")
async def list_tasks(
    task_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
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

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(desc(SysCollectTaskDB.id))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()

    return R.ok({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_task_to_dict(t) for t in rows],
    })


# ═══════════════════════════════════════════════════════════════════════════════
# GET /collect/tasks/{id} — 任务详情
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/tasks/{task_id}", summary="查询任务详情")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(SysCollectTaskDB, task_id)
    if not task:
        return R.ok({"message": "任务不存在"})
    return R.ok(_task_to_dict(task))


# ═══════════════════════════════════════════════════════════════════════════════
# GET /collect/tasks/{id}/progress — 实时进度（Redis HGETALL）
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/tasks/{task_id}/progress", summary="查询实时进度")
async def get_task_progress(task_id: int):
    redis = await get_redis()
    data = await redis.hgetall(f"collect:progress:{task_id}")
    if not data:
        return R.ok({
            "status": "unknown",
            "message": "无进度信息（任务可能已过期）",
        })
    total = int(data.get("total", 0))
    done = int(data.get("done", 0))
    return R.ok({
        "total": total,
        "done": done,
        "success": int(data.get("success", 0)),
        "fail": int(data.get("fail", 0)),
        "skip": int(data.get("skip", 0)),
        "status": data.get("status", "unknown"),
        "current": data.get("current", ""),
        "percent": round(done / total * 100, 1) if total > 0 else 0,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# POST /collect/tasks/{id}/cancel — 取消任务
# ═══════════════════════════════════════════════════════════════════════════════


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

    # 写入取消标志（子类 run() 内的 is_cancelled() 会读到）
    request_cancel(task_id)

    if force:
        # 强制取消：直接改 DB 行 + Redis status
        task.status = "cancelled"
        task.finished_at = datetime.now()
        if task.started_at:
            task.duration_ms = int(
                (task.finished_at - task.started_at).total_seconds() * 1000
            )
        task.message = (
            f"强制取消 (成功{task.success_count} 失败{task.fail_count})"
        )
        await db.commit()

        redis = await get_redis()
        await redis.hset(f"collect:progress:{task_id}", "status", "cancelled")
        logger.info("任务 %d 被强制取消", task_id)
        return R.ok({"message": "任务已强制取消", "forced": True})

    return R.ok({
        "message": "已发送取消信号（如任务已挂起，请使用强制取消）",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _task_to_dict(t: SysCollectTaskDB) -> dict:
    """SysCollectTaskDB → 响应 dict（前端字段契约，保持不变）"""
    return {
        "id": t.id,
        "task_type": t.task_type,
        "trigger_type": t.trigger_type,
        "params": t.params,
        "status": t.status,
        "total_count": t.total_count,
        "success_count": t.success_count,
        "fail_count": t.fail_count,
        "skip_count": t.skip_count,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        "duration_ms": t.duration_ms,
        "message": t.message,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }

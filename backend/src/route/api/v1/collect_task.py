"""采集任务管理 API"""
import asyncio
import logging
import time
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from application.kline_service import KlineAppService
from application.dto.kline import KlineCollectRequest
from domain.kline.schemas import KlineBO
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.database.connection import get_db, AsyncSessionLocal
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.database.models.sys_collect_task import SysCollectTaskDB, SysCollectTaskDetailDB
from infrastructure.redis import get_redis
from route.schemas import response as R

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["采集任务"])


def _get_tushare_fetcher() -> FetcherProtocol:
    from infrastructure.collectors.tushare import TushareFetcher
    return TushareFetcher(KlineBO)


# ── POST /collect/tasks — 创建并启动采集任务 ─────────────────

@router.post("/tasks", summary="创建采集任务")
async def create_task(
    body: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task_type = body.get("task_type")
    params = body.get("params", {})

    if task_type not in ("daily_kline", "daily_basic", "stock_basic"):
        return R.ok({"message": f"不支持的任务类型: {task_type}"})

    running = await db.execute(
        select(SysCollectTaskDB)
        .where(SysCollectTaskDB.task_type == task_type, SysCollectTaskDB.status == "running")
    )
    if running.scalars().first():
        return R.ok({"message": f"{task_type} 已有运行中的任务，请等待完成"})

    count_stmt = select(func.count()).select_from(StockInfoDB).where(StockInfoDB.list_status == "L")
    exchange_filter = params.get("exchange") if params else None
    if exchange_filter and task_type == "daily_kline":
        count_stmt = count_stmt.where(StockInfoDB.exchange.in_(exchange_filter))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

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

    redis = await get_redis()
    await redis.hset(f"collect:progress:{task_id}", mapping={
        "total": str(total), "done": "0", "success": "0", "fail": "0",
        "skip": "0", "status": "running", "current": "",
    })
    await redis.expire(f"collect:progress:{task_id}", 86400)

    background_tasks.add_task(_execute_task, task_id, task_type, params)

    return R.ok({
        "task_id": task_id,
        "task_type": task_type,
        "total_count": total,
        "message": f"已启动 {task_type} 采集任务，共 {total} 只股票",
    })


# ── GET /collect/tasks — 任务列表 ────────────────────────────

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
    rows = (await db.execute(
        stmt.order_by(desc(SysCollectTaskDB.id))
        .limit(page_size)
        .offset((page - 1) * page_size)
    )).scalars().all()

    items = [_task_to_dict(t) for t in rows]
    return R.ok({"total": total, "page": page, "page_size": page_size, "items": items})


# ── GET /collect/tasks/{id} — 任务详情 ───────────────────────

@router.get("/tasks/{task_id}", summary="查询任务详情")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(SysCollectTaskDB, task_id)
    if not task:
        return R.ok({"message": "任务不存在"})
    return R.ok(_task_to_dict(task))


# ── GET /collect/tasks/{id}/progress — 实时进度 ──────────────

@router.get("/tasks/{task_id}/progress", summary="查询实时进度")
async def get_task_progress(task_id: int):
    redis = await get_redis()
    data = await redis.hgetall(f"collect:progress:{task_id}")
    if not data:
        return R.ok({"status": "unknown", "message": "无进度信息（任务可能已过期）"})
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


# ── POST /collect/tasks/{id}/cancel — 取消任务 ──────────────

_cancel_flags: set[int] = set()


@router.post("/tasks/{task_id}/cancel", summary="取消任务")
async def cancel_task(task_id: int, force: bool = Query(False), db: AsyncSession = Depends(get_db)):
    task = await db.get(SysCollectTaskDB, task_id)
    if not task:
        return R.ok({"message": "任务不存在"})
    if task.status not in ("running", "pending"):
        return R.ok({"message": f"任务状态为 {task.status}，无需取消"})

    _cancel_flags.add(task_id)

    if force:
        task.status = "cancelled"
        task.finished_at = datetime.now()
        if task.started_at:
            task.duration_ms = int((task.finished_at - task.started_at).total_seconds() * 1000)
        task.message = f"强制取消 (成功{task.success_count} 失败{task.fail_count})"
        await db.commit()

        redis = await get_redis()
        await redis.hset(f"collect:progress:{task_id}", "status", "cancelled")
        logger.info("任务 %d 被强制取消", task_id)
        return R.ok({"message": "任务已强制取消", "forced": True})

    return R.ok({"message": "已发送取消信号（如任务已挂起，请使用强制取消）"})


# ── 后台执行器 ──────────────────────────────────────────────

async def _execute_task(task_id: int, task_type: str, params: dict):
    handlers = {
        "daily_kline": _collect_daily_kline,
        "daily_basic": _collect_daily_basic,
        "stock_basic": _collect_stock_basic,
    }
    handler = handlers.get(task_type)
    if not handler:
        return

    try:
        await handler(task_id, params)
    except Exception as e:
        logger.exception("采集任务 %d 异常终止", task_id)
        await _finish_task(task_id, "failed", message=str(e))


async def _collect_daily_kline(task_id: int, params: dict):
    from infrastructure.config import get_settings

    settings = get_settings()
    max_conc = settings.COLLECT_MAX_CONCURRENCY
    user_conc = params.get("concurrency", settings.COLLECT_CONCURRENCY)
    concurrency = max(1, min(int(user_conc), max_conc))
    api_interval = max(0.1, concurrency * 0.15)
    chunk_size = settings.COLLECT_CHUNK_SIZE

    days = params.get("days", 7)
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    exchange_filter: list[str] | None = params.get("exchange")
    redis = await get_redis()

    logger.info("日K采集任务 %d 参数: 并发=%d (用户=%s, 上限=%d), 间隔=%.2fs",
                task_id, concurrency, user_conc, max_conc, api_interval)

    async with AsyncSessionLocal() as session:
        stmt = select(StockInfoDB.symbol).where(StockInfoDB.list_status == "L")
        if exchange_filter:
            stmt = stmt.where(StockInfoDB.exchange.in_(exchange_filter))
        stmt = stmt.order_by(StockInfoDB.symbol)
        result = await session.execute(stmt)
        symbols = [r[0] for r in result.all()]

    total = len(symbols)
    exchange_desc = ",".join(exchange_filter) if exchange_filter else "全部"
    await redis.hset(f"collect:progress:{task_id}", "total", str(total))
    logger.info("日K采集任务 %d 启动: %d 只股票 (%s), 并发=%d", task_id, total, exchange_desc, concurrency)

    collect_kwargs: dict = {}
    if start_date and end_date:
        collect_kwargs["start_date"] = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
        collect_kwargs["end_date"] = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
    else:
        collect_kwargs["days"] = days

    fetcher_pool: asyncio.Queue[FetcherProtocol] = asyncio.Queue()
    for _ in range(concurrency):
        fetcher_pool.put_nowait(_get_tushare_fetcher())

    sem = asyncio.Semaphore(concurrency)
    success = fail = 0
    _lock = asyncio.Lock()
    start_time = time.time()

    WORKER_TIMEOUT = 120  # seconds per symbol

    async def _collect_one(symbol: str) -> bool:
        nonlocal success, fail
        async with sem:
            if task_id in _cancel_flags:
                return False
            fetcher = await fetcher_pool.get()
            try:
                async with AsyncSessionLocal() as session:
                    svc = KlineAppService(session=session)
                    await asyncio.wait_for(
                        svc.collect(
                            KlineCollectRequest(symbol=symbol, **collect_kwargs),
                            fetcher,
                        ),
                        timeout=WORKER_TIMEOUT,
                    )
                    await session.commit()
                async with _lock:
                    success += 1
            except asyncio.TimeoutError:
                logger.warning("任务 %d 采集 %s 超时(%ds)", task_id, symbol, WORKER_TIMEOUT)
                async with _lock:
                    fail += 1
            except Exception as e:
                logger.warning("任务 %d 采集 %s 失败: %s", task_id, symbol, e)
                async with _lock:
                    fail += 1
            finally:
                await fetcher_pool.put(fetcher)

            pipe = redis.pipeline()
            pipe.hincrby(f"collect:progress:{task_id}", "done", 1)
            pipe.hset(f"collect:progress:{task_id}", "current", symbol)
            await pipe.execute()

            await asyncio.sleep(api_interval)
            return True

    for i in range(0, total, chunk_size):
        if task_id in _cancel_flags:
            _cancel_flags.discard(task_id)
            await _finish_task(task_id, "cancelled", success=success, fail=fail,
                               message=f"已取消: 成功 {success}, 失败 {fail}")
            await redis.hset(f"collect:progress:{task_id}", "status", "cancelled")
            return

        chunk = symbols[i:i + chunk_size]
        batch_idx = i // chunk_size + 1
        total_batches = (total + chunk_size - 1) // chunk_size
        logger.info("任务 %d 批次 %d/%d (%d只, 并发%d)",
                     task_id, batch_idx, total_batches, len(chunk), concurrency)

        await asyncio.gather(*[_collect_one(s) for s in chunk])

        await redis.hset(f"collect:progress:{task_id}", mapping={
            "done": str(success + fail),
            "success": str(success),
            "fail": str(fail),
        })

        elapsed_so_far = time.time() - start_time
        rate = (success + fail) / elapsed_so_far if elapsed_so_far > 0 else 0
        logger.info("任务 %d 进度: %d/%d (成功%d 失败%d) %.1f只/秒",
                     task_id, success + fail, total, success, fail, rate)

    elapsed = int((time.time() - start_time) * 1000)
    status = "success" if fail == 0 else ("failed" if success == 0 else "success")
    msg = f"完成 ({exchange_desc}, 并发{concurrency}): 成功 {success}, 失败 {fail}, 耗时 {elapsed // 1000}s"

    await _finish_task(task_id, status, success=success, fail=fail, duration_ms=elapsed, message=msg)
    await redis.hset(f"collect:progress:{task_id}", "status", status)
    logger.info("日K采集任务 %d 完成: %s", task_id, msg)


async def _collect_daily_basic(task_id: int, params: dict):
    """同步日频估值 — 复用现有 stock.py 中的逻辑"""
    from datetime import date, timedelta
    from infrastructure.repositories.fin_daily_basic_repository import FinDailyBasicRepoImpl

    days = params.get("days", 1)
    redis = await get_redis()
    start_time = time.time()

    trade_date = params.get("trade_date")
    if trade_date:
        dates = [trade_date]
    else:
        today = date.today()
        dates = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]

    await redis.hset(f"collect:progress:{task_id}", mapping={
        "total": str(len(dates)), "done": "0", "success": "0", "fail": "0",
        "status": "running", "current": "",
    })

    fetcher = _get_tushare_fetcher()
    success = fail = total_saved = 0
    logger.info("估值同步任务 %d 启动: %d 个日期 %s", task_id, len(dates), dates)

    for d in dates:
        if task_id in _cancel_flags:
            _cancel_flags.discard(task_id)
            await _finish_task(task_id, "cancelled", success=success, fail=fail,
                               message=f"已取消: 成功 {success} 日, 失败 {fail} 日")
            logger.info("估值同步任务 %d 已取消", task_id)
            return

        try:
            bo_list = await asyncio.to_thread(fetcher.fetch_daily_basic, d)
            if bo_list:
                entities = [bo.to_entity() for bo in bo_list]
                async with AsyncSessionLocal() as session:
                    repo = FinDailyBasicRepoImpl(session)
                    saved = await repo.save_batch(entities)
                    await session.commit()
                    total_saved += saved
                logger.info("任务 %d 估值 %s: 写入 %d 条", task_id, d, saved)
            else:
                logger.info("任务 %d 估值 %s: 无数据（非交易日？）", task_id, d)
            success += 1
        except Exception as e:
            fail += 1
            logger.warning("任务 %d 估值 %s 失败: %s", task_id, d, e)

        await redis.hset(f"collect:progress:{task_id}", mapping={
            "done": str(success + fail), "success": str(success),
            "fail": str(fail), "current": d,
        })

    elapsed = int((time.time() - start_time) * 1000)
    msg = f"完成: {success} 天, {total_saved} 条, 耗时 {elapsed // 1000}s"
    await _finish_task(task_id, "success" if fail == 0 else "success", success=success,
                       fail=fail, duration_ms=elapsed, message=msg)
    await redis.hset(f"collect:progress:{task_id}", "status", "success")


async def _collect_stock_basic(task_id: int, params: dict):
    """同步股票基本信息 — 复用现有 sync_stocks 逻辑"""
    from application.stock_service import StockAppService

    redis = await get_redis()
    start_time = time.time()
    logger.info("股票信息同步任务 %d 启动", task_id)

    await redis.hset(f"collect:progress:{task_id}", mapping={
        "total": "1", "done": "0", "success": "0", "fail": "0",
        "status": "running", "current": "stock_basic",
    })

    try:
        fetcher = _get_tushare_fetcher()
        async with AsyncSessionLocal() as session:
            svc = StockAppService(session=session)
            result = await svc.sync_stocks(fetcher, list_status=params.get("list_status", "L"))
            await session.commit()

        elapsed = int((time.time() - start_time) * 1000)
        msg = result.message
        logger.info("股票信息同步任务 %d 完成: %s, 耗时 %dms", task_id, msg, elapsed)
        await _finish_task(task_id, "success", success=1, fail=0, duration_ms=elapsed,
                           message=msg, total_count=result.synced_count)
        await redis.hset(f"collect:progress:{task_id}", mapping={
            "done": "1", "success": "1", "status": "success", "current": "",
        })
    except Exception as e:
        elapsed = int((time.time() - start_time) * 1000)
        logger.exception("股票信息同步任务 %d 失败, 耗时 %dms", task_id, elapsed)
        await _finish_task(task_id, "failed", success=0, fail=1, duration_ms=elapsed, message=str(e))
        await redis.hset(f"collect:progress:{task_id}", mapping={
            "done": "1", "fail": "1", "status": "failed",
        })


async def _finish_task(
    task_id: int,
    status: str,
    success: int = 0,
    fail: int = 0,
    duration_ms: int | None = None,
    message: str = "",
    total_count: int | None = None,
):
    logger.info("_finish_task %d → %s (成功%d 失败%d) %s", task_id, status, success, fail, message)
    async with AsyncSessionLocal() as session:
        task = await session.get(SysCollectTaskDB, task_id)
        if task:
            task.status = status
            task.success_count = success
            task.fail_count = fail
            task.finished_at = datetime.now()
            task.duration_ms = duration_ms
            task.message = message
            if total_count is not None:
                task.total_count = total_count
            await session.commit()


def _task_to_dict(t: SysCollectTaskDB) -> dict:
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

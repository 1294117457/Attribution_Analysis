"""FastAPI entry point (step7 simplified, unified DI mode)"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from shared.infrastructure.config.settings import get_settings
from shared.infrastructure.connection.db_factory import close_db
from shared.infrastructure.connection.redis_client import close_redis_client, redis
from shared.interface.router_compat import api_router
from contexts.auth.infrastructure.security import key_manager
from app.exception_handler import register_exception_handlers
from app.middleware import register_middlewares
from app.init_db import ensure_attrib_tables

# 导入所有 ORM 模型（确保 SQLAlchemy 自动建表）
from contexts.collect.infrastructure.persistence.models.collect_log import CollectLogDB  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI app lifecycle.

    step7 simplified:
      - collect ??????fetcher?service???? `connect/` ????? + service
        DefaultConstruct ?????????
      - ???? scheduler?schedule ??????????

    step7 v3（2026-10-19）—— TaskRunner 统一派发：
      - 启动时调用 CollectLogService.recover_orphan_logs()，把卡在 running 的日志（进程
        重启遗失）批量标记为 failed。
      - 不影响业务：只改 status + error_message，不动数据。
    """
    # JWT key warmup
    key_manager.warmup()

    # 自动建表（Phase 2 修复：v2 新增 collect_logs 等表，幂等）
    await ensure_attrib_tables()

    # 启动时恢复 orphan 日志（v3 新增；step8 起日志服务自管 session）
    try:
        from contexts.collect.application.service.manage import CollectLogService
        # CollectLogService 直接 import 全局 redis 单例，无需注入
        log_service = CollectLogService()
        recovered = await log_service.recover_orphan_logs(timeout_minutes=30)
        if recovered:
            logger.info("进程启动：恢复 %d 个 orphan 日志（status=running → failed）", recovered)
    except Exception as e:
        logger.warning("recover_orphan_logs 跳过（启动期容错）: %r", e)

    # Redis 健康检查（fail-fast：启动期发现 Redis 不可用直接报错）
    try:
        await redis.ping()
        logger.info("Redis 连接正常: PING OK")
    except Exception as e:
        logger.error("Redis PING 失败（启动期）：%r", e)
        raise

    yield

    await close_db()
    await close_redis_client()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Attribution Analysis API",
        description="DDD architecture - step7 simplified",
        version="3.0.0",
        lifespan=lifespan,
    )
    register_middlewares(application)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


application = create_app()


@application.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "3.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:application",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )

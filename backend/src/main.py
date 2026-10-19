"""FastAPI entry point (step7 simplified, unified DI mode)"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from shared.infrastructure.config.settings import get_settings
from shared.infrastructure.connection.db_factory import close_db
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

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI app lifecycle.

    step7 simplified:
      - collect ??????fetcher?service???? `connect/` ????? + service
        DefaultConstruct ?????????
      - ???? scheduler?schedule ??????????
    """
    # JWT key warmup
    key_manager.warmup()

    # 自动建表（Phase 2 修复：v2 新增 collect_logs 等表，幂等）
    await ensure_attrib_tables()

    yield

    await close_db()


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

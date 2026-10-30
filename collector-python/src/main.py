"""Collector 入口：只暴露 /api/collect/* + /health。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import response as R
from api import router as collect_router
from core.config import get_settings
from core.db import close_db
from core.errors import DomainError

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ⚠️ 不在运行时建表——collect_logs 由迁移脚本一次性创建
    # （postgres/initdb/02-collect-logs.sql）。见规范 §7.6。
    from tasks.manager import recover_stale_tasks
    try:
        await recover_stale_tasks()
    except Exception as e:
        logging.getLogger(__name__).warning("重启恢复失败（不阻断启动）: %r", e)
    yield
    await close_db()


def _safe(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    return value


def create_app() -> FastAPI:
    application = FastAPI(title="Attribution Collector API", version="2.0.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @application.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(status_code=exc.http_status,
                            content={"code": exc.code, "message": exc.message, "data": None})

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"code": 422, "message": "请求参数校验失败",
                                                      "data": {"errors": _safe(exc.errors())}})

    @application.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logging.getLogger(__name__).exception("未处理的异常: %s", exc)
        return JSONResponse(status_code=500,
                            content={"code": 500, "message": "服务器内部错误", "data": None})

    application.include_router(collect_router)
    from tasks.router import router as tasks_router
    application.include_router(tasks_router)
    return application


application = create_app()


@application.get("/health", tags=["health"])
async def health():
    return R.ok({"status": "ok", "service": "collector", "version": "2.0.0"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:application", host="0.0.0.0", port=8001, reload=False)

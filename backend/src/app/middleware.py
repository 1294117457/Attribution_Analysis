"""全局中间件注册（目前仅 CORS）

设计要点：
- 集中管理所有全局中间件（CORS / GZip / TrustedHost 等）
- main.py 不再关心具体中间件实现，只调用 register_middlewares(application)
- CORS 来源于 Pydantic Settings 的 ALLOWED_ORIGINS，与 .env 解耦
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.infrastructure.config.settings import get_settings


def register_middlewares(application: FastAPI) -> None:
    """注册全部全局中间件（目前仅 CORS）"""
    settings = get_settings()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

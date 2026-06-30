"""FastAPI 应用入口"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from infra.database.base import Base
from infra.database.connection import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="智能金融数据归因分析平台",
        description="数据采集 + 异常检测 + 归因分析",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由
    app.include_router(api_router)

    return app


app = create_app()


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "service": "attribution-analysis"}

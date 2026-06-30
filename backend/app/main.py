"""FastAPI 应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.database.base import Base
from app.database.connection import engine


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="智能金融数据归因分析平台",
        description="数据采集 + 异常检测 + 归因分析",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.on_event("startup")
    def on_startup():
        """启动时创建数据库表"""
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "service": "attribution-analysis"}

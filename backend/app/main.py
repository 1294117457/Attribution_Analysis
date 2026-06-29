"""FastAPI 应用入口"""

from fastapi import FastAPI
from app.api.router import api_router
from app.database.base import Base
from app.database.connection import engine

app = FastAPI(
    title="智能金融数据归因分析平台",
    version="1.0.0",
)

# 注册路由
app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    """启动时创建数据库表"""
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}

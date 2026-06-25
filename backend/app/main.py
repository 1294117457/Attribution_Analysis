"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import router as api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print(f"\n🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    print(f"📚 API 文档: http://localhost:8000/docs")
    print(f"📖 ReDoc: http://localhost:8000/redoc\n")

    # TODO: 启动定时任务
    # from app.tasks.scheduler import start_scheduler
    # start_scheduler()

    yield

    # 关闭时执行
    print(f"\n👋 {settings.APP_NAME} 已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能金融数据归因分析平台后端 API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# === CORS 中间件 ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === 注册路由 ===
app.include_router(api_v1_router, prefix="/api/v1", tags=["v1"])


# === 健康检查 ===
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# === 根路径 ===
@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": "Attribution Analysis API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }

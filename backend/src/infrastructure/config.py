"""应用配置（pydantic-settings）"""

import threading
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 服务
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = False

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/stock_db"

    # 连接池
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 数据源
    TUSHARE_TOKEN: str = ""

    # 采集并发
    COLLECT_CONCURRENCY: int = 3
    COLLECT_MAX_CONCURRENCY: int = 8
    COLLECT_CHUNK_SIZE: int = 30

    # API 版本
    API_V1_PREFIX: str = "/api/v1"


_settings: Settings | None = None
_lock = threading.Lock()


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（线程安全）"""
    global _settings
    if _settings is None:
        with _lock:
            if _settings is None:
                _settings = Settings()
    return _settings

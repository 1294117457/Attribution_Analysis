"""全局配置管理"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # 数据库
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/attribution"
    DATABASE_URL_ASYNC: str = "postgresql+asyncpg://postgres:password@localhost:5432/attribution"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API
    API_V1_PREFIX: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()

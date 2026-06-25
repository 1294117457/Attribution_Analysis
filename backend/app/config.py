"""应用配置"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # === 应用配置 ===
    APP_NAME: str = "Attribution Analysis API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # === 数据库配置 ===
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/attribution_db?charset=utf8mb4"

    # === Redis 配置 ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === Qdrant 向量数据库 ===
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "experiences"

    # === LLM API Keys ===
    OPENAI_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""

    # === CORS 配置 ===
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # === 文件路径 ===
    DATA_DIR: Path = BASE_DIR / "data"
    LOG_DIR: Path = BASE_DIR / "logs"


# 全局配置实例
settings = Settings()


# 确保目录存在
settings.DATA_DIR.mkdir(exist_ok=True)
settings.LOG_DIR.mkdir(exist_ok=True)

"""
配置管理，读取 .env 文件。
所有配置集中在这里，避免散落在代码各处。
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_ASYNC: str
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()

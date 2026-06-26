"""
基于pydantic_settings包
读取.env

不会有问题，因为 env_file = ".env" 的路径是相对于你运行命令的目录，而不是相对于 config.py 文件本身。
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_ASYNC: str
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
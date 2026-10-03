"""应用配置（pydantic-settings）"""

import threading
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        # DDD 改造后 settings.py 移到 infrastructure/config/settings.py
        # __file__ = backend/src/infrastructure/config/settings.py
        # .parent.parent.parent.parent = backend/  (要往上 4 级)
        env_file=Path(__file__).parent.parent.parent.parent / ".env",
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
    # 采集方案 / 任务组的定时调度（开发时可在 .env 关闭）
    COLLECT_SCHEDULER_ENABLED: bool = True
    COLLECT_SCHEDULER_TIMEZONE: str = "Asia/Shanghai"

    # API 版本
    API_V1_PREFIX: str = "/api/v1"

    # ── 邮件 SMTP(用于邮箱验证码) ──
    # 通过 .env 配置: SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD
    # SMTP_PASSWORD 推荐使用 QQ 邮箱「授权码」,不是登录密码
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""                # 留空则取 SMTP_USERNAME
    SMTP_USE_SSL: bool = True         # 465 → SSL; 587 → STARTTLS
    SMTP_SUBJECT_PREFIX: str = "[归因分析]"

    # 验证码策略
    VERIFICATION_CODE_LENGTH: int = 6
    VERIFICATION_CODE_TTL_SECONDS: int = 5 * 60         # 5 分钟
    VERIFICATION_CODE_RL_1M: int = 1                    # 1 分钟最多 1 次
    VERIFICATION_CODE_RL_1H: int = 5                    # 1 小时最多 5 次

    # 业务"系统账号":不受 1 小时最多 5 次的限制(方便压测与运营)
    # 用英文逗号分隔的用户名列表
    SYSTEM_ACCOUNTS: str = ""


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

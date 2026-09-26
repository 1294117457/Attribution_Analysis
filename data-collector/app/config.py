"""应用配置（pydantic-settings）。

所有配置从环境变量读取，详见 `.env.example`。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """运行时配置。所有字段均可通过环境变量覆盖。"""

    # ──────────────────────────────────────────────
    # 服务监听
    # ──────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", description="监听地址（生产仅内网）")
    port: int = Field(default=9100, description="监听端口")
    workers: int = Field(default=1, description="uvicorn worker 数")

    # ──────────────────────────────────────────────
    # 日志
    # ──────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="DEBUG/INFO/WARNING/ERROR")
    log_json: bool = Field(default=True, description="是否输出 JSON 结构化日志")
    log_file: Optional[str] = Field(default=None, description="日志文件路径（None = stdout）")

    # ──────────────────────────────────────────────
    # 安全（HMAC 验签）
    # ──────────────────────────────────────────────
    internal_hmac_secret: str = Field(
        default="dev-secret-please-rotate-in-production",
        description="内网 HMAC 共享密钥（必须 >= 32 字符）",
    )
    internal_allowed_ips: List[str] = Field(
        default_factory=lambda: ["127.0.0.1", "::1"],
        description="允许的客户端 IP 白名单（CIDR / 单 IP）",
    )
    timestamp_tolerance_seconds: int = Field(default=60, description="timestamp 允许偏差（秒）")
    nonce_ttl_seconds: int = Field(default=300, description="nonce 一次性有效期（秒）")
    enable_signature: bool = Field(default=True, description="是否启用 HMAC 验签（开发可关）")

    # ──────────────────────────────────────────────
    # 上游数据源
    # ──────────────────────────────────────────────
    tushare_token: str = Field(default="", description="tushare Pro token")
    eastmoney_base_url: str = Field(default="https://push2his.eastmoney.com")
    eastmoney_apis_base_url: str = Field(default="https://push2.eastmoney.com")
    sina_base_url: str = Field(default="https://image.sinajs.cn")

    # ──────────────────────────────────────────────
    # 上游调用策略
    # ──────────────────────────────────────────────
    upstream_timeout_seconds: int = Field(default=8, description="上游 HTTP 超时")
    upstream_max_retries: int = Field(default=2, description="上游失败重试次数")
    rate_limit_per_minute: int = Field(default=600, description="slowapi 每分钟限速")

    # ──────────────────────────────────────────────
    # Redis（用于 nonce 防重放 + 限流）
    # ──────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")

    # ──────────────────────────────────────────────
    # 元信息
    # ──────────────────────────────────────────────
    service_name: str = Field(default="data-collector", description="服务名（日志/指标）")
    service_version: str = Field(default="0.1.0", description="服务版本")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("internal_hmac_secret")
    @classmethod
    def _validate_secret(cls, v: str) -> str:
        if v and len(v) < 16:
            raise ValueError("internal_hmac_secret 必须 >= 16 字符")
        return v

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"log_level 必须是 {allowed}")
        return v_upper


# 全局单例（延迟加载：仅在首次访问时实例化）
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局配置实例（懒加载）。"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

"""auth context — DI 工厂聚合

按资源/职责分文件，本文件 re-export 给 route 层 `from contexts.auth.infrastructure.di import ...`。
"""
from contexts.auth.infrastructure.di.auth_service import (
    get_auth_service,
    get_captcha,
    get_email_verification_store,
    get_jwt_service,
    get_password_hasher,
)

__all__ = [
    "get_password_hasher",
    "get_jwt_service",
    "get_captcha",
    "get_email_verification_store",
    "get_auth_service",
]

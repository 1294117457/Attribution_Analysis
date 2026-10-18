"""auth context — 业务 DI 工厂

仅负责：组装 auth 相关的 service 和 adapter，供 route 层 Depends 注入。

包含：
- get_password_hasher / get_jwt_service / get_captcha / get_email_verification_store
- get_auth_service

**不包含** 纯资源 DI（get_db / get_redis 等）—— 那些在 `shared.infrastructure.di`。
**不包含** lifespan 初始化 —— auth 没有 lifespan init（装配在 service 首次构造时 lazy）。
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_db


# ═══════════════════════════════════════════════════════════════
# Auth 端口工厂
# ═══════════════════════════════════════════════════════════════

def get_password_hasher():
    """密码哈希器（bcrypt）单例"""
    from contexts.auth.infrastructure.adapter.auth_port_adapters import BcryptPasswordHasher
    return BcryptPasswordHasher()


def get_jwt_service():
    """JWT 服务（access + refresh token 签发与解析）单例"""
    from contexts.auth.infrastructure.adapter.auth_port_adapters import JwtAdapter
    return JwtAdapter()


def get_captcha():
    """图形验证码服务（生成 + 校验）单例"""
    from contexts.auth.infrastructure.adapter.auth_port_adapters import CaptchaAdapter
    return CaptchaAdapter()


def get_email_verification_store():
    """邮箱验证码存储（Redis-backed）单例"""
    from contexts.auth.infrastructure.adapter.auth_port_adapters import EmailVerificationAdapter
    return EmailVerificationAdapter()


# ═══════════════════════════════════════════════════════════════
# 业务 Service 工厂
# ═══════════════════════════════════════════════════════════════

def get_auth_service(
    session: AsyncSession = Depends(get_db),
    hasher = Depends(get_password_hasher),
    jwt = Depends(get_jwt_service),
    captcha = Depends(get_captcha),
    email_store = Depends(get_email_verification_store),
):
    """AuthService 工厂（每次请求一个新实例，每个实例一个 session）"""
    from contexts.auth.application.service.auth_service import AuthService
    from contexts.auth.infrastructure.persistence.repositories.auth_repository import (
        PermissionRepoImpl,
        RefreshTokenRepoImpl,
        RoleRepoImpl,
        UserRepoImpl,
    )
    return AuthService(
        users=UserRepoImpl(session),
        roles=RoleRepoImpl(session),
        perms=PermissionRepoImpl(session),
        refresh=RefreshTokenRepoImpl(),
        hasher=hasher,
        captcha=captcha,
        email_verify=email_store,
        jwt=jwt,
    )


__all__ = [
    "get_password_hasher",
    "get_jwt_service",
    "get_captcha",
    "get_email_verification_store",
    "get_auth_service",
]

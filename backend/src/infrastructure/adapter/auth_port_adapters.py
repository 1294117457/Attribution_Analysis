"""基础设施 port 适配器 — 实现 application/service/auth_app_service.py 中声明的 4 个 port

- BcryptPasswordHasher        : PasswordHasherPort
- CaptchaAdapter              : CaptchaPort
- EmailVerificationAdapter    : EmailVerificationPort
- JwtAdapter                  : JwtPort

DDD.md §2.2 / §4：application 定义 port，infrastructure 实现并注入。
"""
from __future__ import annotations

from typing import Optional

from application.service.auth_service import (
    CaptchaPort,
    EmailVerificationPort,
    JwtPort,
    PasswordHasherPort,
)
from infrastructure.security import password as _password_module
from infrastructure.security.captcha import Captcha as _Captcha
from infrastructure.security.jwt_service import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    REFRESH_TOKEN_EXPIRE_SECONDS,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from infrastructure.adapter.email_verification import (
    EmailVerificationService,
)


class BcryptPasswordHasher(PasswordHasherPort):
    """bcrypt 密码 hash/verify 适配器"""

    def hash(self, plain: str) -> str:
        return _password_module.hash_password(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        return _password_module.verify_password(plain, hashed)


class CaptchaAdapter(CaptchaPort):
    """图形验证码适配器（委托 Captcha.verify 静态方法）"""

    async def verify(self, captcha_id: str, captcha_code: str) -> tuple[bool, str]:
        return await _Captcha.verify(captcha_id, captcha_code)


class EmailVerificationAdapter(EmailVerificationPort):
    """邮箱验证码适配器"""

    def __init__(self, service: Optional[EmailVerificationService] = None) -> None:
        self._service = service or EmailVerificationService()

    async def send(
        self,
        *,
        email: str,
        purpose: str,
        ip: Optional[str],
        user_agent: Optional[str],
    ) -> dict:
        return await self._service.send(
            email=email, purpose=purpose, ip=ip, user_agent=user_agent,
        )

    async def verify(self, *, email: str, purpose: str, input_code: str) -> None:
        await self._service.verify(email=email, purpose=purpose, input_code=input_code)


class JwtAdapter(JwtPort):
    """JWT 签发 / 解码 适配器"""

    @property
    def access_expire_seconds(self) -> int:
        return ACCESS_TOKEN_EXPIRE_SECONDS

    @property
    def refresh_expire_seconds(self) -> int:
        return REFRESH_TOKEN_EXPIRE_SECONDS

    def create_access_token(
        self,
        *,
        user_id: int,
        email: str,
        roles: list[str],
        permissions: list[str],
    ) -> tuple[str, int]:
        token, expires_at = create_access_token(
            user_id=user_id, email=email, roles=roles, permissions=permissions,
        )
        return token, int(expires_at.timestamp())

    def create_refresh_token(self, *, user_id: int) -> tuple[str, str, int]:
        token, jti, expires_at = create_refresh_token(user_id=user_id)
        return token, jti, int(expires_at.timestamp())

    def decode_token(self, token: str, *, expected_type: str) -> dict:
        return decode_token(token, expected_type=expected_type)  # type: ignore[arg-type]
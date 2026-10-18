"""邮箱验证码服务

业务流程:
- send(email, purpose)  -> 限流(1 分钟 1 次 / 1 小时 5 次)
                           -> 生成 6 位数字码
                           -> 写 Redis(明文,5 分钟 TTL)
                           -> 异步发邮件(失败时删除 Redis 中的码)
- verify(email, purpose, input_code)
                         -> 一次性取 + 校验(避免并发重放)

存储 / 限流原语由 `contexts.auth.infrastructure.cache.email_code` 提供。
"""
from __future__ import annotations

import logging
import random
import string
from dataclasses import dataclass
from typing import Optional

from shared.infrastructure.config.settings import get_settings
from contexts.auth.infrastructure.cache import email_code
from contexts.auth.infrastructure.security.email import build_verification_code_email, send_email

logger = logging.getLogger(__name__)


# ── 异常 ─────────────────────────────────────────────────────────


class EmailCodeError(Exception):
    """邮箱验证码相关异常(由 DomainError 处理器统一 400)"""

    def __init__(self, message: str, code: str = "EMAIL_CODE_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class EmailCodeRateLimitedError(EmailCodeError):
    def __init__(self, retry_after: int):
        super().__init__(
            message=f"验证码发送过于频繁,请 {retry_after} 秒后再试",
            code="EMAIL_CODE_RATE_LIMITED",
        )
        self.retry_after = retry_after


class EmailCodeInvalidError(EmailCodeError):
    def __init__(self, reason: str = "验证码错误"):
        super().__init__(message=reason, code="EMAIL_CODE_INVALID")


# ── 业务实现 ─────────────────────────────────────────────────────


@dataclass
class EmailVerificationService:
    """邮箱验证码工具类(不依赖 DB session)"""

    async def send(
        self,
        *,
        email: str,
        purpose: str = "register",
        ip: Optional[str] = None,            # 保留入参(调用方传),但不落库(便于后续扩展审计)
        user_agent: Optional[str] = None,
    ) -> dict:
        """发送验证码,返回 {expire_seconds, purpose}。限流 / 失败时抛 EmailCodeError。"""
        settings = get_settings()

        # 1. Redis 限流
        await self._check_rate_limit(email=email, purpose=purpose)

        # 2. 生成 + 写 Redis
        code = _make_code(settings.VERIFICATION_CODE_LENGTH)
        ttl = settings.VERIFICATION_CODE_TTL_SECONDS
        await email_code.store_code(code, ttl, purpose, email)

        # 3. 发邮件
        try:
            purpose_label = "注册" if purpose == "register" else "改密"
            subject, html = build_verification_code_email(
                code=code,
                expire_minutes=ttl // 60,
                purpose_label=purpose_label,
            )
            await send_email(email, subject, html)
        except Exception as e:  # noqa: BLE001
            # 失败立即把 Redis 中码删除,用户不会拿到一个失败的验证码
            await email_code.delete_code(purpose, email)
            logger.error("发送验证码失败并已回滚: %s", e)
            raise EmailCodeError(
                message=f"验证码发送失败: {e}", code="EMAIL_CODE_SEND_FAILED"
            )

        return {
            "expire_seconds": ttl,
            "purpose": purpose,
        }

    async def _check_rate_limit(self, *, email: str, purpose: str) -> None:
        """1m / 1h 两层限频(任一被拒都抛错)。"""
        settings = get_settings()

        # 1 分钟内 1 次
        allowed_1m, _ = await email_code.check_rate_limit(
            "1m", purpose, email,
            max_count=settings.VERIFICATION_CODE_RL_1M, window_seconds=60,
        )
        if not allowed_1m:
            raise EmailCodeRateLimitedError(retry_after=60)

        # 1 小时内 5 次
        allowed_1h, _ = await email_code.check_rate_limit(
            "1h", purpose, email,
            max_count=settings.VERIFICATION_CODE_RL_1H, window_seconds=3600,
        )
        if not allowed_1h:
            raise EmailCodeRateLimitedError(retry_after=3600)

    # ── 校验 ──

    async def verify(
        self,
        *,
        email: str,
        purpose: str,
        input_code: str,
    ) -> None:
        """校验验证码。成功:先比对后 DEL(防重放);失败/过期抛 EmailCodeError。"""
        if not input_code or not input_code.strip():
            raise EmailCodeInvalidError("验证码不能为空")

        stored = await email_code.get_code(purpose, email)

        if not stored:
            raise EmailCodeInvalidError("验证码已过期,请重新获取")

        # 先比对,后删除,避免误删(比如用户多打了一个空格导致不匹配时仍把码留下)
        if stored != input_code.strip():
            raise EmailCodeInvalidError("验证码错误")

        # 校验通过,立即销毁(防重放)
        await email_code.delete_code(purpose, email)


# ── 工具 ──────────────────────────────────────────────────────────


def _make_code(length: int) -> str:
    return "".join(random.choices(string.digits, k=length))

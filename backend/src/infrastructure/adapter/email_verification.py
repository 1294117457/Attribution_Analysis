"""邮箱验证码服务(Redis 版)

业务流程:
- send(email, purpose)  -> Redis 限流(1 分钟 1 次 / 1 小时 5 次)
                           -> 生成 6 位数字码
                           -> 写入 Redis(明文,5 分钟 TTL)
                           -> 异步发邮件(失败时删除 Redis 中的码)
- verify(email, purpose, input_code)
                         -> Redis GETDEL 一次性取 + 校验(避免并发重放)

存储:
- 验证码明文存 Redis,TTL 5 分钟;过期/被消费后自动失效。
- 不入库;考虑到 5 分钟短时,数据价值低,丢了不影响业务。

业务用途:
- register    : 注册
- reset_password : 改密 / 找回密码(预留)
"""
from __future__ import annotations

import logging
import random
import string
from dataclasses import dataclass
from typing import Optional

from infrastructure.adapter.cache.redis_cache import RedisCache, get_cache
from infrastructure.config.settings import get_settings
from infrastructure.security.email import build_verification_code_email, send_email


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
    """邮箱验证码工具类(不依赖 DB session,直接走 Redis)。

    旧设计:接受 AsyncSession;现服务由 AuthAppService 无参构造即可。
    """

    # 默认无参构造即可(不再需要 session)
    # 用 dataclass 但保留向后兼容:EmailVerificationService(session) / EmailVerificationService() 都可

    # ── 生成 + 发送 ──

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
        cache: RedisCache = await get_cache()
        await cache.store_email_code(code, ttl, purpose, email)

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
            await cache.delete_email_code(purpose, email)
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
        cache: RedisCache = await get_cache()

        # 1 分钟内 1 次
        key_1m = RedisCache.email_rate_limit_key("1m", purpose, email)
        allowed_1m, _ = await cache.rate_limit(
            key_1m, max_count=settings.VERIFICATION_CODE_RL_1M, window_seconds=60
        )
        if not allowed_1m:
            raise EmailCodeRateLimitedError(retry_after=60)

        # 1 小时内 5 次
        key_1h = RedisCache.email_rate_limit_key("1h", purpose, email)
        allowed_1h, _ = await cache.rate_limit(
            key_1h, max_count=settings.VERIFICATION_CODE_RL_1H, window_seconds=3600
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
        """校验验证码。成功:Redis GETDEL 一次性消费;失败/过期抛 EmailCodeError。

        GETDEL 是原子操作:并发请求两个相同码,只有一个能拿到正确码,另一个必然失败。
        """
        if not input_code or not input_code.strip():
            raise EmailCodeInvalidError("验证码不能为空")

        cache: RedisCache = await get_cache()
        stored = await cache.get_email_code(purpose, email)

        if not stored:
            raise EmailCodeInvalidError("验证码已过期,请重新获取")

        # 先比对,后 GETDEL,避免误删(比如用户多打了一个空格导致不匹配时仍把码留下)
        if stored != input_code.strip():
            raise EmailCodeInvalidError("验证码错误")

        # 校验通过,立即销毁(防重放)
        await cache.delete_email_code(purpose, email)


# ── 工具 ──────────────────────────────────────────────────────────


def _make_code(length: int) -> str:
    return "".join(random.choices(string.digits, k=length))
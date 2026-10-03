"""E2E smoke test for email verification code (in-memory sqlite, no real SMTP)."""
import asyncio
import re
import sys

sys.path.insert(0, "src")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import infrastructure.persistence.models  # noqa: F401
from infrastructure.persistence.base import Base
from infrastructure.service import email_verification_service as ev_mod
from infrastructure.service.email_verification_service import (
    EmailCodeInvalidError,
    EmailCodeRateLimitedError,
    EmailVerificationService,
)


async def main() -> int:
    # 1) 替换真发邮件为本地捕获
    captured: list[tuple[str, str, str]] = []

    async def fake_send(to_email: str, subject: str, html: str) -> None:
        captured.append((to_email, subject, html))

    ev_mod.send_email = fake_send

    # 2) 内存建表
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    failures: list[str] = []

    async with Session() as s:
        ev = EmailVerificationService(s)

        # (a) 第一次发送
        r = await ev.send(email="a@x.com", purpose="register")
        assert r["expire_seconds"] == 5 * 60
        assert len(captured) == 1
        m = re.search(r"<div[^>]*>([0-9]{6})</div>", captured[0][2])
        if not m:
            failures.append("无法从 HTML 提取验证码")
            print("FAIL", failures)
            return 1
        code = m.group(1)
        print(f"send#1 ok, code={code}")

        # (b) 立即第二次 → 1 分钟限流
        try:
            await ev.send(email="a@x.com", purpose="register")
            failures.append("限流未生效")
        except EmailCodeRateLimitedError as e:
            print(f"rate-limit ok: {e.message}")

        # (c) 错误验证码
        try:
            await ev.verify(email="a@x.com", purpose="register", input_code="000000")
            failures.append("错误码未拒绝")
        except EmailCodeInvalidError as e:
            print(f"invalid-code ok: {e.message}")

        # (d) 正确验证码
        await ev.verify(email="a@x.com", purpose="register", input_code=code)
        print("verify ok")

        # (e) 重放 → 已消费
        try:
            await ev.verify(
                email="a@x.com", purpose="register", input_code=code
            )
            failures.append("重放未拦截")
        except EmailCodeInvalidError as e:
            print(f"replay-blocked ok: {e.message}")

    if failures:
        print("FAIL", failures)
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

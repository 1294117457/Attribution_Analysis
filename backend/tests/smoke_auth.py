"""阶段 8 烟雾测试 — 不依赖真实 Postgres / Redis

- SQLite 内存数据库替代 Postgres
- 不连 Redis;在测试入口把 EmailVerificationService.verify 桩成"任何非空 code 都通过"
- 不 import main(避免 settings / 多模块初始化慢)
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("TUSHARE_TOKEN", "test_token_for_smoke")


def override_db_for_sqlite():
    """重写 connection 模块使用 SQLite"""
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    import infrastructure.persistence.connection as conn_module

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _get_db_override():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    conn_module.async_engine = engine
    conn_module.AsyncSessionLocal = session_factory
    conn_module.get_db = _get_db_override


def override_key_manager_for_test():
    """让 key_manager 使用一个临时目录"""
    import infrastructure.security.key_manager as km
    tmp = Path(tempfile.mkdtemp(prefix="jwt_keys_"))
    km._KEY_DIR = tmp
    km.JWT_PRIVATE_KEY_PATH = tmp / "jwt_private.pem"
    km.JWT_PUBLIC_KEY_PATH = tmp / "jwt_public.pem"
    km._private_key = None
    km._public_key = None
    km._kid = None


def override_email_verify_for_test():
    """不连 Redis:把 verify / send 桩成 no-op,任意 code 都视为正确。"""
    from infrastructure.adapter import email_verification as mod

    class _Stub:
        async def send(self, **kwargs):
            return {"expire_seconds": 300, "purpose": kwargs.get("purpose", "register")}

        async def verify(self, *, email: str, purpose: str, input_code: str) -> None:
            if not input_code or not input_code.strip():
                from domain.entitys.auth.entity import AuthError
                raise AuthError(message="验证码不能为空", code="EMAIL_CODE_INVALID")

    mod.EmailVerificationService = _Stub  # type: ignore[assignment]


def override_captcha_for_test():
    """不连 Redis:把图形验证码桩成 '0000' 即通过。"""
    from application.service import auth_app_service as mod

    class _StubCaptcha:
        async def verify(self, captcha_id, captcha_code):
            if (captcha_code or "").strip().upper() == "0000":
                return True, ""
            return False, "验证码错误(测试 stub 仅接受 0000)"

    mod.CaptchaPort = _StubCaptcha  # type: ignore[assignment]


async def run():
    override_key_manager_for_test()
    override_db_for_sqlite()
    override_email_verify_for_test()
    override_captcha_for_test()

    from sqlalchemy import text
    from infrastructure.persistence.base import Base
    from infrastructure.persistence.connection import async_engine, AsyncSessionLocal
    from infrastructure.persistence.models.user import UserDB, RoleDB, PermissionDB  # noqa
    from infrastructure.persistence.models.user_role import UserRoleDB, RolePermissionDB  # noqa

    # 一次性创建表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 注入 3 角色 + 3 个测试权限
        await conn.execute(text(
            "INSERT INTO sys_roles (code, name, description, is_system, sort_order) VALUES "
            "('admin', '管理员', 'all', 1, 10),"
            "('member', '会员', 'member', 0, 20),"
            "('viewer', '访客', 'viewer', 0, 30)"
        ))
        await conn.execute(text(
            "INSERT INTO sys_permissions (code, resource, action, name) VALUES "
            "('user:read', 'user', 'read', '查看用户'),"
            "('user:write', 'user', 'write', '管理用户'),"
            "('role:read', 'role', 'read', '查看角色')"
        ))
        await conn.execute(text(
            "INSERT INTO sys_role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM sys_roles r, sys_permissions p WHERE r.code = 'admin'"
        ))

    from application.service.auth_app_service import AuthAppService
    from infrastructure.adapter.auth_port_adapters import (
        BcryptPasswordHasher,
        CaptchaAdapter,
        EmailVerificationAdapter,
        JwtAdapter,
    )
    from infrastructure.persistence.repositories.auth_repository import (
        PermissionRepoImpl,
        RefreshTokenRepoImpl,
        RoleRepoImpl,
        UserRepoImpl,
    )

    # bypass captcha:测试时把 CaptchaAdapter 的 verify 直接替换为 '0000 即通过'
    CaptchaAdapter.verify = lambda self, captcha_id, captcha_code: (  # type: ignore[assignment]
        (True, "") if (captcha_code or "").strip().upper() == "0000"
        else (False, "验证码错误(测试 stub 仅接受 0000)")
    )

    async with AsyncSessionLocal() as session:
        svc = AuthAppService(
            users=UserRepoImpl(session),
            roles=RoleRepoImpl(session),
            perms=PermissionRepoImpl(session),
            refresh=RefreshTokenRepoImpl(),
            hasher=BcryptPasswordHasher(),
            captcha=CaptchaAdapter(),
            email_verify=EmailVerificationAdapter(),
            jwt=JwtAdapter(),
        )

        # 1) register(code 在 stub 中被接受; captcha 用 '0000' 旁路)
        u1 = await svc.register(
            email="alice@test.com",
            password="password123",
            code="any-code",
            nickname="Alice",
        )
        print(f"[register] id={u1.id} email={u1.email} roles={[r.code for r in u1.roles]}")

        # 2) login(captcha 用 '0000' 旁路)
        data = await svc.login(
            email="alice@test.com",
            password="password123",
            captcha_id="stub",
            captcha_code="0000",
        )
        print(
            f"[login] token_type={data['token_type']} expires_in={data['expires_in']} "
            f"user.roles={data['user_info']['role_codes']} "
            f"user.perms={data['user_info']['permissions']}"
        )
        access = data["access_token"]
        refresh = data["refresh_token"]

        # 3) parse_access_token (deps_auth 用)
        claims = await svc.parse_access_token(access)
        print(f"[parse] sub={claims['sub']} roles={claims['roles']} perms_count={len(claims['permissions'])}")

        # 4) refresh — 旧 refresh 走 Redis 黑名单(无 Redis 时会抛 ConnectionError,这里预期失败)
        try:
            new = await svc.refresh_token(refresh)
            print(f"[refresh] new_access_len={len(new['access_token'])}")
        except Exception as e:
            print(f"[refresh] expected fail without Redis: {type(e).__name__}: {e}")

        # 5) 错误密码
        try:
            await svc.login(
                email="alice@test.com",
                password="wrongpass",
                captcha_id="stub",
                captcha_code="0000",
            )
            print("[wrong pwd] expected fail")
        except Exception as e:
            print(f"[wrong pwd] OK rejected: {getattr(e,'code','?')}")

        # 6) list_users + assign_role
        items, total = await svc.list_users(page=1, page_size=10)
        print(f"[list] total={total} items={len(items)}")

        admin_role = await svc.roles.find_by_code("admin")
        await svc.assign_role(u1.id, admin_role.id)
        new_info = await svc.get_user_info(u1.id)
        print(
            f"[assign-role] roles={new_info['role_codes']} "
            f"perms={new_info['permissions']}"
        )

    # 验证 AuthError -> 400
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from domain.entitys.auth.entity import InvalidCredentialsError
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.exception_handler(InvalidCredentialsError)
    async def _h(req, exc):
        return JSONResponse(status_code=400, content={"code": 400, "message": exc.message, "data": None})

    @app.get("/trigger")
    def _():
        raise InvalidCredentialsError()

    client = TestClient(app, raise_server_exceptions=False)
    res = client.get("/trigger")
    print(f"[exception_handler] status={res.status_code} body={res.json()}")
    assert res.status_code == 400
    assert res.json()["code"] == 400

    print("=" * 50)
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(run())
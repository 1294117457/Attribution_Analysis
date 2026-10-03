"""认证授权 - 应用服务

业务模块：auth/（前端 LoginPage / ChangePasswordPage / AccountPage）

依赖全部通过构造注入（DDD.md §4）：
- users / roles / perms / refresh：仓储接口（domain）
- hasher / captcha / email_verify / jwt：port 接口（application，由 infrastructure 实现）
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Protocol

import jwt as pyjwt

from domain.entitys.auth.entity import (
    InvalidCredentialsError,
    Permission,
    Role,
    TokenInvalidError,
    User,
    UserAlreadyExistsError,
    UserInactiveError,
    UserNotFoundError,
)
from domain.entitys.auth.repository import (
    PermissionRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)


# ════════════════════════════════════════════════════════════════════════
# Port 接口（DDD.md §2.2 — application 定义 port，由 infrastructure 实现）
# ════════════════════════════════════════════════════════════════════════


class PasswordHasherPort(Protocol):
    """密码 hash / verify 抽象端口"""

    def hash(self, plain: str) -> str: ...
    def verify(self, plain: str, hashed: str) -> bool: ...


class CaptchaPort(Protocol):
    """图形验证码校验端口"""

    async def verify(self, captcha_id: str, captcha_code: str) -> tuple[bool, str]: ...


class EmailVerificationPort(Protocol):
    """邮箱验证码发送 / 校验端口（实现位于 infrastructure.adapter.email_verification）"""

    async def send(
        self,
        *,
        email: str,
        purpose: str,
        ip: Optional[str],
        user_agent: Optional[str],
    ) -> dict: ...

    async def verify(self, *, email: str, purpose: str, input_code: str) -> None: ...


class JwtPort(Protocol):
    """JWT 签发 / 解码端口"""

    @property
    def access_expire_seconds(self) -> int: ...
    @property
    def refresh_expire_seconds(self) -> int: ...

    def create_access_token(
        self,
        *,
        user_id: int,
        email: str,
        roles: list[str],
        permissions: list[str],
    ) -> tuple[str, int]: ...

    def create_refresh_token(self, *, user_id: int) -> tuple[str, str, int]: ...

    def decode_token(self, token: str, *, expected_type: str) -> dict: ...


# ════════════════════════════════════════════════════════════════════════
# 应用服务
# ════════════════════════════════════════════════════════════════════════


class AuthService:
    """认证授权应用服务（依赖注入：所有依赖由构造函数注入）"""

    def __init__(
        self,
        *,
        users: UserRepository,
        roles: RoleRepository,
        perms: PermissionRepository,
        refresh: RefreshTokenRepository,
        hasher: PasswordHasherPort,
        captcha: CaptchaPort,
        email_verify: EmailVerificationPort,
        jwt: JwtPort,
    ) -> None:
        self.users = users
        self.roles = roles
        self.perms = perms
        self.refresh = refresh
        self.hasher = hasher
        self.captcha = captcha
        self.email_verify = email_verify
        self.jwt = jwt

    # ── 邮箱验证码 ──────────────────────────────────────────────────

    async def send_verification_code(
        self,
        *,
        email: str,
        purpose: str = "register",
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        captcha_id: str,
        captcha_code: str,
    ) -> dict:
        """发送邮箱验证码（限流 + 写 Redis + 发邮件）。

        - 注册场景:邮箱已被注册 → 抛 UserAlreadyExistsError(避免泄漏注册状态)
        - 改密场景:邮箱未注册 → 抛 UserNotFoundError(用户应能感知"邮箱未注册")
        - 图形验证码:必传,失败抛 AuthError → 400
        """
        await self._verify_captcha(captcha_id, captcha_code)

        if purpose == "register" and await self.users.find_by_email(email):
            raise UserAlreadyExistsError(field="邮箱", value=email)
        if purpose == "reset_password" and not await self.users.find_by_email(email):
            raise UserNotFoundError(email)
        return await self.email_verify.send(
            email=email,
            purpose=purpose,
            ip=ip,
            user_agent=user_agent,
        )

    async def _verify_captcha(self, captcha_id: str, captcha_code: str) -> None:
        """强制要求前端传 captcha_id + code,任一为空或校验失败都抛 AuthError。"""
        if not captcha_id or not captcha_code:
            from domain.entitys.auth.entity import AuthError
            raise AuthError(message="图形验证码不能为空", code="CAPTCHA_REQUIRED")
        ok, err = await self.captcha.verify(captcha_id, captcha_code)
        if not ok:
            from domain.entitys.auth.entity import AuthError
            raise AuthError(message=err, code="CAPTCHA_INVALID")

    # ── 注册 ─────────────────────────────────────────────────────────

    async def register(
        self,
        *,
        email: str,
        password: str,
        code: str,
        nickname: Optional[str] = None,
    ) -> User:
        """注册新用户。

        - 必须先通过 /auth/send-verification-code 拿到邮箱验证码
        - email 必须未占用
        - 自动绑定 'member' 角色(由 UserRepoImpl.create 完成)
        - nickname 可选,空时回退为 email 本地部分
        - 通过邮箱验证码注册 = 邮箱已验证(is_verified=True)
        """
        await self.email_verify.verify(email=email, purpose="register", input_code=code)

        if await self.users.find_by_email(email):
            raise UserAlreadyExistsError(field="邮箱", value=email)

        fallback_nick = email.split("@", 1)[0] if "@" in email else email
        new_user = User(
            id=0,
            email=email,
            password_hash=self.hasher.hash(password),
            nickname=nickname or fallback_nick,
            is_active=True,
            is_verified=True,
            roles=[],
        )
        return await self.users.create(new_user)

    # ── 登录 ─────────────────────────────────────────────────────────

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None,
        captcha_id: str,
        captcha_code: str,
    ) -> dict:
        """邮箱 + 密码登录。返回完整登录响应 dict。

        图形验证码:必传,失败抛 AuthError → 400。
        """
        await self._verify_captcha(captcha_id, captcha_code)

        user = await self.users.find_by_email(email)
        # 即使用户不存在,也走一遍 hash(避免时序攻击暴露"用户存在与否")
        if not user:
            self.hasher.hash(password)
            raise InvalidCredentialsError()

        if not self.hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise UserInactiveError()

        role_codes = [r.code for r in user.roles]
        perm_codes = await self.users.list_permission_codes_by_user(user.id)

        access_token, _access_exp = self.jwt.create_access_token(
            user_id=user.id,
            email=user.email,
            roles=role_codes,
            permissions=perm_codes,
        )
        refresh_token, jti, _new_refresh_exp = self.jwt.create_refresh_token(user_id=user.id)
        await self.refresh.save(
            user_id=user.id,
            jti=jti,
            expires_in_seconds=self.jwt.refresh_expire_seconds,
        )

        user.record_login(ip)
        await self.users.update(user)
        user.clear_events()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.jwt.access_expire_seconds,
            "user_info": self._user_to_dict(user, role_codes, perm_codes),
        }

    # ── refresh ───────────────────────────────────────────────────────

    async def refresh_token(self, refresh_token: str) -> dict:
        """refresh rotation: 撤销旧 jti,签发新一对 token。"""
        try:
            claims = self.jwt.decode_token(refresh_token, expected_type="refresh")
        except pyjwt.ExpiredSignatureError:
            raise TokenInvalidError("已过期")
        except pyjwt.InvalidTokenError as e:
            raise TokenInvalidError(str(e))

        old_jti = claims["jti"]
        sub = int(claims["sub"])
        old_exp_ts = int(claims["exp"])
        now_ts = int(datetime.now(tz=timezone.utc).timestamp())
        old_remaining = max(1, old_exp_ts - now_ts)

        if not await self.refresh.is_active(old_jti):
            await self.refresh.revoke_all_for_user(sub)
            raise TokenInvalidError("refresh token 已被撤销,全设备下线")

        user = await self.users.find_by_id(sub)
        if not user or not user.is_active:
            await self.refresh.revoke_all_for_user(sub)
            raise UserInactiveError()

        await self.refresh.revoke(old_jti, expires_in_seconds=old_remaining)

        role_codes = [r.code for r in user.roles]
        perm_codes = await self.users.list_permission_codes_by_user(user.id)
        new_access, _access_exp = self.jwt.create_access_token(
            user_id=user.id,
            email=user.email,
            roles=role_codes,
            permissions=perm_codes,
        )
        new_refresh, new_jti, _new_exp = self.jwt.create_refresh_token(user_id=user.id)
        await self.refresh.save(
            user_id=user.id,
            jti=new_jti,
            expires_in_seconds=self.jwt.refresh_expire_seconds,
        )

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "Bearer",
            "expires_in": self.jwt.access_expire_seconds,
        }

    # ── logout ─────────────────────────────────────────────────────────

    async def logout(self, user_id: int) -> None:
        """登出:撤销该用户所有未撤销的 refresh token。"""
        await self.refresh.revoke_all_for_user(user_id)

    # ── 解析 access token(供 deps_auth) ─────────────────────────────

    async def parse_access_token(self, token: str) -> dict:
        """解码 access token claims。"""
        try:
            return self.jwt.decode_token(token, expected_type="access")
        except pyjwt.ExpiredSignatureError:
            raise TokenInvalidError("access token 已过期")
        except pyjwt.InvalidTokenError as e:
            raise TokenInvalidError(str(e))

    # ── 查询 ─────────────────────────────────────────────────────────

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict], int]:
        users, total = await self.users.list_users(
            page=page,
            page_size=page_size,
            keyword=keyword,
            is_active=is_active,
        )
        items = []
        for u in users:
            role_codes = [r.code for r in u.roles]
            perm_codes = await self.users.list_permission_codes_by_user(u.id)
            items.append(self._user_to_dict(u, role_codes, perm_codes))
        return items, total

    async def get_user_info(self, user_id: int) -> dict:
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        role_codes = [r.code for r in user.roles]
        perm_codes = await self.users.list_permission_codes_by_user(user_id)
        return self._user_to_dict(user, role_codes, perm_codes)

    # ── 写操作 ──────────────────────────────────────────────────────

    async def update_user_status(self, user_id: int, is_active: bool) -> dict:
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        user.is_active = is_active
        updated = await self.users.update(user)
        if not is_active:
            await self.refresh.revoke_all_for_user(user_id)
        return {"id": updated.id, "is_active": updated.is_active}

    async def reset_user_password(self, user_id: int, new_password: str) -> None:
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        user.password_hash = self.hasher.hash(new_password)
        await self.users.update(user)
        await self.refresh.revoke_all_for_user(user_id)

    async def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> None:
        """用户自助改密:校验旧密码 → 写入新密码 → 撤销该用户全部 refresh token。"""
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        if not self.hasher.verify(old_password, user.password_hash):
            raise InvalidCredentialsError()
        user.password_hash = self.hasher.hash(new_password)
        await self.users.update(user)
        await self.refresh.revoke_all_for_user(user_id)

    async def assign_role(self, user_id: int, role_id: int) -> None:
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        await self.users.assign_role(user_id, role_id)

    async def remove_role(self, user_id: int, role_id: int) -> None:
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        await self.users.remove_role(user_id, role_id)

    # ── 角色/权限查询 ───────────────────────────────────────────────

    async def list_roles(self) -> list[Role]:
        return await self.roles.list_roles()

    async def list_permissions(self) -> list[Permission]:
        return await self.perms.list_permissions()

    # ── 序列化 ──────────────────────────────────────────────────────

    @staticmethod
    def _user_to_dict(user: User, role_codes: list[str], perm_codes: list[str]) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "roles": [
                {
                    "id": r.id,
                    "code": r.code,
                    "name": r.name,
                }
                for r in user.roles
            ],
            "role_codes": role_codes,
            "permissions": perm_codes,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        }

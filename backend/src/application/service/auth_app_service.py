"""认证授权 - 应用服务

AuthAppService 是用户登录、注册、刷新令牌、登出、用户列表/角色管理等的统一入口。
所有密码校验均通过基础设施层 infrastructure.security.password 完成。
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

import jwt as pyjwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.entity import (
    InvalidCredentialsError,
    Permission,
    Role,
    TokenInvalidError,
    User,
    UserAlreadyExistsError,
    UserInactiveError,
    UserNotFoundError,
)
from domain.auth.repository import (
    PermissionRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from infrastructure.persistence.models.user_role import RolePermissionDB
from infrastructure.persistence.models.user import (
    PermissionDB,
)
from infrastructure.persistence.repositories.auth_repository import (
    PermissionRepoImpl,
    RefreshTokenRepoImpl,
    RoleRepoImpl,
    UserRepoImpl,
)
from infrastructure.security.jwt_service import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from infrastructure.security.password import hash_password, verify_password


class AuthAppService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users: UserRepository = UserRepoImpl(session)
        self.roles: RoleRepository = RoleRepoImpl(session)
        self.perms: PermissionRepository = PermissionRepoImpl(session)
        self.refresh: RefreshTokenRepository = RefreshTokenRepoImpl(session)

    # ── 注册 ─────────────────────────────────────────────────────────

    async def register(
        self,
        *,
        email: str,
        username: str,
        password: str,
        nickname: Optional[str] = None,
    ) -> User:
        """注册新用户。

        - email / username 必须未占用
        - 自动绑定 'member' 角色(由 UserRepoImpl.create 完成)
        """
        if await self.users.find_by_email(email):
            raise UserAlreadyExistsError(field="邮箱", value=email)
        if await self.users.find_by_username(username):
            raise UserAlreadyExistsError(field="用户名", value=username)

        new_user = User(
            id=0,
            email=email,
            username=username,
            password_hash=hash_password(password),
            nickname=nickname or username,
            is_active=True,
            is_verified=False,
            roles=[],
        )
        created = await self.users.create(new_user)
        return created

    # ── 登录 ─────────────────────────────────────────────────────────

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> dict:
        """邮箱 + 密码登录。返回完整登录响应 dict。"""
        user = await self.users.find_by_email(email)
        # 即使用户不存在,也走一遍 bcrypt(避免时序攻击暴露"用户存在与否")
        if not user:
            hash_password(password)
            raise InvalidCredentialsError()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise UserInactiveError()

        # 加载角色 + 权限
        role_codes = [r.code for r in user.roles]
        perm_codes = await self._get_user_permissions(user)

        # 签发 token 对
        access_token, access_exp = create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            roles=role_codes,
            permissions=perm_codes,
        )
        refresh_token, jti, refresh_exp = create_refresh_token(user_id=user.id)
        await self.refresh.save(
            user_id=user.id,
            jti=jti,
            token_hash=hashlib.sha256(refresh_token.encode("utf-8")).hexdigest(),
            expires_at=refresh_exp.replace(tzinfo=None),
            user_agent=user_agent,
            ip=ip,
        )

        user.record_login(ip)
        await self.users.update(user)
        user.clear_events()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
            "user_info": self._user_to_dict(user, role_codes, perm_codes),
        }

    # ── refresh ───────────────────────────────────────────────────────

    async def refresh_token(self, refresh_token: str) -> dict:
        """refresh rotation: 撤销旧 jti,签发新一对 token。

        - jti 必须存在
        - 未撤销
        - 未过期
        - 旧 token 已被使用(reuse detection): 撤销该用户全部 token
        """
        try:
            claims = decode_token(refresh_token, expected_type="refresh")
        except pyjwt.ExpiredSignatureError:
            raise TokenInvalidError("已过期")
        except pyjwt.InvalidTokenError as e:
            raise TokenInvalidError(str(e))

        jti = claims["jti"]
        sub = int(claims["sub"])

        record = await self.refresh.find_by_jti(jti)
        if not record:
            raise TokenInvalidError("jti 不存在")
        # 校验 token_hash
        if record["token_hash"] != hashlib.sha256(refresh_token.encode("utf-8")).hexdigest():
            raise TokenInvalidError("token hash 不匹配")
        if record["revoked_at"] is not None:
            # 已被撤销 → 可能被盗用,撤销该用户所有 refresh token
            await self.refresh.revoke_all_for_user(sub)
            raise TokenInvalidError("refresh token 已被撤销,全设备下线")
        # expires_at 比较(naive datetime)
        if record["expires_at"] < datetime.utcnow():
            raise TokenInvalidError("已过期")

        user = await self.users.find_by_id(sub)
        if not user or not user.is_active:
            raise UserInactiveError()

        role_codes = [r.code for r in user.roles]
        perm_codes = await self._get_user_permissions(user)

        new_access, access_exp = create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            roles=role_codes,
            permissions=perm_codes,
        )
        new_refresh, new_jti, new_exp = create_refresh_token(user_id=user.id)
        await self.refresh.save(
            user_id=user.id,
            jti=new_jti,
            token_hash=hashlib.sha256(new_refresh.encode("utf-8")).hexdigest(),
            expires_at=new_exp.replace(tzinfo=None),
            user_agent=None,
            ip=None,
        )
        # 撤销旧 jti
        await self.refresh.revoke(jti, replaced_by_jti=new_jti)

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
        }

    # ── logout ───────────────────────────────────────────────────────

    async def logout(self, user_id: int) -> None:
        """登出:撤销该用户所有未撤销的 refresh token。"""
        await self.refresh.revoke_all_for_user(user_id)

    # ── 解析 access token(供 deps_auth) ─────────────────────────────

    async def parse_access_token(self, token: str) -> dict:
        """解码 access token claims。"""
        try:
            return decode_token(token, expected_type="access")
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
            perm_codes = await self._get_user_permissions(u)
            items.append(self._user_to_dict(u, role_codes, perm_codes))
        return items, total

    async def get_user_info(self, user_id: int) -> dict:
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        role_codes = [r.code for r in user.roles]
        perm_codes = await self._get_user_permissions(user)
        return self._user_to_dict(user, role_codes, perm_codes)

    # ── 写操作 ──────────────────────────────────────────────────────

    async def update_user_status(self, user_id: int, is_active: bool) -> dict:
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        user.is_active = is_active
        updated = await self.users.update(user)
        return {"id": updated.id, "is_active": updated.is_active}

    async def reset_user_password(self, user_id: int, new_password: str) -> None:
        user = await self.users.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(str(user_id))
        user.password_hash = hash_password(new_password)
        await self.users.update(user)
        # 强制重登:撤销该用户全部 refresh token
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

    # ── 内部:通过 user 的角色聚合权限码 ─────────────────────────────

    async def _get_user_permissions(self, user: User) -> list[str]:
        if not user.roles:
            return []
        role_ids = [r.id for r in user.roles]
        stmt = (
            select(PermissionDB.code)
            .join(RolePermissionDB, RolePermissionDB.permission_id == PermissionDB.id)
            .where(RolePermissionDB.role_id.in_(role_ids))
            .distinct()
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    @staticmethod
    def _user_to_dict(user: User, role_codes: list[str], perm_codes: list[str]) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
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
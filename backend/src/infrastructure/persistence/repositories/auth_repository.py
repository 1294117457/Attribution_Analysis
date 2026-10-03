"""认证授权 - 仓储实现(infra 层)

4 个 Repo 实现:
- UserRepoImpl        :  CRUD + 角色绑定(仍走 DB)
- RoleRepoImpl        :  CRUD(DB)
- PermissionRepoImpl  :  只读(DB)
- RefreshTokenRepoImpl:  refresh token 持久化(Redis) — 不再依赖 DB

均为 async,接受 AsyncSession。UserRepoImpl.create 完成后会自动绑定 'member' 角色。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select, update as sa_update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entitys.auth.entity import Permission, Role, User
from domain.entitys.auth.repository import (
    PermissionRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from infrastructure.adapter.cache.redis_cache import RedisCache, get_cache
from infrastructure.persistence.models.user import PermissionDB, RoleDB, UserDB
from infrastructure.persistence.models.user_role import RolePermissionDB, UserRoleDB


# ════════════════════════════════════════════════════════════════════════
# 工具
# ════════════════════════════════════════════════════════════════════════


def _role_to_vo(db: RoleDB) -> Role:
    return Role(
        id=db.id,
        code=db.code,
        name=db.name,
        description=db.description,
        is_system=db.is_system,
        sort_order=db.sort_order,
    )


def _perm_to_vo(db: PermissionDB) -> Permission:
    return Permission(
        id=db.id,
        code=db.code,
        resource=db.resource,
        action=db.action,
        name=db.name,
        description=db.description,
    )


def _user_to_vo(db: UserDB, roles: list[Role]) -> User:
    return User(
        id=db.id,
        email=db.email,
        password_hash=db.password_hash,
        nickname=db.nickname,
        avatar_url=db.avatar_url,
        is_active=db.is_active,
        is_verified=db.is_verified,
        last_login_at=db.last_login_at,
        last_login_ip=db.last_login_ip,
        created_at=db.created_at,
        updated_at=db.updated_at,
        roles=roles,
    )


async def _load_roles_for_user(session: AsyncSession, user_id: int) -> list[Role]:
    stmt = (
        select(RoleDB)
        .join(UserRoleDB, UserRoleDB.role_id == RoleDB.id)
        .where(UserRoleDB.user_id == user_id)
        .order_by(RoleDB.sort_order.asc(), RoleDB.id.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_role_to_vo(r) for r in rows]


# ════════════════════════════════════════════════════════════════════════
# User
# ════════════════════════════════════════════════════════════════════════


class UserRepoImpl(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, user_id: int) -> Optional[User]:
        db = await self.session.get(UserDB, user_id)
        if not db:
            return None
        roles = await _load_roles_for_user(self.session, user_id)
        return _user_to_vo(db, roles)

    async def find_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserDB).where(UserDB.email == email)
        db = (await self.session.execute(stmt)).scalars().first()
        if not db:
            return None
        roles = await _load_roles_for_user(self.session, db.id)
        return _user_to_vo(db, roles)

    async def create(self, user: User) -> User:
        db = UserDB(
            email=user.email,
            password_hash=user.password_hash,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
        )
        self.session.add(db)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise

        # 自动绑定 member 角色(注册即会员)
        member_role = (
            await self.session.execute(select(RoleDB).where(RoleDB.code == "member"))
        ).scalars().first()
        if member_role:
            self.session.add(UserRoleDB(user_id=db.id, role_id=member_role.id))
            await self.session.flush()

        roles = await _load_roles_for_user(self.session, db.id)
        return _user_to_vo(db, roles)

    async def update(self, user: User) -> User:
        db = await self.session.get(UserDB, user.id)
        if not db:
            return user
        db.nickname = user.nickname
        db.avatar_url = user.avatar_url
        db.is_active = user.is_active
        db.is_verified = user.is_verified
        db.last_login_at = user.last_login_at
        db.last_login_ip = user.last_login_ip
        await self.session.flush()
        # updated_at 由 DB 端 onupdate=func.now() 维护,flush 后该字段处于
        # expired 状态;若在 await 之后再读取会触发 lazy-load → MissingGreenlet。
        # 显式 refresh 一次以加载最新值。
        await self.session.refresh(db, attribute_names=["updated_at"])
        roles = await _load_roles_for_user(self.session, db.id)
        return _user_to_vo(db, roles)

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[User], int]:
        stmt = select(UserDB)
        count_stmt = select(func.count()).select_from(UserDB)

        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                (UserDB.email.ilike(like)) | (UserDB.nickname.ilike(like))
            )
            count_stmt = count_stmt.where(
                (UserDB.email.ilike(like)) | (UserDB.nickname.ilike(like))
            )
        if is_active is not None:
            stmt = stmt.where(UserDB.is_active == is_active)
            count_stmt = count_stmt.where(UserDB.is_active == is_active)

        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(UserDB.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.session.execute(stmt)).scalars().all()

        users: list[User] = []
        for r in rows:
            roles = await _load_roles_for_user(self.session, r.id)
            users.append(_user_to_vo(r, roles))
        return users, int(total)

    async def delete(self, user_id: int) -> None:
        stmt = delete(UserDB).where(UserDB.id == user_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def assign_role(self, user_id: int, role_id: int) -> None:
        # 幂等 INSERT
        stmt = (
            select(UserRoleDB)
            .where(UserRoleDB.user_id == user_id)
            .where(UserRoleDB.role_id == role_id)
        )
        exists = (await self.session.execute(stmt)).scalars().first()
        if exists:
            return
        self.session.add(UserRoleDB(user_id=user_id, role_id=role_id))
        await self.session.flush()

    async def remove_role(self, user_id: int, role_id: int) -> None:
        stmt = (
            delete(UserRoleDB)
            .where(UserRoleDB.user_id == user_id)
            .where(UserRoleDB.role_id == role_id)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def list_permission_codes_by_user(self, user_id: int) -> list[str]:
        """通过用户聚合的角色 join 出全部权限码（DDD.md §2.2 / §4）

        原实现位于 `AuthAppService._get_user_permissions`（AppService 直接 ORM join），
        现下沉到仓储实现，AppService 不再持有 session / ORM 模型。
        """
        stmt = (
            select(PermissionDB.code)
            .join(UserRoleDB, UserRoleDB.user_id == user_id)
            .join(
                RolePermissionDB,
                RolePermissionDB.role_id == UserRoleDB.role_id,
            )
            .where(PermissionDB.id == RolePermissionDB.permission_id)
            .distinct()
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)


# ════════════════════════════════════════════════════════════════════════
# Role
# ════════════════════════════════════════════════════════════════════════


class RoleRepoImpl(RoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, role_id: int) -> Optional[Role]:
        db = await self.session.get(RoleDB, role_id)
        return _role_to_vo(db) if db else None

    async def find_by_code(self, code: str) -> Optional[Role]:
        stmt = select(RoleDB).where(RoleDB.code == code)
        db = (await self.session.execute(stmt)).scalars().first()
        return _role_to_vo(db) if db else None

    async def list_roles(self) -> list[Role]:
        stmt = select(RoleDB).order_by(RoleDB.sort_order.asc(), RoleDB.id.asc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_role_to_vo(r) for r in rows]

    async def create(self, role: Role) -> Role:
        db = RoleDB(
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            sort_order=role.sort_order,
        )
        self.session.add(db)
        await self.session.flush()
        return _role_to_vo(db)

    async def update(self, role: Role) -> Role:
        db = await self.session.get(RoleDB, role.id)
        if not db:
            return role
        db.name = role.name
        db.description = role.description
        db.sort_order = role.sort_order
        await self.session.flush()
        return _role_to_vo(db)

    async def delete(self, role_id: int) -> None:
        stmt = delete(RoleDB).where(RoleDB.id == role_id).where(RoleDB.is_system.is_(False))
        await self.session.execute(stmt)
        await self.session.flush()


# ════════════════════════════════════════════════════════════════════════
# Permission
# ════════════════════════════════════════════════════════════════════════


class PermissionRepoImpl(PermissionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, perm_id: int) -> Optional[Permission]:
        db = await self.session.get(PermissionDB, perm_id)
        return _perm_to_vo(db) if db else None

    async def list_permissions(self) -> list[Permission]:
        stmt = select(PermissionDB).order_by(
            PermissionDB.resource.asc(),
            PermissionDB.id.asc(),
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_perm_to_vo(p) for p in rows]


# ════════════════════════════════════════════════════════════════════════
# RefreshToken(Redis 实现)
# ════════════════════════════════════════════════════════════════════════


class RefreshTokenRepoImpl(RefreshTokenRepository):
    """Refresh token 仓储(纯 Redis,无 DB 依赖)。

    数据结构:
    - revoked:{jti}                string "1",TTL = refresh 剩余有效期
    - user_refresh_tokens:{user_id}  set of jti,TTL = 7 天(同步 refresh 期限)

    接口约束:
    - 不再保存 token_hash / expires_at / user_agent / ip
      这些信息已经在 JWT claims 里,落库意义不大
    """

    # 集合 key 的 TTL 兜底(7 天),保证过期集合自动释放
    _SET_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        """为兼容旧的调用方 `RefreshTokenRepoImpl(session)` 保留 session 形参。

        注意:本类已切到 Redis,**不依赖**传入的 session(仅留签名兼容)。
        """
        self._legacy_session = session

    async def save(
        self,
        *,
        user_id: int,
        jti: str,
        expires_in_seconds: int,
    ) -> None:
        """登记新 refresh token:把 jti 加入用户的活跃 set。"""
        cache: RedisCache = await get_cache()
        set_key = f"user_refresh_tokens:{user_id}"
        await cache.sadd(set_key, jti)
        # 集合 TTL 与 refresh 期限一致
        await cache.expire(set_key, expires_in_seconds)

    async def is_active(self, jti: str) -> bool:
        """未撤销 → True。已撤销 / key 不存在 → False。"""
        cache: RedisCache = await get_cache()
        return not await cache.is_refresh_token_revoked(jti)

    async def revoke(self, jti: str, expires_in_seconds: int) -> None:
        """撤销该 jti(写黑名单)。"""
        cache: RedisCache = await get_cache()
        await cache.revoke_refresh_token(jti, ttl_seconds=expires_in_seconds)

    async def revoke_all_for_user(self, user_id: int) -> int:
        """撤销该用户所有活跃 refresh token(改密 / 封号场景)。"""
        cache: RedisCache = await get_cache()
        return await cache.revoke_all_user_refresh_tokens(user_id)
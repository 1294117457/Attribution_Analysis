"""认证授权 - 仓储实现(infra 层)

4 个 Repo 实现:
- UserRepoImpl        :  CRUD + 角色绑定
- RoleRepoImpl        :  CRUD
- PermissionRepoImpl :  只读
- RefreshTokenRepoImpl:  refresh token 持久化(SHA-256 哈希)

均为 async,接受 AsyncSession。UserRepoImpl.create 完成后会自动绑定 'member' 角色。
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select, update as sa_update, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.entity import Permission, Role, User
from domain.auth.repository import (
    PermissionRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from infrastructure.persistence.models.refresh_token import RefreshTokenDB
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
        username=db.username,
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

    async def find_by_username(self, username: str) -> Optional[User]:
        stmt = select(UserDB).where(UserDB.username == username)
        db = (await self.session.execute(stmt)).scalars().first()
        if not db:
            return None
        roles = await _load_roles_for_user(self.session, db.id)
        return _user_to_vo(db, roles)

    async def create(self, user: User) -> User:
        db = UserDB(
            email=user.email,
            username=user.username,
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
                (UserDB.email.ilike(like))
                | (UserDB.username.ilike(like))
                | (UserDB.nickname.ilike(like))
            )
            count_stmt = count_stmt.where(
                (UserDB.email.ilike(like))
                | (UserDB.username.ilike(like))
                | (UserDB.nickname.ilike(like))
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
# RefreshToken
# ════════════════════════════════════════════════════════════════════════


class RefreshTokenRepoImpl(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def save(
        self,
        *,
        user_id: int,
        jti: str,
        token_hash: str,
        expires_at: datetime,
        user_agent: Optional[str],
        ip: Optional[str],
    ) -> None:
        db = RefreshTokenDB(
            user_id=user_id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
        )
        self.session.add(db)
        await self.session.flush()

    async def find_by_jti(self, jti: str) -> Optional[dict]:
        stmt = select(RefreshTokenDB).where(RefreshTokenDB.jti == jti)
        db = (await self.session.execute(stmt)).scalars().first()
        if not db:
            return None
        return {
            "id": db.id,
            "user_id": db.user_id,
            "jti": db.jti,
            "token_hash": db.token_hash,
            "expires_at": db.expires_at,
            "revoked_at": db.revoked_at,
            "replaced_by_jti": db.replaced_by_jti,
        }

    async def revoke(self, jti: str, replaced_by_jti: Optional[str] = None) -> None:
        stmt = (
            sa_update(RefreshTokenDB)
            .where(RefreshTokenDB.jti == jti)
            .where(RefreshTokenDB.revoked_at.is_(None))
            .values(revoked_at=datetime.now(), replaced_by_jti=replaced_by_jti)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: int) -> None:
        stmt = (
            sa_update(RefreshTokenDB)
            .where(RefreshTokenDB.user_id == user_id)
            .where(RefreshTokenDB.revoked_at.is_(None))
            .values(revoked_at=datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.flush()
"""认证授权 ORM 模型 - sys_users / sys_roles / sys_permissions"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.base import Base


if TYPE_CHECKING:
    from infrastructure.persistence.models.user_role import (
        RolePermissionDB,
        UserRoleDB,
    )


class UserDB(Base):
    """用户表 - sys_users"""

    __tablename__ = "sys_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 关系
    user_roles: Mapped[list["UserRoleDB"]] = relationship(
        "UserRoleDB",
        primaryjoin="UserDB.id == UserRoleDB.user_id",
        foreign_keys="UserRoleDB.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RoleDB(Base):
    """角色表 - sys_roles"""

    __tablename__ = "sys_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 关系
    user_roles: Mapped[list["UserRoleDB"]] = relationship(
        "UserRoleDB", back_populates="role", cascade="all, delete-orphan"
    )
    role_permissions: Mapped[list["RolePermissionDB"]] = relationship(
        "RolePermissionDB", back_populates="role", cascade="all, delete-orphan"
    )


class PermissionDB(Base):
    """权限表 - sys_permissions"""

    __tablename__ = "sys_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    # 关系
    role_permissions: Mapped[list["RolePermissionDB"]] = relationship(
        "RolePermissionDB", back_populates="permission", cascade="all, delete-orphan"
    )
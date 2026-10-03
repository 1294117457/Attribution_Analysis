"""认证授权 ORM 模型 - sys_user_roles / sys_role_permissions 关联表"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.base import Base


class UserRoleDB(Base):
    """用户-角色关联表 - sys_user_roles"""

    __tablename__ = "sys_user_roles"
    __table_args__ = (
        # 唯一约束 — 让 SQL 中 ON CONFLICT (user_id, role_id) DO NOTHING 能命中
        UniqueConstraint("user_id", "role_id", name="uq_sys_user_roles_user_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    granted_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 关系
    user: Mapped["UserDB"] = relationship(
        "UserDB",
        primaryjoin="UserRoleDB.user_id == UserDB.id",
        foreign_keys="UserRoleDB.user_id",
        back_populates="user_roles",
    )
    role: Mapped["RoleDB"] = relationship(
        "RoleDB",
        back_populates="user_roles",
    )


class RolePermissionDB(Base):
    """角色-权限关联表 - sys_role_permissions"""

    __tablename__ = "sys_role_permissions"
    __table_args__ = (
        # 唯一约束 — 让 002_auth_system.sql 的 ON CONFLICT (role_id, permission_id) DO NOTHING 能命中
        # 修复：之前缺此约束导致 002_auth_system.sql 的子句 #15/#16/#17 全部 ON CONFLICT 失败
        UniqueConstraint("role_id", "permission_id", name="uq_sys_role_permissions_role_perm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sys_permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 关系
    role: Mapped["RoleDB"] = relationship(
        "RoleDB",
        back_populates="role_permissions",
    )
    permission: Mapped["PermissionDB"] = relationship(
        "PermissionDB", back_populates="role_permissions"
    )

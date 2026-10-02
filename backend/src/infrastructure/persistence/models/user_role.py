"""认证授权 ORM 模型 - sys_user_roles / sys_role_permissions 关联表"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.base import Base


class UserRoleDB(Base):
    """用户-角色关联表 - sys_user_roles"""

    __tablename__ = "sys_user_roles"
    __table_args__ = (
        # 唯一约束在 SQL 中显式声明;ORM 这里仅声明主键
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
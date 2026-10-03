"""认证授权实体 / 值对象 / 领域事件 / 异常 — 聚合根

User 是聚合根；Role / Permission 是值对象（只读/unchanged）。
AuthError 子类继承 DomainError，由 main.py 的统一 DomainError 处理器捕获为 400。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.base import AggregateRoot, DomainError, DomainEvent, ValueObject


# ════════════════════════════════════════════════════════════════════════
# 值对象
# ════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Role(ValueObject):
    """角色值对象"""

    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_system: bool = False
    sort_order: int = 0

    def _get_values(self) -> tuple:
        return (self.id, self.code, self.name)


@dataclass(frozen=True)
class Permission(ValueObject):
    """权限值对象"""

    id: int
    code: str
    resource: str
    action: str
    name: str
    description: Optional[str] = None

    def _get_values(self) -> tuple:
        return (self.id, self.code, self.resource, self.action)


# ════════════════════════════════════════════════════════════════════════
# 聚合根
# ════════════════════════════════════════════════════════════════════════


class User(AggregateRoot):
    """用户聚合根

    - 持有 roles（值对象集合）
    - can_login / has_role / validate_password 等业务方法
    - 不在 __init__ 中校验密码（允许已存在但 is_active=false 的用户不参与登录）

    2026-10-02 改造：去除 username 字段，仅以 email 作为唯一业务标识。
    """

    def __init__(
        self,
        *,
        id: int,
        email: str,
        password_hash: str,
        nickname: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_active: bool = True,
        is_verified: bool = False,
        last_login_at: Optional[datetime] = None,
        last_login_ip: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        roles: Optional[list[Role]] = None,
    ) -> None:
        super().__init__()
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.nickname = nickname
        self.avatar_url = avatar_url
        self.is_active = is_active
        self.is_verified = is_verified
        self.last_login_at = last_login_at
        self.last_login_ip = last_login_ip
        self.created_at = created_at
        self.updated_at = updated_at
        self.roles: list[Role] = roles or []

    # ── 业务方法 ────────────────────────────────────────────────────────

    def has_role(self, role_code: str) -> bool:
        return any(r.code == role_code for r in self.roles)

    def has_permission(self, perm_code: str) -> bool:
        # 直接判定：实际权限从应用服务 join 后注入；
        # 领域层不依赖 SQLAlchemy，这里仅按"用户聚合持有权限"语义保留接口备用
        return False

    def can_login(self) -> bool:
        """用户是否可登录（is_active=True 且至少有 1 个角色）。"""
        return self.is_active and len(self.roles) > 0

    def validate_password(self, plain: str, hasher) -> bool:
        """校验密码（明文 vs 存储的 hash）。"""
        return hasher(plain, self.password_hash)

    def record_login(self, ip: Optional[str]) -> None:
        """记录登录时间和 IP，发布领域事件。"""
        now = datetime.now()
        self.last_login_at = now
        self.last_login_ip = ip
        self.add_event(UserLoggedIn(user_id=self.id, ip=ip))


# ════════════════════════════════════════════════════════════════════════
# 领域事件
# ════════════════════════════════════════════════════════════════════════


@dataclass
class UserLoggedIn(DomainEvent):
    user_id: int = 0
    ip: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════
# 领域异常
# ════════════════════════════════════════════════════════════════════════


class AuthError(DomainError):
    """认证授权通用异常基类"""

    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        super().__init__(message=message, code=code)


class UserNotFoundError(AuthError):
    def __init__(self, identifier: str):
        super().__init__(
            message=f"用户不存在: {identifier}",
            code="USER_NOT_FOUND",
        )


class UserAlreadyExistsError(AuthError):
    def __init__(self, field: str, value: str):
        super().__init__(
            message=f"该{field}已被注册: {value}",
            code="USER_ALREADY_EXISTS",
        )


class InvalidCredentialsError(AuthError):
    def __init__(self):
        super().__init__(
            message="邮箱或密码错误",
            code="INVALID_CREDENTIALS",
        )


class UserInactiveError(AuthError):
    def __init__(self):
        super().__init__(
            message="账号已被禁用",
            code="USER_INACTIVE",
        )


class TokenExpiredError(AuthError):
    def __init__(self):
        super().__init__(
            message="令牌已过期",
            code="TOKEN_EXPIRED",
        )


class TokenInvalidError(AuthError):
    def __init__(self, reason: str = ""):
        super().__init__(
            message=f"令牌无效{(':'+reason) if reason else ''}",
            code="TOKEN_INVALID",
        )


class PermissionDeniedError(AuthError):
    def __init__(self, required: str):
        super().__init__(
            message=f"缺少权限: {required}",
            code="PERMISSION_DENIED",
        )

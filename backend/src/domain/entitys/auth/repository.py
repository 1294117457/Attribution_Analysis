"""认证授权 - 仓储接口（纯抽象）

按 DDD.md §3.1，repository 接口定义在 domain 层，由 infrastructure 实现。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.entitys.auth.entity import Permission, Role, User


class UserRepository(ABC):
    """用户仓储接口"""

    @abstractmethod
    async def find_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[User], int]: ...

    @abstractmethod
    async def delete(self, user_id: int) -> None: ...

    @abstractmethod
    async def assign_role(self, user_id: int, role_id: int) -> None:
        """绑定角色（幂等）。"""

    @abstractmethod
    async def remove_role(self, user_id: int, role_id: int) -> None:
        """解绑角色（幂等）。"""

    @abstractmethod
    async def list_permission_codes_by_user(self, user_id: int) -> list[str]:
        """通过用户聚合的角色 join 出全部权限码。

        原为 AuthAppService._get_user_permissions 中直接 SQLAlchemy join，
        现下沉到仓储实现，AppService 不再持有 session / ORM（DDD.md §4）。
        """


class RoleRepository(ABC):
    """角色仓储接口"""

    @abstractmethod
    async def find_by_id(self, role_id: int) -> Optional[Role]: ...

    @abstractmethod
    async def find_by_code(self, code: str) -> Optional[Role]: ...

    @abstractmethod
    async def list_roles(self) -> list[Role]: ...

    @abstractmethod
    async def create(self, role: Role) -> Role: ...

    @abstractmethod
    async def update(self, role: Role) -> Role: ...

    @abstractmethod
    async def delete(self, role_id: int) -> None: ...


class PermissionRepository(ABC):
    """权限仓储接口"""

    @abstractmethod
    async def find_by_id(self, perm_id: int) -> Optional[Permission]: ...

    @abstractmethod
    async def list_permissions(self) -> list[Permission]: ...


class RefreshTokenRepository(ABC):
    """refresh token 仓储接口（Redis 版）。

    接口设计原则：
    - 不再接收 token_hash / expires_at / user_agent / ip（jwt claims 自带 + 业务上不必落库）
    - 只暴露"该 jti 是否仍有效 / 撤销"两个动作

    关键安全机制：
    - revoked:{jti}    黑名单 KV，TTL = refresh 剩余有效期（jwt.exp 推断）
    - user_refresh_tokens:{user_id}  Set，记该用户所有 jti，改密时一键全撤销
    """

    @abstractmethod
    async def save(
        self,
        *,
        user_id: int,
        jti: str,
        expires_in_seconds: int,
    ) -> None:
        """登记一个新 refresh token（jti），并把 jti 加入用户的活跃集合。

        expires_in_seconds 决定 user_refresh_tokens Set 的 TTL，
        保证过期 Set 自动释放。
        """

    @abstractmethod
    async def is_active(self, jti: str) -> bool:
        """该 jti 是否"未撤销且仍存活"。"""

    @abstractmethod
    async def revoke(self, jti: str, expires_in_seconds: int) -> None:
        """撤销该 jti（写黑名单，TTL 与 refresh 剩余有效期一致）。"""

    @abstractmethod
    async def revoke_all_for_user(self, user_id: int) -> int:
        """撤销该用户所有活跃 refresh token。返回被撤销的数量。"""

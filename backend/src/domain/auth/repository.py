"""认证授权 - 仓储接口(纯抽象)"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from domain.auth.entity import Permission, Role, User


class UserRepository(ABC):
    """用户仓储接口"""

    @abstractmethod
    async def find_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    async def find_by_username(self, username: str) -> Optional[User]: ...

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
        """绑定角色(幂等)。"""

    @abstractmethod
    async def remove_role(self, user_id: int, role_id: int) -> None:
        """解绑角色(幂等)。"""


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
    """refresh token 仓储接口"""

    @abstractmethod
    async def save(
        self,
        *,
        user_id: int,
        jti: str,
        token_hash: str,
        expires_at: datetime,
        user_agent: Optional[str],
        ip: Optional[str],
    ) -> None: ...

    @abstractmethod
    async def find_by_jti(self, jti: str) -> Optional[dict]: ...

    @abstractmethod
    async def revoke(self, jti: str, replaced_by_jti: Optional[str] = None) -> None: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: int) -> None: ...
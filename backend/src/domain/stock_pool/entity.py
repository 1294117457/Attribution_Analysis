"""操作池 - 聚合根"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.base import AggregateRoot, DomainEvent
from domain.stock_pool.value_objects import PoolType, PoolMember


# ═══════════════════════════════════════════════════════════════════════════════
# 领域事件
# 注：使用 kw_only=True 避免与父类 DomainEvent.occurred_on（带默认值）冲突
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(kw_only=True)
class PoolCreated(DomainEvent):
    pool_id: int
    pool_name: str


@dataclass(kw_only=True)
class PoolRenamed(DomainEvent):
    pool_id: int
    new_name: str


@dataclass(kw_only=True)
class PoolArchived(DomainEvent):
    pool_id: int


@dataclass(kw_only=True)
class MemberAdded(DomainEvent):
    pool_id: int
    symbol: str


@dataclass(kw_only=True)
class MemberRemoved(DomainEvent):
    pool_id: int
    symbol: str


# ═══════════════════════════════════════════════════════════════════════════════
# 领域异常
# ═══════════════════════════════════════════════════════════════════════════════


class PoolDomainError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DuplicateMemberError(PoolDomainError):
    def __init__(self, symbol: str, pool_id: int):
        self.symbol = symbol
        self.pool_id = pool_id
        super().__init__(f"股票 {symbol} 已在池 {pool_id} 中")


class MemberNotFoundError(PoolDomainError):
    def __init__(self, symbol: str, pool_id: int):
        self.symbol = symbol
        self.pool_id = pool_id
        super().__init__(f"股票 {symbol} 不在池 {pool_id} 中")


class CannotDeleteDefaultPoolError(PoolDomainError):
    def __init__(self, pool_id: int):
        self.pool_id = pool_id
        super().__init__(f"无法删除默认池 {pool_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# StockPool 聚合根
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class StockPool(AggregateRoot):
    """操作池聚合根

    业务规则：
    1. 默认池不可删除
    2. 成员不能重复
    """

    id: int
    name: str
    pool_type: PoolType
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    is_default: bool = False
    is_archived: bool = False

    members: list[PoolMember] = field(default_factory=list)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    _next_sort_order: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)
        if self._next_sort_order == 0 and self.members:
            self._next_sort_order = max(m.sort_order for m in self.members) + 1

    # ── 工厂方法 ────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name: str,
        pool_type: str = "custom",
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        is_default: bool = False,
        id: int = 0,
    ) -> StockPool:
        now = datetime.now()
        pool = cls(
            id=id,
            name=name.strip(),
            pool_type=PoolType.from_code(pool_type),
            description=description,
            color=color,
            icon=icon,
            sort_order=0,
            is_default=is_default,
            is_archived=False,
            members=[],
            created_at=now,
            updated_at=now,
        )
        pool.add_event(PoolCreated(pool_id=pool.id, pool_name=pool.name))
        return pool

    @classmethod
    def reconstitute(
        cls,
        id: int,
        name: str,
        pool_type: str,
        description: Optional[str],
        color: Optional[str],
        icon: Optional[str],
        sort_order: int,
        is_default: bool,
        is_archived: bool,
        members: list[PoolMember],
        created_at: datetime,
        updated_at: datetime,
    ) -> StockPool:
        pool = cls(
            id=id,
            name=name,
            pool_type=PoolType.from_code(pool_type),
            description=description,
            color=color,
            icon=icon,
            sort_order=sort_order,
            is_default=is_default,
            is_archived=is_archived,
            members=members,
            created_at=created_at,
            updated_at=updated_at,
        )
        return pool

    # ── 业务行为 ─────────────────────────────────────────────────────────────

    def add_member(self, symbol: str, memo: str = "") -> PoolMember:
        symbol = symbol.strip()
        if any(m.symbol == symbol for m in self.members):
            raise DuplicateMemberError(symbol, self.id)

        member = PoolMember(
            symbol=symbol,
            memo=memo,
            sort_order=self._next_sort_order,
            added_at=datetime.now(),
        )
        self.members.append(member)
        self._next_sort_order += 1
        self._touch()
        self.add_event(MemberAdded(pool_id=self.id, symbol=symbol))
        return member

    def remove_member(self, symbol: str) -> PoolMember:
        symbol = symbol.strip()
        for i, m in enumerate(self.members):
            if m.symbol == symbol:
                removed = self.members.pop(i)
                self._touch()
                self.add_event(MemberRemoved(pool_id=self.id, symbol=symbol))
                return removed
        raise MemberNotFoundError(symbol, self.id)

    def update_member_memo(self, symbol: str, memo: str) -> None:
        for i, m in enumerate(self.members):
            if m.symbol == symbol:
                new_member = PoolMember(
                    symbol=m.symbol,
                    memo=memo,
                    sort_order=m.sort_order,
                    added_at=m.added_at,
                )
                self.members[i] = new_member
                self._touch()
                return
        raise MemberNotFoundError(symbol, self.id)

    def clear_members(self) -> list[PoolMember]:
        removed = self.members.copy()
        self.members.clear()
        self._touch()
        for m in removed:
            self.add_event(MemberRemoved(pool_id=self.id, symbol=m.symbol))
        return removed

    def rename(self, new_name: str) -> None:
        name = new_name.strip()
        if not name:
            raise ValueError("池名称不能为空")
        self.name = name
        self._touch()
        self.add_event(PoolRenamed(pool_id=self.id, new_name=self.name))

    def update_description(self, description: Optional[str]) -> None:
        self.description = description
        self._touch()

    def update_color(self, color: Optional[str]) -> None:
        self.color = color
        self._touch()

    def update_icon(self, icon: Optional[str]) -> None:
        self.icon = icon
        self._touch()

    def archive(self) -> None:
        self.is_archived = True
        self._touch()
        self.add_event(PoolArchived(pool_id=self.id))

    def unarchive(self) -> None:
        self.is_archived = False
        self._touch()

    # ── 查询方法 ─────────────────────────────────────────────────────────────

    def has_member(self, symbol: str) -> bool:
        return any(m.symbol == symbol for m in self.members)

    def get_member(self, symbol: str) -> Optional[PoolMember]:
        for m in self.members:
            if m.symbol == symbol:
                return m
        return None

    @property
    def member_count(self) -> int:
        return len(self.members)

    @property
    def symbols(self) -> list[str]:
        return [m.symbol for m in self.members]

    # ── 私有方法 ─────────────────────────────────────────────────────────────

    def _can_delete(self) -> bool:
        return not self.is_default

    def _validate_deletable(self) -> None:
        if not self._can_delete():
            raise CannotDeleteDefaultPoolError(self.id)

    def _touch(self) -> None:
        self.updated_at = datetime.now()

    # ── 序列化 ───────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "pool_type": self.pool_type.code,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "is_default": self.is_default,
            "is_archived": self.is_archived,
            "member_count": self.member_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def member_list_dict(self) -> list[dict]:
        return [
            {
                "symbol": m.symbol,
                "memo": m.memo,
                "sort_order": m.sort_order,
                "added_at": m.added_at,
            }
            for m in self.members
        ]

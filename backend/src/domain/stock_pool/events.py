"""操作池 - 领域事件"""

from dataclasses import dataclass
from domain.base import DomainEvent


@dataclass(kw_only=True)
class PoolCreated(DomainEvent):
    pool_id: int
    pool_name: str


@dataclass(kw_only=True)
class PoolRenamed(DomainEvent):
    pool_id: int
    new_name: str


@dataclass(kw_only=True)
class PoolDeleted(DomainEvent):
    pool_id: int


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


@dataclass(kw_only=True)
class PoolOperationStarted(DomainEvent):
    op_id: int
    pool_id: int
    operation_type: str
    total: int


@dataclass(kw_only=True)
class PoolOperationProgress(DomainEvent):
    op_id: int
    done: int
    total: int
    failed: int


@dataclass(kw_only=True)
class PoolOperationFinished(DomainEvent):
    op_id: int
    pool_id: int
    status: str
    success_count: int
    failed_count: int

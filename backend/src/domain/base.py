"""领域层基类

领域层不依赖任何外部框架（SQLAlchemy、FastAPI、Pydantic 等）。
仅使用 Python 标准库和 dataclasses。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ════════════════════════════════════════════════════════════════
# Entity / AggregateRoot 基类
# 注意：不使用 @dataclass 和抽象方法，以避免 dataclass 继承时的字段顺序冲突
# ════════════════════════════════════════════════════════════════

class Entity(ABC):
    """实体基类

    实体具有唯一标识，其相等性基于标识而非属性。
    子类应定义 `id` 属性。
    """

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class AggregateRoot(Entity, ABC):
    """聚合根基类

    聚合根是聚合内唯一可以外部引用的实体。
    聚合根负责维护聚合内对象的一致性。
    """

    def __init__(self):
        self._domain_events: list = []

    def add_event(self, event: "DomainEvent") -> None:
        """添加领域事件"""
        self._domain_events.append(event)

    def clear_events(self) -> list:
        """获取并清除所有事件（用于发布）"""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    @property
    def domain_events(self) -> list:
        """获取所有未发布的领域事件"""
        return self._domain_events.copy()


# ════════════════════════════════════════════════════════════════
# 值对象基类
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ValueObject(ABC):
    """值对象基类

    值对象无唯一标识，其相等性基于属性值。
    使用 frozen=True 使其不可变。
    """

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self._get_values() == other._get_values()

    def __hash__(self) -> int:
        return hash(self._get_values())

    @abstractmethod
    def _get_values(self) -> tuple:
        """返回用于比较的属性元组"""
        ...


# ════════════════════════════════════════════════════════════════
# 领域事件基类
# ════════════════════════════════════════════════════════════════

@dataclass
class DomainEvent:
    """领域事件基类"""

    occurred_on: datetime = field(default_factory=datetime.now)

    @property
    def event_type(self) -> str:
        return type(self).__name__

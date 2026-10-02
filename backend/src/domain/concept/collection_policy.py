"""概念采集保护策略（领域知识）

业务规则（采集时的领域保护）：
- 清单缩量保护：清单数量低于库中活跃数 × guard 时不下线（避免问财接口返回不全导致误下线）
- 成分股骤降保护：旧数量超过 min 且新数量低于旧 × guard 时不替换（避免接口异常导致关系丢失）

实现为领域服务（DDD §3.2）：纯函数式，无状态，可独立单测。

配套设计文档：docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.4
"""
from __future__ import annotations

from typing import Optional


# 领域常量（业务规则阈值）
DEFAULT_LIST_SHRINK_GUARD: float = 0.8
"""清单缩量保护阈值：新清单数量 < 旧活跃数 × 此值时不下线"""

DEFAULT_MEMBER_SHRINK_MIN: int = 20
"""成分股骤降保护阈值：旧成员数超过此值且新成员数低于旧 × guard 时不替换"""

DEFAULT_MEMBER_SHRINK_GUARD: float = 0.5
"""成分股骤降保护阈值：新成员数 < 旧成员数 × 此值时不替换"""


class ConceptCollectionPolicy:
    """概念采集保护策略领域服务

    提供"采集时应不应该覆盖库中数据"的业务判断。
    所有阈值通过构造参数注入，便于不同数据源（问财 / 同花顺）独立调参。

    使用示例：
        policy = ConceptCollectionPolicy()
        if policy.should_skip_member_sync(old_count=100, new_count=30):
            # 成分股骤降，可能是接口异常，保留旧关系
            ...
    """

    def __init__(
        self,
        list_shrink_guard: float = DEFAULT_LIST_SHRINK_GUARD,
        member_shrink_min: int = DEFAULT_MEMBER_SHRINK_MIN,
        member_shrink_guard: float = DEFAULT_MEMBER_SHRINK_GUARD,
    ) -> None:
        self._list_shrink_guard = list_shrink_guard
        self._member_shrink_min = member_shrink_min
        self._member_shrink_guard = member_shrink_guard

    def should_skip_list_update(
        self,
        old_active_count: int,
        new_listing_count: int,
    ) -> bool:
        """判断是否跳过清单下线（避免接口返回不全导致误下线）

        Args:
            old_active_count: 库中当前活跃概念数
            new_listing_count: 这次接口返回的概念数

        Returns:
            True 表示应该跳过下线（疑似接口返回不全）
        """
        if old_active_count <= 0:
            return False
        return new_listing_count < old_active_count * self._list_shrink_guard

    def should_skip_member_sync(
        self,
        old_member_count: int,
        new_member_count: int,
    ) -> bool:
        """判断是否跳过成分股替换（避免接口异常导致关系丢失）

        Args:
            old_member_count: 库中现有成员数
            new_member_count: 这次接口返回的成员数

        Returns:
            True 表示应该跳过替换（疑似接口异常）
        """
        if old_member_count <= self._member_shrink_min:
            return False
        return new_member_count < old_member_count * self._member_shrink_guard


__all__ = [
    "ConceptCollectionPolicy",
    "DEFAULT_LIST_SHRINK_GUARD",
    "DEFAULT_MEMBER_SHRINK_MIN",
    "DEFAULT_MEMBER_SHRINK_GUARD",
]
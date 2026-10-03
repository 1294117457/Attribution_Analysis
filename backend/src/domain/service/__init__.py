"""领域服务（跨聚合根或跨实体的纯算法）

按 DDD.md §3.2：
- 只有跨聚合根 / 跨多实体的通用算法才放这里
- 输入是 entity / VO，输出是新 VO 或新 entity 属性
- 不允许副作用（无 IO、无状态变更），无外部依赖
"""
from domain.service.concept_brief_service import (
    DEFAULT_TOP_K,
    ConceptBriefService,
)
from domain.service.concept_collection_policy import (
    DEFAULT_LIST_SHRINK_GUARD,
    DEFAULT_MEMBER_SHRINK_GUARD,
    DEFAULT_MEMBER_SHRINK_MIN,
    ConceptCollectionPolicy,
)
from domain.service.indicator_calculator import (
    INDICATOR_COLUMNS,
    IndicatorCalculator,
)
from domain.service.market_session import (
    is_trading_time,
    market_now,
    ttl_for,
)
from domain.service.signal_detector import (
    SignalDetector,
    TechnicalSummary,
)

__all__ = [
    # concept
    "ConceptBriefService",
    "ConceptCollectionPolicy",
    "DEFAULT_LIST_SHRINK_GUARD",
    "DEFAULT_MEMBER_SHRINK_GUARD",
    "DEFAULT_MEMBER_SHRINK_MIN",
    "DEFAULT_TOP_K",
    # kline
    "INDICATOR_COLUMNS",
    "IndicatorCalculator",
    "SignalDetector",
    "TechnicalSummary",
    # market
    "is_trading_time",
    "market_now",
    "ttl_for",
]

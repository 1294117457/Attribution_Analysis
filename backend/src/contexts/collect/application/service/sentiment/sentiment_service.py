"""SentimentService：情绪面 service（占位，无 fetcher）"""
from __future__ import annotations

import logging

from contexts.collect.application.service.base import CollectResult, ServiceKind, ServiceMeta

logger = logging.getLogger(__name__)


class SentimentService:
    META = ServiceMeta(
        name='sentiment',
        facet='sentiment',
        label='情绪面',
        description='占位（暂无 fetcher）',
        kind=ServiceKind.FULL_REFRESH,
    )

    def __init__(self) -> None:
        """空占位 —— 无 fetcher、无 cache 依赖。"""

    async def collect(self, params: dict) -> CollectResult:
        return CollectResult(skip=1, message="sentiment 暂无 fetcher")


__all__ = ["SentimentService"]

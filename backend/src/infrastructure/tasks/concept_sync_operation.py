"""概念同步任务操作

配套设计文档：
  docs/dev/06gainian/02-infrastructure-design.md §5
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from domain.concept.schemas import ConceptListBO, ConceptStockBO
from domain.concept.repository import ConceptRepository
from infrastructure.collectors.akshare.fetcher import AkShareConceptFetcher

logger = logging.getLogger(__name__)


@dataclass
class ConceptSyncResult:
    """同步结果"""
    total_concepts: int = 0
    total_members: int = 0
    failed_concepts: list[str] = field(default_factory=list)
    elapsed_ms: int = 0
    synced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConceptSyncOperation:
    """概念同步任务

    步骤：
    1. fetch_concept_list → 全量概念清单
    2. 对每个概念 upsert_concept + upsert_members
    3. 统计失败项，记录结果
    """

    def __init__(
        self,
        repo: ConceptRepository,
        fetcher: Optional[AkShareConceptFetcher] = None,
    ):
        self._repo = repo
        self._fetcher = fetcher or AkShareConceptFetcher()

    async def sync_all(self) -> ConceptSyncResult:
        """全量同步所有概念"""
        start = time.time()
        result = ConceptSyncResult()

        # 1. 拉概念清单
        concept_bos = self._fetcher.fetch_concept_list()
        result.total_concepts = len(concept_bos)
        logger.info("全量同步：获取 %d 个概念", result.total_concepts)

        # 2. 逐个同步
        for i, bo in enumerate(concept_bos):
            try:
                member_count = await self._sync_one(bo)
                result.total_members += member_count
            except Exception as e:
                logger.warning("同步概念 %s 失败: %s", bo.name, e)
                result.failed_concepts.append(bo.name)

            if (i + 1) % 50 == 0:
                logger.info("进度: %d/%d", i + 1, result.total_concepts)

        result.elapsed_ms = int((time.time() - start) * 1000)
        result.synced_at = datetime.now(timezone.utc)
        return result

    async def _sync_one(self, bo: ConceptListBO) -> int:
        """同步单个概念及其成分股，返回成员数量"""
        # 1. upsert 概念
        concept = bo.to_entity()
        concept = await self._repo.upsert_concept(concept)

        # 2. 拉成分股
        stock_bos = self._fetcher.fetch_concept_stocks(bo.name)
        concept.mark_synced(member_count=len(stock_bos))
        await self._repo.upsert_concept(concept)  # 更新 stock_count

        # 3. upsert 成员
        members = [bo.to_entity(concept.id) for bo in stock_bos]
        return await self._repo.upsert_members(concept.id, members)

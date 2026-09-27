"""概念相关 sync operations（09concept 新增）

包含 3 个采集编排类：
- ConceptMembershipSyncOperation  : 枚举股票 → adata THS 反查 → 累加 M:N
- ConceptSnapshotSyncOperation    : 枚举概念 → akshare THS info → 写入快照
- ConceptIndexTHSyncOperation     : 枚举概念 → akshare THS index → 写入日 K
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from domain.concept.entity import ConceptSource
from domain.concept.schemas import (
    ConceptIndexTHBO,
    ConceptSnapshotBO,
)
from infrastructure.adapter.adata.fetcher import AdataConceptFetcher
from infrastructure.adapter.akshare.fetcher import AkShareConceptFetcher
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Membership：枚举股票 → adata THS 反查 → 累加写入 stock_concept_members
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class MembershipSyncResult:
    """成分股反查同步结果"""

    total_stocks: int = 0
    success_stocks: int = 0
    failed_stocks: list[str] = field(default_factory=list)
    new_concepts: int = 0
    new_members: int = 0
    elapsed_ms: int = 0
    synced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConceptMembershipSyncOperation:
    """成分股 M:N 反查同步

    步骤：
    1. 从 DB 拉所有 stock_infos (list_status='L') 的 symbol
    2. 逐只股票调 adata.get_concept_ths(symbol)
    3. 对返回的每个概念：
       a. 若 (name, ths) 不存在 → upsert_concept 入库
       b. 拿 concept_id，upsert_single_member 累加写入

    性能：5000 × ~0.4s = 约 33 分钟全量
    增量：仅同步 first_seen_at > 上次成功时间的股票（v1.1 再实现）

    失败容忍：单只股票失败 → 累计到 failed_stocks，不中断
    """

    def __init__(
        self,
        repo: ConceptRepoImpl,
        adata_fetcher: AdataConceptFetcher,
        stock_info_repo=None,
    ):
        self._repo = repo
        self._adata = adata_fetcher
        self._stock_info_repo = stock_info_repo

    async def _list_all_stock_symbols(self) -> list[str]:
        """列出所有 active 股票 symbol（list_status='L'）

        优先用 stock_info_repo，否则用 SQL 直查。
        """
        if self._stock_info_repo is not None and hasattr(
            self._stock_info_repo, "list_active_symbols"
        ):
            return await self._stock_info_repo.list_active_symbols()

        # Fallback：用 SQL 直接查（避免在概念上下文里 import stock_info_repo）
        from sqlalchemy import text as sql_text
        stmt = sql_text(
            "SELECT symbol FROM stock_infos "
            "WHERE list_status = 'L' AND symbol ~ '^[0-9]{6}$' "
            "ORDER BY symbol"
        )
        rows = (await self._repo._session.execute(stmt)).scalars().all()
        return [str(r) for r in rows]

    async def sync_membership(
        self,
        limit: Optional[int] = None,
    ) -> MembershipSyncResult:
        """执行成分股反查同步

        Args:
            limit: 仅同步前 N 只股票（测试用），None 全量
        """
        start = time.time()
        result = MembershipSyncResult()

        try:
            symbols = await self._list_all_stock_symbols()
        except Exception as e:
            logger.error("拉股票清单失败: %s", e)
            return result

        if limit is not None:
            symbols = symbols[:limit]

        result.total_stocks = len(symbols)
        logger.info("MembershipSync 启动: %d 只股票", result.total_stocks)

        for i, symbol in enumerate(symbols):
            try:
                added = await self._sync_one_stock(symbol)
                result.new_members += added
                result.success_stocks += 1
            except Exception as e:
                logger.warning("反查 %s 失败: %s", symbol, str(e)[:200])
                result.failed_stocks.append(symbol)

            if (i + 1) % 100 == 0:
                logger.info(
                    "MembershipSync 进度 %d/%d (成功%d 失败%d 新增关联%d)",
                    i + 1, result.total_stocks,
                    result.success_stocks, len(result.failed_stocks),
                    result.new_members,
                )

        result.elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "MembershipSync 完成: %d 成功 / %d 失败 / %d 新增关联 / %dms",
            result.success_stocks,
            len(result.failed_stocks),
            result.new_members,
            result.elapsed_ms,
        )
        return result

    async def _sync_one_stock(self, symbol: str) -> int:
        """处理一只股票：反查 → upsert 概念 → 累加 members

        Returns: 新增关联数（已存在的不计）
        """
        # 1. adata 反查（同步调用，包到线程池避免阻塞 event loop）
        loop = asyncio.get_event_loop()
        bos = await loop.run_in_executor(
            None, self._adata.fetch_concepts_by_stock, symbol
        )
        if not bos:
            return 0

        added_count = 0
        for bo in bos:
            # 2. 概念入库（upsert_concept 自带去重）
            from domain.concept.entity import Concept
            concept = Concept.create(
                name=bo.name,
                source=bo.source,  # THS（adata.get_concept_ths 标记）
                description=bo.reason,  # 入选理由入库
            )
            concept = await self._repo.upsert_concept(concept)

            # 3. 单条插入 M:N
            inserted = await self._repo.upsert_single_member(
                symbol=symbol,
                concept_id=concept.id,
                source=concept.source,
            )
            if inserted:
                added_count += 1

        return added_count


# ═══════════════════════════════════════════════════════════════════════════════
#  Snapshot：枚举概念 → akshare THS info → 写入快照
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SnapshotSyncResult:
    success: int = 0
    failed: int = 0
    failed_names: list[str] = field(default_factory=list)
    elapsed_ms: int = 0
    synced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConceptSnapshotSyncOperation:
    """概念行情快照同步（每 5 分钟）

    步骤：
    1. 拉所有 active 概念名
    2. 逐个调 akshare concept_info_ths(name)
    3. 解析 → upsert_snapshot
    """

    def __init__(
        self,
        repo: ConceptRepoImpl,
        akshare_fetcher: AkShareConceptFetcher,
    ):
        self._repo = repo
        self._ak = akshare_fetcher

    async def sync_snapshots(
        self,
        limit: Optional[int] = None,
    ) -> SnapshotSyncResult:
        start = time.time()
        result = SnapshotSyncResult()

        try:
            names = await self._repo.list_active_concept_names(source="ths")
        except Exception as e:
            logger.error("拉概念清单失败: %s", e)
            return result

        if limit is not None:
            names = names[:limit]

        logger.info("SnapshotSync 启动: %d 个概念", len(names))

        loop = asyncio.get_event_loop()
        for i, name in enumerate(names):
            try:
                bo = await loop.run_in_executor(
                    None, self._ak.fetch_concept_info_ths, name
                )
                if bo is None:
                    result.failed += 1
                    result.failed_names.append(name)
                    continue
                await self._repo.upsert_snapshot(bo)
                result.success += 1
            except Exception as e:
                logger.warning("行情 %s 失败: %s", name, str(e)[:200])
                result.failed += 1
                result.failed_names.append(name)

            if (i + 1) % 50 == 0:
                logger.info(
                    "SnapshotSync 进度 %d/%d (成功%d 失败%d)",
                    i + 1, len(names), result.success, result.failed,
                )

        result.elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "SnapshotSync 完成: %d 成功 / %d 失败 / %dms",
            result.success, result.failed, result.elapsed_ms,
        )
        return result


# ═══════════════════════════════════════════════════════════════════════════════
#  IndexTH：枚举概念 → akshare THS index → 写入日 K
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class IndexTHSyncResult:
    success: int = 0
    failed: int = 0
    failed_names: list[str] = field(default_factory=list)
    rows_total: int = 0
    elapsed_ms: int = 0
    synced_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConceptIndexTHSyncOperation:
    """概念指数日 K 同步（按需触发）

    步骤：
    1. 拉所有 active 概念名
    2. 逐个调 akshare concept_index_ths(name, start, end)
    3. upsert_index_th（按 (name, date) 冲突更新）
    """

    def __init__(
        self,
        repo: ConceptRepoImpl,
        akshare_fetcher: AkShareConceptFetcher,
        default_lookback_days: int = 365,
    ):
        self._repo = repo
        self._ak = akshare_fetcher
        self._lookback = default_lookback_days

    async def sync_index_th(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> IndexTHSyncResult:
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=self._lookback)

        start = time.time()
        result = IndexTHSyncResult()

        try:
            names = await self._repo.list_active_concept_names(source="ths")
        except Exception as e:
            logger.error("拉概念清单失败: %s", e)
            return result

        if limit is not None:
            names = names[:limit]

        logger.info(
            "IndexTHSync 启动: %d 个概念 [%s, %s]",
            len(names), start_date, end_date,
        )

        loop = asyncio.get_event_loop()
        for i, name in enumerate(names):
            try:
                bos = await loop.run_in_executor(
                    None,
                    self._ak.fetch_concept_index_ths,
                    name,
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d"),
                )
                if bos:
                    written = await self._repo.upsert_index_th(bos)
                    result.rows_total += written
                    result.success += 1
                else:
                    result.failed += 1
                    result.failed_names.append(name)
            except Exception as e:
                logger.warning("日 K %s 失败: %s", name, str(e)[:200])
                result.failed += 1
                result.failed_names.append(name)

            if (i + 1) % 50 == 0:
                logger.info(
                    "IndexTHSync 进度 %d/%d (成功%d 失败%d 行数%d)",
                    i + 1, len(names), result.success, result.failed, result.rows_total,
                )

        result.elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "IndexTHSync 完成: %d 成功 / %d 失败 / %d 行 / %dms",
            result.success, result.failed, result.rows_total, result.elapsed_ms,
        )
        return result

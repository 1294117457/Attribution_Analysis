"""概念采集任务（09concept 新增）

3 个 BaseCollectTask 子类，对应采集管理 UI 的 3 个子任务：
- MembershipCollectTask  概念-股票 M:N 反查累加（adata THS）
- SnapshotCollectTask    概念行情快照采集（akshare THS info）
- IndexTHCollectTask     概念指数日 K 采集（akshare THS index）

配套设计文档：docs/dev/09concept/02-class-design.md §7
"""

from __future__ import annotations

import asyncio
import logging

from infrastructure.adapter.adata.fetcher import AdataConceptFetcher
from infrastructure.adapter.akshare.fetcher import AkShareConceptFetcher
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    is_cancelled,
)
from infrastructure.adapter.scheduler.concept_sync_operations_v2 import (
    ConceptIndexTHSyncOperation,
    ConceptMembershipSyncOperation,
    ConceptSnapshotSyncOperation,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. MembershipCollectTask — 概念-股票 M:N 反查累加
# ═══════════════════════════════════════════════════════════════════════════════


class MembershipCollectTask(BaseCollectTask):
    """概念-股票 M:N 反查累加采集（adata THS 同源）

    单元 = 每只股票
    并发 = 顺序循环（adata 接口限频 0.3s）
    失败 = 累计到 failed_stocks，不中断
    """

    name = "concept_membership"

    def __init__(self) -> None:
        super().__init__()
        self._adata = AdataConceptFetcher()

    async def estimate_total(self, params: dict) -> int:
        """从 stock_infos 拉 active 股票数量"""
        from sqlalchemy import text as sql_text
        try:
            async with AsyncSessionLocal() as session:
                stmt = sql_text(
                    "SELECT COUNT(*) FROM stock_infos "
                    "WHERE list_status = 'L' AND symbol ~ '^[0-9]{6}$'"
                )
                result = await session.execute(stmt)
                return int(result.scalar_one())
        except Exception as e:
            logger.warning("estimate_total 拉股票数失败: %s", e)
            return 0

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        limit = params.get("limit")  # 测试用：仅同步前 N 只

        try:
            async with AsyncSessionLocal() as session:
                repo = ConceptRepoImpl(session)
                op = ConceptMembershipSyncOperation(repo=repo, adata_fetcher=self._adata)

                # 列出所有股票（带限制）
                symbols = await op._list_all_stock_symbols()
                if limit is not None:
                    symbols = symbols[: int(limit)]

                total = len(symbols)
                logger.info(
                    "MembershipCollect task %d 启动: %d 只股票 (limit=%s)",
                    self._task_id, total, limit,
                )

                success = fail = new_members = 0
                for i, symbol in enumerate(symbols):
                    if is_cancelled(self._task_id):
                        raise Cancelled()
                    try:
                        added = await op._sync_one_stock(symbol)
                        new_members += added
                        await on_unit_done(
                            UnitResult(
                                success=True, detail=symbol, saved_count=added,
                            ),
                            symbol,
                        )
                        success += 1
                    except Exception as e:
                        logger.warning("反查 %s 失败: %s", symbol, str(e)[:200])
                        await on_unit_done(
                            UnitResult(success=False, detail=symbol, error=str(e)),
                            symbol,
                        )
                        fail += 1

                    if (i + 1) % 100 == 0:
                        logger.info(
                            "MembershipCollect 进度 %d/%d (成功%d 失败%d 新增%d)",
                            i + 1, total, success, fail, new_members,
                        )

                return TaskSummary(
                    success=success,
                    fail=fail,
                    total_count=total,
                    message=(
                        f"完成: 成功 {success}, 失败 {fail}, "
                        f"新增关联 {new_members}"
                    ),
                )
        except Cancelled:
            raise
        except Exception as e:
            logger.exception("MembershipCollect task %d 异常", self._task_id)
            return TaskSummary(success=0, fail=0, message=f"任务异常: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SnapshotCollectTask — 概念行情快照
# ═══════════════════════════════════════════════════════════════════════════════


class SnapshotCollectTask(BaseCollectTask):
    """概念行情快照采集（akshare THS info）

    单元 = 每个概念
    """

    name = "concept_snapshot"

    def __init__(self) -> None:
        super().__init__()
        self._ak = AkShareConceptFetcher()

    async def estimate_total(self, params: dict) -> int:
        try:
            async with AsyncSessionLocal() as session:
                repo = ConceptRepoImpl(session)
                names = await repo.list_active_concept_names(source="ths")
                return len(names)
        except Exception as e:
            logger.warning("estimate_total 拉概念数失败: %s", e)
            return 0

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        limit = params.get("limit")
        try:
            async with AsyncSessionLocal() as session:
                repo = ConceptRepoImpl(session)
                op = ConceptSnapshotSyncOperation(repo=repo, akshare_fetcher=self._ak)
                names = await repo.list_active_concept_names(source="ths")
                if limit is not None:
                    names = names[: int(limit)]

                total = len(names)
                logger.info(
                    "SnapshotCollect task %d 启动: %d 个概念",
                    self._task_id, total,
                )

                loop = asyncio.get_event_loop()
                success = fail = 0
                for i, name in enumerate(names):
                    if is_cancelled(self._task_id):
                        raise Cancelled()
                    try:
                        bo = await loop.run_in_executor(
                            None, self._ak.fetch_concept_info_ths, name,
                        )
                        if bo is None:
                            raise RuntimeError("概念行情为空")
                        await repo.upsert_snapshot(bo)
                        await on_unit_done(
                            UnitResult(success=True, detail=name, saved_count=1),
                            name,
                        )
                        success += 1
                    except Exception as e:
                        logger.warning("行情 %s 失败: %s", name, str(e)[:200])
                        await on_unit_done(
                            UnitResult(success=False, detail=name, error=str(e)),
                            name,
                        )
                        fail += 1

                    if (i + 1) % 50 == 0:
                        logger.info(
                            "SnapshotCollect 进度 %d/%d (成功%d 失败%d)",
                            i + 1, total, success, fail,
                        )

                return TaskSummary(
                    success=success,
                    fail=fail,
                    total_count=total,
                    message=f"完成: 成功 {success}, 失败 {fail}",
                )
        except Cancelled:
            raise
        except Exception as e:
            logger.exception("SnapshotCollect task %d 异常", self._task_id)
            return TaskSummary(success=0, fail=0, message=f"任务异常: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. IndexTHCollectTask — 概念指数日 K
# ═══════════════════════════════════════════════════════════════════════════════


class IndexTHCollectTask(BaseCollectTask):
    """概念指数日 K 采集（akshare THS index）

    单元 = 每个概念 × 日 K 行数（一次 upsert 算 1 个 unit）
    """

    name = "concept_index_th"

    def __init__(self) -> None:
        super().__init__()
        self._ak = AkShareConceptFetcher()

    async def estimate_total(self, params: dict) -> int:
        try:
            async with AsyncSessionLocal() as session:
                repo = ConceptRepoImpl(session)
                names = await repo.list_active_concept_names(source="ths")
                return len(names)
        except Exception as e:
            logger.warning("estimate_total 拉概念数失败: %s", e)
            return 0

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        limit = params.get("limit")
        from datetime import date, timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        try:
            async with AsyncSessionLocal() as session:
                repo = ConceptRepoImpl(session)
                op = ConceptIndexTHSyncOperation(repo=repo, akshare_fetcher=self._ak)
                names = await repo.list_active_concept_names(source="ths")
                if limit is not None:
                    names = names[: int(limit)]

                total = len(names)
                logger.info(
                    "IndexTHCollect task %d 启动: %d 个概念 [%s, %s]",
                    self._task_id, total, start_date, end_date,
                )

                loop = asyncio.get_event_loop()
                success = fail = rows_total = 0
                for i, name in enumerate(names):
                    if is_cancelled(self._task_id):
                        raise Cancelled()
                    try:
                        bos = await loop.run_in_executor(
                            None,
                            self._ak.fetch_concept_index_ths,
                            name,
                            start_date.strftime("%Y%m%d"),
                            end_date.strftime("%Y%m%d"),
                        )
                        if not bos:
                            raise RuntimeError("日 K 为空")
                        written = await repo.upsert_index_th(bos)
                        rows_total += written
                        await on_unit_done(
                            UnitResult(
                                success=True, detail=name, saved_count=written,
                            ),
                            name,
                        )
                        success += 1
                    except Exception as e:
                        logger.warning("日 K %s 失败: %s", name, str(e)[:200])
                        await on_unit_done(
                            UnitResult(success=False, detail=name, error=str(e)),
                            name,
                        )
                        fail += 1

                    if (i + 1) % 50 == 0:
                        logger.info(
                            "IndexTHCollect 进度 %d/%d (成功%d 失败%d 行数%d)",
                            i + 1, total, success, fail, rows_total,
                        )

                return TaskSummary(
                    success=success,
                    fail=fail,
                    total_count=total,
                    message=(
                        f"完成: 成功 {success}, 失败 {fail}, "
                        f"写入 {rows_total} 行"
                    ),
                )
        except Cancelled:
            raise
        except Exception as e:
            logger.exception("IndexTHCollect task %d 异常", self._task_id)
            return TaskSummary(success=0, fail=0, message=f"任务异常: {e}")

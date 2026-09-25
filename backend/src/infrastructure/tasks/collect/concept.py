"""概念全量同步任务（接入采集管理 tab）

本次新增：让概念同步跑在采集管理 tab 里，可触发 / 可取消 / 可追溯。
复用既有 ConceptSyncOperation._sync_one() 业务逻辑，零业务改动。

关键约束：
  · 每个概念独立 session（避免一个失败回滚全部）
  · 复用 ConceptSyncOperation._sync_one()，业务代码不重写
  · on_unit_done() 通过基类注入 task_id，本类调 is_cancelled(self._task_id)

配套设计文档：
  docs/dev/07collect-class/01-collect-task-class-design.md §5.4
  docs/dev/07collect-class/02-concept-collect-integration.md §5
"""

from __future__ import annotations

import logging

from infrastructure.collectors.akshare.fetcher import AkShareConceptFetcher
from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.concept_repository import ConceptRepoImpl
from infrastructure.tasks.collect.base import (
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    is_cancelled,
)
from infrastructure.tasks.concept_sync_operation import ConceptSyncOperation

logger = logging.getLogger(__name__)


class ConceptCollectTask(BaseCollectTask):
    """概念全量同步（采集管理 tab 用）

    单元 = 每个概念名（~423 个）
    并发 = 顺序循环（AKShare 接口限频 0.3s）
    失败 = 累计 fail，不中断（个别概念失败不影响其他）
    """

    name = "concept"

    def __init__(self) -> None:
        super().__init__()
        # AKShare fetcher 是无状态的，每次实例化代价很小；保留单例避免重复构造
        self._fetcher = AkShareConceptFetcher()

    # ── estimate_total ────────────────────────────────────────────────

    async def estimate_total(self, params: dict) -> int:
        """同步拉清单拿总数

        AKShare 接口同步调用，0.3s 延迟 + retry < 5s，对 router 可接受。
        """
        try:
            concepts = await _to_thread(self._fetcher.fetch_concept_list)
            return len(concepts)
        except Exception as e:
            logger.warning("estimate_total 拉清单失败: %s", e)
            return 0

    # ── run：业务主循环 ───────────────────────────────────────────────

    async def run(
        self,
        params: dict,
        on_unit_done,
    ) -> TaskSummary:
        try:
            concepts = await _to_thread(self._fetcher.fetch_concept_list)
        except Exception as e:
            logger.error("拉概念清单失败: %s", e)
            return TaskSummary(success=0, fail=0, message=f"拉清单失败: {e}")

        total = len(concepts)
        source = params.get("source", "em")
        logger.info(
            "ConceptCollect 任务 %d 启动: %d 个概念 (source=%s)",
            self._task_id, total, source,
        )

        success = fail = total_members = 0
        for i, bo in enumerate(concepts):
            # ── 取消检查（每概念一次，开销可忽略） ──
            if is_cancelled(self._task_id):
                raise Cancelled()

            try:
                # ── 每概念独立 session（避免长事务 / 单点失败） ──
                async with AsyncSessionLocal() as session:
                    repo_i = ConceptRepoImpl(session)
                    op_i = ConceptSyncOperation(
                        repo=repo_i, fetcher=self._fetcher,
                    )
                    member_count = await op_i._sync_one(bo)
                    await session.commit()

                total_members += member_count
                await on_unit_done(
                    UnitResult(
                        success=True,
                        detail=bo.name,
                        saved_count=member_count,
                    ),
                    bo.name,
                )
                success += 1
            except Cancelled:
                # 重新抛出，让 framework 收尾
                raise
            except Exception as e:
                logger.warning("概念 %s 同步失败: %s", bo.name, e)
                await on_unit_done(
                    UnitResult(success=False, detail=bo.name, error=str(e)),
                    bo.name,
                )
                fail += 1

            # 进度日志（与既有 ConceptSyncOperation.sync_all 行为一致）
            if (i + 1) % 50 == 0:
                logger.info(
                    "概念同步进度: %d/%d (成功%d 失败%d)",
                    i + 1, total, success, fail,
                )

        return TaskSummary(
            success=success,
            fail=fail,
            total_count=total,
            message=(
                f"完成: 成功 {success} 概念, 失败 {fail}, "
                f"成员 {total_members} 只"
            ),
        )


# ── 内部 helper ──────────────────────────────────────────────────────────


async def _to_thread(func, /, *args, **kwargs):
    """把同步函数包成 async（asyncio.to_thread 在 Python 3.9+ 才有，本项目 3.12 OK）

    用途：AkShare 的 fetch_concept_list() 是同步阻塞调用，
          在 estimate_total() 内不能直接 await，
          故包到后台线程避免阻塞 event loop。
    """
    import asyncio
    return await asyncio.to_thread(func, *args, **kwargs)

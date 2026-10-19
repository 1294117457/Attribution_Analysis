"""collect context — 业务 DI 工厂（Phase 2 渐进式重构）

Phase 2 重构（2026-10-19）：
- 已升级 service：注入 CollectLogService + CollectTaskRunner
- 未升级 service：保持原签名

升级步骤（每个 service 需做）：
    1. service __init__ 接受 log_service + task_runner
    2. service.collect() 改为编排入口（返回 dict）
    3. service 增加 _run_collect() 执行入口（generator）
    4. 本文件对应 factory 改为 new + old 双签名
"""
from __future__ import annotations

import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_db, get_raw_db
from shared.infrastructure.di.redis_session import get_redis
from contexts.collect.application.service.manage import CollectLogService
from contexts.collect.infrastructure.adapter.background import get_collect_task_runner

logger = logging.getLogger(__name__)


def _build_log_service(
    session: AsyncSession,
    redis,
    *,
    log_session: AsyncSession | None = None,
) -> CollectLogService:
    """构造日志服务（统一 helper）

    Args:
        session:      service 业务 session（可能是 raw_data_db 或 attribution_db）
        redis:        redis 客户端
        log_session:  日志库 session（默认 = session）
                      当 service 业务数据在 raw_data_db 时，log_session 必须显式传 attribution_db session
    """
    return CollectLogService(
        session=log_session or session,
        redis_client=redis,
    )


def _safe_new(cls, **kwargs):
    """实例化：优先用新参数（log_service/task_runner），失败回退

    返回 (instance, is_phase2):
        - is_phase2=True  → 已是 Phase 2 版本
        - is_phase2=False → 回退到旧签名（暂未升级）
    """
    try:
        return cls(**kwargs), True
    except TypeError as e:
        # 旧版本不接受 log_service/task_runner，过滤掉
        old_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ("log_service", "task_runner")
        }
        logger.debug(
            "[%s] 暂未升级到 Phase 2，回退到旧签名: %s",
            cls.__name__, e,
        )
        return cls(**old_kwargs), False


# ═══════════════════════════════════════════════════════════════════════
# tech 5
# ═══════════════════════════════════════════════════════════════════════
def get_daily_kline_service(
    session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """日 K 线 service（写业务库 kline，用 get_db）— ★ Phase 2 已升级"""
    from contexts.collect.application.service.tech.daily_kline_service import (
        DailyKlineService,
    )
    return DailyKlineService(
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )


def get_minute_kline_service():
    """实时查询 service，无 repo（Phase 2 暂不接入日志）"""
    from contexts.collect.application.service.tech.minute_kline_service import (
        MinuteKlineService,
    )
    return MinuteKlineService()


def get_adj_factor_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_adj_factor_repository"],
        ).get_adj_factor_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.tech.adj_factor_service import (
        AdjFactorService,
    )
    return _safe_new(
        AdjFactorService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_suspend_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_suspend_repository"],
        ).get_suspend_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.tech.suspend_service import (
        SuspendService,
    )
    return _safe_new(
        SuspendService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_name_change_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_name_change_repository"],
        ).get_name_change_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.tech.name_change_service import (
        NameChangeService,
    )
    return _safe_new(
        NameChangeService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


# ═══════════════════════════════════════════════════════════════════════
# capital 9
# ═══════════════════════════════════════════════════════════════════════
def get_moneyflow_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_moneyflow_repository"],
        ).get_moneyflow_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.moneyflow_service import (
        MoneyflowService,
    )
    return _safe_new(
        MoneyflowService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_moneyflow_hsgt_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_moneyflow_hsgt_repository"],
        ).get_moneyflow_hsgt_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.moneyflow_hsgt_service import (
        MoneyflowHsgtService,
    )
    return _safe_new(
        MoneyflowHsgtService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_top_list_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_top_list_repository"],
        ).get_top_list_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.top_list_service import (
        TopListService,
    )
    return _safe_new(
        TopListService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_top_inst_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_top_inst_repository"],
        ).get_top_inst_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.top_inst_service import (
        TopInstService,
    )
    return _safe_new(
        TopInstService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_block_trade_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_block_trade_repository"],
        ).get_block_trade_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.block_trade_service import (
        BlockTradeService,
    )
    return _safe_new(
        BlockTradeService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_margin_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_margin_detail_repository"],
        ).get_margin_detail_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.margin_service import (
        MarginService,
    )
    return _safe_new(
        MarginService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_hsgt_top10_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_hsgt_top10_repository"],
        ).get_hsgt_top10_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.hsgt_top10_service import (
        HsgtTop10Service,
    )
    return _safe_new(
        HsgtTop10Service,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_limit_list_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_limit_list_repository"],
        ).get_limit_list_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.limit_list_service import (
        LimitListService,
    )
    return _safe_new(
        LimitListService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_holder_number_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_holder_number_repository"],
        ).get_holder_number_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.capital.holder_number_service import (
        HolderNumberService,
    )
    return _safe_new(
        HolderNumberService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


# ═══════════════════════════════════════════════════════════════════════
# fundamental 12
# ═══════════════════════════════════════════════════════════════════════
def get_daily_basic_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_fin_daily_basic_repository"],
        ).get_fin_daily_basic_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.daily_basic_service import (
        DailyBasicService,
    )
    return _safe_new(
        DailyBasicService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_fin_income_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_fin_report_repository"],
        ).get_fin_report_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.fin_income_service import (
        FinIncomeService,
    )
    return _safe_new(
        FinIncomeService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_top10_holders_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_fin_top10_holders_repository"],
        ).get_fin_top10_holders_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.top10_holders_service import (
        Top10HoldersService,
    )
    return _safe_new(
        Top10HoldersService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_top10_float_holders_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_fin_top10_float_holders_repository"],
        ).get_fin_top10_float_holders_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.top10_floatholders_service import (
        Top10FloatHoldersService,
    )
    return _safe_new(
        Top10FloatHoldersService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_dividend_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_dividend_repository"],
        ).get_dividend_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.dividend_service import (
        DividendService,
    )
    return _safe_new(
        DividendService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_stock_basic_service(
    session: AsyncSession = Depends(get_raw_db),
    log_session: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """股票基本信息 service（写采集库 fundamental_stock_info，用 get_raw_db）— ★ Phase 2 已升级

    v2（2026-10-19）：FULL_REFRESH 编排模式
      - 注入 CollectLogService + CollectTaskRunner
      - collect() 立即返回 { log_id, status }；实际 fetch+replace_all 在后台跑

    ★ 双 session 架构：
      - session      = raw_data_db（采集库），用于 StockInfoRepository.replace_all
      - log_session  = attribution_db（业务库），用于 CollectLogService 写 collect_logs

    原因：StockInfoDB 继承 RawBase → 表在 raw_data_db；但 collect_logs 在 attribution_db。
    CollectLogService 与业务 service 共享 session 写日志的设计，遇到"数据落采集库"
    的 service（stock_basic / daily_kline）时必须解耦 session。
    """
    from contexts.collect.application.service.fundamental.stock_basic_service import (
        StockBasicService,
    )
    return StockBasicService(
        session=session,
        log_service=_build_log_service(session, redis, log_session=log_session),
        task_runner=get_collect_task_runner(),
    )


def get_stock_concepts_service(
    stock_concept_repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_stock_concept_repository"],
        ).get_stock_concept_repository
    ),
    concept_repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_concept_repository"],
        ).get_concept_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.stock_concepts_service import (
        StockConceptsService,
    )
    return _safe_new(
        StockConceptsService,
        stock_concept_repo=stock_concept_repo,
        concept_repo=concept_repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_concept_list_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_concept_repository"],
        ).get_concept_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.concept_list_service import (
        ConceptListService,
    )
    return _safe_new(
        ConceptListService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_concept_members_service(
    member_repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_concept_member_repository"],
        ).get_concept_member_repository
    ),
    concept_repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_concept_repository"],
        ).get_concept_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.concept_members_service import (
        ConceptMembersService,
    )
    return _safe_new(
        ConceptMembersService,
        member_repo=member_repo,
        concept_repo=concept_repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_concept_index_daily_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_concept_index_repository"],
        ).get_concept_index_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.concept_index_daily_service import (
        ConceptIndexDailyService,
    )
    return _safe_new(
        ConceptIndexDailyService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


def get_concept_minute_service():
    """实时查询 service，无 repo"""
    from contexts.collect.application.service.fundamental.concept_minute_service import (
        ConceptMinuteService,
    )
    return ConceptMinuteService()


def get_concept_snapshot_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_concept_snapshot_repository"],
        ).get_concept_snapshot_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.fundamental.concept_snapshot_service import (
        ConceptSnapshotService,
    )
    return _safe_new(
        ConceptSnapshotService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


# ═══════════════════════════════════════════════════════════════════════
# news 1
# ═══════════════════════════════════════════════════════════════════════
def get_news_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_news_article_repository"],
        ).get_news_article_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
    redis=Depends(get_redis),
):
    from contexts.collect.application.service.news.news_service import (
        NewsService,
    )
    return _safe_new(
        NewsService,
        repo=repo,
        session=session,
        log_service=_build_log_service(session, redis),
        task_runner=get_collect_task_runner(),
    )[0]


# ═══════════════════════════════════════════════════════════════════════
# sentiment 1（空壳，不动）
# ═══════════════════════════════════════════════════════════════════════
def get_sentiment_service():
    from contexts.collect.application.service.sentiment.sentiment_service import (
        SentimentService,
    )
    return SentimentService()


__all__ = [
    # tech 5
    "get_daily_kline_service",
    "get_minute_kline_service",
    "get_adj_factor_service",
    "get_suspend_service",
    "get_name_change_service",
    # capital 9
    "get_moneyflow_service",
    "get_moneyflow_hsgt_service",
    "get_top_list_service",
    "get_top_inst_service",
    "get_block_trade_service",
    "get_margin_service",
    "get_hsgt_top10_service",
    "get_limit_list_service",
    "get_holder_number_service",
    # fundamental 12
    "get_daily_basic_service",
    "get_fin_income_service",
    "get_top10_holders_service",
    "get_top10_float_holders_service",
    "get_dividend_service",
    "get_stock_basic_service",
    "get_stock_concepts_service",
    "get_concept_list_service",
    "get_concept_members_service",
    "get_concept_index_daily_service",
    "get_concept_minute_service",
    "get_concept_snapshot_service",
    # news 1
    "get_news_service",
    # sentiment 1
    "get_sentiment_service",
]

"""collect context — 业务 DI 工厂（step9 Redis 全局单例版）

step9 重构（2026-10-20）—— Redis 走全局单例：
    - 移除 25 个 factory 的 redis=Depends(get_redis) 参数
    - _make_log_service helper 移除 —— CollectLogService 无参构造，内部自接 redis 单例
    - 工厂函数保持 def（同步），FastAPI Depends 链路更短

step8 修正（2026-10-20）—— session 注入修正：

修正前的两个系统性缺陷：
    1. 24 个 factory 把 raw_data 库 session 传给 CollectLogService，
       而 collect_logs 表在 attribution 库 → create_pending 第一步就 500
    2. get_daily_service 用业务库 session（get_db）写 RawBase 表
       → tech_kline_daily 找不到

修正后的统一约定（28 个 factory 无一例外）：
    - session 一律取 get_raw_db（采集数据 100% 在 raw_data_db）
    - CollectLogService 不再收 session —— 它自管 attribution 库短事务
    - 不再有「双 session 特例」，签名完全一致

标准工厂模板：
    def get_xxx_service(
        repo=Depends(...),
        session: AsyncSession = Depends(get_raw_db),
    ):
        return XxxService(
            repo=repo,
            session=session,
            log_service=CollectLogService(),
            task_runner=get_collect_task_runner(),
        )

职责边界：
    - service.session      → 采集数据读写（raw_data_db）
    - service.log_service  → 采集日志（内部自开 attribution_db session + 直连全局 redis 单例）
    - service.task_runner  → 后台派发（纯内存，无 session）

历史：
    v3（2026-10-19）—— TaskRunner 统一派发 Phase 1
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.infrastructure.di.db_session import get_raw_db
from contexts.collect.application.service.manage import CollectLogService
from contexts.collect.infrastructure.adapter.background import get_collect_task_runner
from contexts.collect.infrastructure.di.repo import (
    get_daily_kline_repository,
)


# ═══════════════════════════════════════════════════════════════════════
# tech 5
# ═══════════════════════════════════════════════════════════════════════
def get_daily_service(
    kline_repo=Depends(get_daily_kline_repository),
):
    """日 K 线 service（写采集库 tech_daily）

    v11（2026-10-26）：
        - 去掉 log_service 入参：日志改用 log_util（工具函数，零注入）
        - 构造函数：(fetcher=None, kline_repo=None)
    """
    from contexts.collect.application.service.tech.daily_service import (
        DailyService,
    )
    return DailyService(kline_repo=kline_repo)


def get_minute_service():
    """实时查询 service，无 repo（不走采集队列，无 log 集成）"""
    from contexts.collect.application.service.tech.minute_service import (
        MinuteService,
    )
    return MinuteService()


def get_adj_factor_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_adj_factor_repository"],
        ).get_adj_factor_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.tech.adj_factor_service import (
        AdjFactorService,
    )
    return AdjFactorService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_suspend_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_suspend_repository"],
        ).get_suspend_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.tech.suspend_service import (
        SuspendService,
    )
    return SuspendService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_name_change_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_name_change_repository"],
        ).get_name_change_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.tech.name_change_service import (
        NameChangeService,
    )
    return NameChangeService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


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
):
    from contexts.collect.application.service.capital.moneyflow_service import (
        MoneyflowService,
    )
    return MoneyflowService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_moneyflow_hsgt_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_moneyflow_hsgt_repository"],
        ).get_moneyflow_hsgt_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.capital.moneyflow_hsgt_service import (
        MoneyflowHsgtService,
    )
    return MoneyflowHsgtService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_top_list_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_top_list_repository"],
        ).get_top_list_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.capital.top_list_service import (
        TopListService,
    )
    return TopListService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_top_inst_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_top_inst_repository"],
        ).get_top_inst_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.capital.top_inst_service import (
        TopInstService,
    )
    return TopInstService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_block_trade_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_block_trade_repository"],
        ).get_block_trade_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.capital.block_trade_service import (
        BlockTradeService,
    )
    return BlockTradeService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_margin_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_margin_detail_repository"],
        ).get_margin_detail_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.capital.margin_service import (
        MarginService,
    )
    return MarginService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_hsgt_top10_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_hsgt_top10_repository"],
        ).get_hsgt_top10_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.capital.hsgt_top10_service import (
        HsgtTop10Service,
    )
    return HsgtTop10Service(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_limit_list_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_limit_list_repository"],
        ).get_limit_list_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.capital.limit_list_service import (
        LimitListService,
    )
    return LimitListService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_holder_number_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_holder_number_repository"],
        ).get_holder_number_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.capital.holder_number_service import (
        HolderNumberService,
    )
    return HolderNumberService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


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
):
    from contexts.collect.application.service.fundamental.daily_basic_service import (
        DailyBasicService,
    )
    return DailyBasicService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_fin_income_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_fin_report_repository"],
        ).get_fin_report_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.fundamental.fin_income_service import (
        FinIncomeService,
    )
    return FinIncomeService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_top10_holders_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_fin_top10_holders_repository"],
        ).get_fin_top10_holders_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.fundamental.top10_holders_service import (
        Top10HoldersService,
    )
    return Top10HoldersService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_top10_float_holders_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_fin_top10_float_holders_repository"],
        ).get_fin_top10_float_holders_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.fundamental.top10_floatholders_service import (
        Top10FloatHoldersService,
    )
    return Top10FloatHoldersService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_dividend_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_dividend_repository"],
        ).get_dividend_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.fundamental.dividend_service import (
        DividendService,
    )
    return DividendService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_stock_basic_service(
    session: AsyncSession = Depends(get_raw_db),
):
    """股票基本信息 service（写采集库 fundamental_stock_basic，用 get_raw_db）

    v4 自管协议（2026-10-20）：
        - session 仅 get() 实时查询用；run_collect 自己开 raw_data session
        - 构造函数：(log_service, session=None, fetcher=None, stock_repo=None)
    """
    from contexts.collect.application.service.fundamental.stock_basic_service import (
        StockBasicService,
    )
    return StockBasicService(
        log_service=CollectLogService(),
        session=session,
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
):
    from contexts.collect.application.service.fundamental.stock_concepts_service import (
        StockConceptsService,
    )
    return StockConceptsService(
        stock_concept_repo=stock_concept_repo,
        concept_repo=concept_repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_concept_list_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_concept_repository"],
        ).get_concept_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.fundamental.concept_list_service import (
        ConceptListService,
    )
    return ConceptListService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


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
):
    from contexts.collect.application.service.fundamental.concept_members_service import (
        ConceptMembersService,
    )
    return ConceptMembersService(
        member_repo=member_repo,
        concept_repo=concept_repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


def get_concept_index_daily_service(
    repo=Depends(
        __import__(
            "contexts.collect.infrastructure.di.repo",
            fromlist=["get_concept_index_repository"],
        ).get_concept_index_repository
    ),
    session: AsyncSession = Depends(get_raw_db),
):
    from contexts.collect.application.service.fundamental.concept_index_daily_service import (
        ConceptIndexDailyService,
    )
    return ConceptIndexDailyService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


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
):
    from contexts.collect.application.service.fundamental.concept_snapshot_service import (
        ConceptSnapshotService,
    )
    return ConceptSnapshotService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


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
):
    from contexts.collect.application.service.news.news_service import (
        NewsService,
    )
    return NewsService(
        repo=repo,
        session=session,
        log_service=CollectLogService(),
        task_runner=get_collect_task_runner(),
    )


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
    "get_daily_service",
    "get_minute_service",
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
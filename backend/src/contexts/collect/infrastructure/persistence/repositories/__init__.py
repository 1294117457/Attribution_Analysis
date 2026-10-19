"""contexts.collect.infrastructure.persistence.repositories

25 个 repo 全部列出（phase1+ 完成，2026-10-18）。

SQL/ORM 实现 domain Protocol：
  - tech (5)         : adj_factor / suspend / name_change / dividend / (kline)
  - capital (9)      : moneyflow / moneyflow_hsgt / top_list / top_inst / block_trade
                       / margin_detail / hsgt_top10 / limit_list / holder_number
  - fundamental (9)  : fin_daily_basic / fin_report / fin_top10_holders
                       / fin_top10_float_holders / (stock_info) / stock_concept
  - concept (4)      : concept / concept_member / concept_index / concept_snapshot
  - news (1)         : news_article
  24 + kline_repo + stock_info_repo = 26
"""
from contexts.collect.infrastructure.persistence.repositories.kline_repo import (
    KlineRepository,
)
from contexts.collect.infrastructure.persistence.repositories.stock_info_repo import (
    StockInfoRepository,
)
# tech
from contexts.collect.infrastructure.persistence.repositories.adj_factor_repo import (
    AdjFactorRepository,
)
from contexts.collect.infrastructure.persistence.repositories.suspend_repo import (
    SuspendRepository,
)
from contexts.collect.infrastructure.persistence.repositories.name_change_repo import (
    NameChangeRepository,
)
from contexts.collect.infrastructure.persistence.repositories.dividend_repo import (
    DividendRepository,
)
# capital
from contexts.collect.infrastructure.persistence.repositories.moneyflow_repo import (
    MoneyflowRepository,
)
from contexts.collect.infrastructure.persistence.repositories.moneyflow_hsgt_repo import (
    MoneyflowHsgtRepository,
)
from contexts.collect.infrastructure.persistence.repositories.top_list_repo import (
    TopListRepository,
)
from contexts.collect.infrastructure.persistence.repositories.top_inst_repo import (
    TopInstRepository,
)
from contexts.collect.infrastructure.persistence.repositories.block_trade_repo import (
    BlockTradeRepository,
)
from contexts.collect.infrastructure.persistence.repositories.margin_detail_repo import (
    MarginDetailRepository,
)
from contexts.collect.infrastructure.persistence.repositories.hsgt_top10_repo import (
    HsgtTop10Repository,
)
from contexts.collect.infrastructure.persistence.repositories.limit_list_repo import (
    LimitListRepository,
)
from contexts.collect.infrastructure.persistence.repositories.holder_number_repo import (
    HolderNumberRepository,
)
# fundamental
from contexts.collect.infrastructure.persistence.repositories.fin_daily_basic_repo import (
    FinDailyBasicRepository,
)
from contexts.collect.infrastructure.persistence.repositories.fin_report_repo import (
    FinReportRepository,
)
from contexts.collect.infrastructure.persistence.repositories.fin_top10_holders_repo import (
    FinTop10HoldersRepository,
)
from contexts.collect.infrastructure.persistence.repositories.fin_top10_float_holders_repo import (
    FinTop10FloatHoldersRepository,
)
from contexts.collect.infrastructure.persistence.repositories.stock_concept_repo import (
    StockConceptRepository,
)
# concept (在 concept DB)
from contexts.collect.infrastructure.persistence.repositories.concept_repo import (
    ConceptRepository,
)
from contexts.collect.infrastructure.persistence.repositories.concept_member_repo import (
    ConceptMemberRepository,
)
from contexts.collect.infrastructure.persistence.repositories.concept_index_repo import (
    ConceptIndexRepository,
)
from contexts.collect.infrastructure.persistence.repositories.concept_snapshot_repo import (
    ConceptSnapshotRepository,
)
# news
from contexts.collect.infrastructure.persistence.repositories.news_article_repo import (
    NewsArticleRepository,
)
# collect logs (v2 采集日志进度优化)
from contexts.collect.infrastructure.persistence.repositories.collect_log_repository import (
    CollectLogRepository,
)

__all__ = [
    # 既有
    "KlineRepository",
    "StockInfoRepository",
    # tech
    "AdjFactorRepository",
    "SuspendRepository",
    "NameChangeRepository",
    "DividendRepository",
    # capital
    "MoneyflowRepository",
    "MoneyflowHsgtRepository",
    "TopListRepository",
    "TopInstRepository",
    "BlockTradeRepository",
    "MarginDetailRepository",
    "HsgtTop10Repository",
    "LimitListRepository",
    "HolderNumberRepository",
    # fundamental
    "FinDailyBasicRepository",
    "FinReportRepository",
    "FinTop10HoldersRepository",
    "FinTop10FloatHoldersRepository",
    "StockConceptRepository",
    # concept
    "ConceptRepository",
    "ConceptMemberRepository",
    "ConceptIndexRepository",
    "ConceptSnapshotRepository",
    # news
    "NewsArticleRepository",
    # collect logs
    "CollectLogRepository",
]

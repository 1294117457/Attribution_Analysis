"""ORM 模型统一注册入口（替代原 infrastructure.persistence.models）

作用：把所有 context 下的 ORM 模型 import 一遍，让 SQLAlchemy Base.metadata 收集到。
仅被 schema_init.py 和 di.py 引用。
"""
# 这一行 import 不存在——仅仅为了让 IDE / flake8 不报未使用的警告
# 每个 model 模块必须在 import 时执行 model class 定义（继承 Base）

# auth
from contexts.auth.infrastructure.persistence.models.user import PermissionDB, RoleDB, UserDB  # noqa: F401
from contexts.auth.infrastructure.persistence.models.user_role import RolePermissionDB, UserRoleDB  # noqa: F401

# collect
from contexts.collect.infrastructure.persistence.models.collect_config import (  # noqa: F401
    CollectFetcherDB,
    CollectPlanDB,
    CollectPlanItemDB,
)
from contexts.collect.infrastructure.persistence.models.sys_collect_task import SysCollectTaskDB  # noqa: F401

# concept
from contexts.concept.infrastructure.persistence.models.concept import (  # noqa: F401
    ConceptIndexTHDB,
    ConceptMemberDB,
    ConceptsDB,
)

# market
from contexts.market.infrastructure.persistence.models.tech_kline import TechKlineDailyDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.stock_info import StockInfoDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.fin_daily_basic import FinDailyBasicDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.fin_report import FinReportDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.fin_top10_holders import FinTop10HolderDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.fin_top10_float import FinTop10FloatHolderDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.cap_top_list import CapTopListDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.cap_top_inst import CapTopInstDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.cap_moneyflow import CapMoneyflowDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.cap_margin import CapMarginDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.cap_margin_detail import CapMarginDetailDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.cap_block_trade import CapBlockTradeDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.cap_holder_num import CapHolderNumDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.base_suspend import BaseSuspendDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.base_name_change import BaseNameChangeDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.base_adj_factor import BaseAdjFactorDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.base_dividend import BaseDividendDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.mkt_calendar import MktCalendarDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.mkt_market_daily import MktMarketDailyDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.mkt_sector_daily import MktSectorDailyDB  # noqa: F401
from contexts.market.infrastructure.persistence.models.mkt_index_member import MktIndexMemberDB  # noqa: F401

# user (stock_pool)
from contexts.user.infrastructure.persistence.models.pool import (  # noqa: F401
    StockPoolDB,
    StockPoolMemberDB,
    PoolOperationDB,
)

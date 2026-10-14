#!/usr/bin/env python3
"""step6 完整迁移 v2

修复 v1 遗漏：
- auth ORM 模型：user.py / user_role.py / permission.py / role.py → contexts.auth
- mixins.py → contexts.shared
- 缩略 import：from application.service import XxxService（无完整路径）
- auth_repository.py → contexts.auth
- main.py / di.py 里的循环引用

策略：物理移动 + import 重写 + 写所有 context 的 bootstrap.py + 写 app/main.py
"""
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path("D:/codes/Attribution_Analysis/backend/src")

# ═══════════════════════════════════════════════════════════════
# 阶段 B：shared/
# ═══════════════════════════════════════════════════════════════
SHARED_MOVES = [
    ("domain/base.py",                "contexts/shared/domain/base.py"),
    ("domain/repository.py",          "contexts/shared/domain/repository.py"),
    ("application/port/page.py",      "contexts/shared/application/port/page.py"),
    ("route/api/_response.py",        "contexts/shared/interface/response.py"),
    ("infrastructure/persistence/connection.py",      "contexts/shared/infrastructure/persistence/connection.py"),
    ("infrastructure/persistence/schema_init.py",     "contexts/shared/infrastructure/persistence/schema_init.py"),
    ("infrastructure/persistence/base.py",           "contexts/shared/infrastructure/persistence/orm_base.py"),
    ("infrastructure/persistence/mixins.py",         "contexts/shared/infrastructure/persistence/mixins.py"),
    ("infrastructure/adapter/cache/redis_client.py", "contexts/shared/infrastructure/cache/redis_client.py"),
    ("infrastructure/config/settings.py",            "contexts/shared/infrastructure/config/settings.py"),
    ("infrastructure/config/__init__.py",            "contexts/shared/infrastructure/config/__init__.py"),
]

# ═══════════════════════════════════════════════════════════════
# 阶段 C：auth + collect
# ═══════════════════════════════════════════════════════════════
AUTH_MOVES = [
    # domain
    ("domain/entitys/auth/entity.py",        "contexts/auth/domain/entity.py"),
    ("domain/entitys/auth/repository.py",    "contexts/auth/domain/repository.py"),
    # application
    ("application/service/auth_service.py", "contexts/auth/application/service/auth_service.py"),
    # interface
    ("route/api/v1/auth.py",                "contexts/auth/interface/route.py"),
    ("route/api/v1/user.py",                "contexts/auth/interface/route_user.py"),
    ("route/api/v1/role.py",                "contexts/auth/interface/route_role.py"),
    ("route/api/v1/permission.py",          "contexts/auth/interface/route_permission.py"),
    ("route/api/v1/deps_auth.py",           "contexts/auth/interface/deps.py"),
    ("route/dto/request/auth.py",           "contexts/auth/interface/dto/request/auth.py"),
    ("route/dto/response/auth.py",          "contexts/auth/interface/dto/response/auth.py"),
    # infrastructure
    ("infrastructure/security/jwt_service.py",        "contexts/auth/infrastructure/security/jwt_service.py"),
    ("infrastructure/security/email.py",              "contexts/auth/infrastructure/security/email.py"),
    ("infrastructure/security/password.py",           "contexts/auth/infrastructure/security/password.py"),
    ("infrastructure/security/key_manager.py",        "contexts/auth/infrastructure/security/key_manager.py"),
    ("infrastructure/security/captcha.py",            "contexts/auth/infrastructure/security/captcha.py"),
    ("infrastructure/adapter/auth_port_adapters.py",  "contexts/auth/infrastructure/adapter/auth_port_adapters.py"),
    ("infrastructure/adapter/email_verification.py",  "contexts/auth/infrastructure/adapter/email_verification.py"),
    # ORM (auth)
    ("infrastructure/persistence/models/user.py",      "contexts/auth/infrastructure/persistence/models/user.py"),
    ("infrastructure/persistence/models/user_role.py", "contexts/auth/infrastructure/persistence/models/user_role.py"),
    ("infrastructure/persistence/repositories/auth_repository.py", "contexts/auth/infrastructure/persistence/repositories/auth_repository.py"),
    # "infrastructure/persistence/models/permission.py" / "role.py" 可能不存在
    # 留待 verify 后补充
]

COLLECT_MOVES = [
    # domain
    ("domain/entitys/collect_plan/vo.py",       "contexts/collect/domain/vo_collect_plan.py"),
    ("domain/entitys/collect_task/vo.py",       "contexts/collect/domain/vo_collect_task.py"),
    ("domain/service/concept_collection_policy.py", "contexts/collect/domain/service/concept_collection_policy.py"),
    # application/collect
    ("application/collect/__init__.py",          "contexts/collect/application/collect/__init__.py"),
    ("application/collect/task.py",              "contexts/collect/application/collect/task.py"),
    ("application/collect/runner.py",            "contexts/collect/application/collect/runner.py"),
    ("application/collect/context.py",           "contexts/collect/application/collect/context.py"),
    ("application/collect/planners.py",          "contexts/collect/application/collect/planners.py"),
    ("application/collect/declarative.py",       "contexts/collect/application/collect/declarative.py"),
    ("application/collect/registry.py",          "contexts/collect/application/collect/registry.py"),
    ("application/collect/tasks/__init__.py",    "contexts/collect/application/collect/tasks/__init__.py"),
    ("application/collect/tasks/tushare.py",     "contexts/collect/application/collect/tasks/tushare.py"),
    ("application/collect/tasks/daily_kline.py", "contexts/collect/application/collect/tasks/daily_kline.py"),
    ("application/collect/tasks/stock_basic.py", "contexts/collect/application/collect/tasks/stock_basic.py"),
    ("application/collect/tasks/concept.py",     "contexts/collect/application/collect/tasks/concept.py"),
    ("application/collect/tasks/concept_reason.py",     "contexts/collect/application/collect/tasks/concept_reason.py"),
    ("application/collect/tasks/concept_snapshot.py",  "contexts/collect/application/collect/tasks/concept_snapshot.py"),
    ("application/collect/tasks/planned.py",    "contexts/collect/application/collect/tasks/planned.py"),
    # application/service
    ("application/service/collect_manage_service.py", "contexts/collect/application/service/collect_manage_service.py"),
    # application/port
    ("application/port/collect_port.py",        "contexts/collect/application/port/collect_port.py"),
    ("application/port/scheduler_port.py",      "contexts/collect/application/port/scheduler_port.py"),
    # interface
    ("route/api/v1/collect_task.py",            "contexts/collect/interface/route.py"),
    ("route/dto/request/collect.py",            "contexts/collect/interface/dto/request/collect.py"),
    ("route/dto/response/collect.py",           "contexts/collect/interface/dto/response/collect.py"),
    # infrastructure
    ("infrastructure/persistence/collect/__init__.py",   "contexts/collect/infrastructure/persistence/collect/__init__.py"),
    ("infrastructure/persistence/collect/task_store.py",  "contexts/collect/infrastructure/persistence/collect/task_store.py"),
    ("infrastructure/persistence/collect/concept_store.py","contexts/collect/infrastructure/persistence/collect/concept_store.py"),
    ("infrastructure/persistence/collect/stock_universe.py","contexts/collect/infrastructure/persistence/collect/stock_universe.py"),
    ("infrastructure/persistence/collect/raw_store.py",  "contexts/collect/infrastructure/persistence/collect/raw_store.py"),
    ("infrastructure/persistence/models/collect_config.py",  "contexts/collect/infrastructure/persistence/models/collect_config.py"),
    ("infrastructure/persistence/models/sys_collect_task.py", "contexts/collect/infrastructure/persistence/models/sys_collect_task.py"),
    ("infrastructure/persistence/repositories/collect_config_repository.py", "contexts/collect/infrastructure/persistence/repositories/collect_config_repository.py"),
    ("infrastructure/adapter/scheduler/apscheduler_adapter.py", "contexts/collect/infrastructure/adapter/scheduler/apscheduler_adapter.py"),
    ("infrastructure/adapter/cache/collect_progress.py",       "contexts/collect/infrastructure/adapter/cache/collect_progress.py"),
    ("infrastructure/adapter/background/task_registry.py",     "contexts/collect/infrastructure/adapter/background/task_registry.py"),
]

# ═══════════════════════════════════════════════════════════════
# 阶段 D：data + market + concept
# ═══════════════════════════════════════════════════════════════
DATA_MOVES = [
    ("application/port/data/__init__.py",      "contexts/data/application/port/__init__.py"),
    ("application/port/data/base.py",         "contexts/data/application/port/base.py"),
    ("application/port/data/types.py",        "contexts/data/application/port/types.py"),
    ("application/port/data/tech.py",         "contexts/data/application/port/tech.py"),
    ("application/port/data/capital.py",      "contexts/data/application/port/capital.py"),
    ("application/port/data/fundamental.py",  "contexts/data/application/port/fundamental.py"),
    ("application/port/data/reference.py",    "contexts/data/application/port/reference.py"),
    ("application/port/data/concept.py",      "contexts/data/application/port/concept.py"),
    ("application/service/data_query_service.py", "contexts/data/application/service/data_query_service.py"),
    ("infrastructure/adapter/data/__init__.py",   "contexts/data/infrastructure/adapter/__init__.py"),
    ("infrastructure/adapter/data/setup.py",      "contexts/data/infrastructure/adapter/setup.py"),
    ("infrastructure/adapter/data/core/__init__.py",  "contexts/data/infrastructure/adapter/core/__init__.py"),
    ("infrastructure/adapter/data/core/base.py",      "contexts/data/infrastructure/adapter/core/base.py"),
    ("infrastructure/adapter/data/core/registry.py",  "contexts/data/infrastructure/adapter/core/registry.py"),
    ("infrastructure/adapter/data/core/gateway.py",   "contexts/data/infrastructure/adapter/core/gateway.py"),
    ("infrastructure/adapter/data/core/decorators.py", "contexts/data/infrastructure/adapter/core/decorators.py"),
    ("infrastructure/adapter/data/core/cache.py",    "contexts/data/infrastructure/adapter/core/cache.py"),
    ("infrastructure/adapter/data/core/context.py",  "contexts/data/infrastructure/adapter/core/context.py"),
    ("infrastructure/adapter/data/tushare/__init__.py", "contexts/data/infrastructure/adapter/tushare/__init__.py"),
    ("infrastructure/adapter/data/tushare/client.py",   "contexts/data/infrastructure/adapter/tushare/client.py"),
    ("infrastructure/adapter/data/tushare/base.py",     "contexts/data/infrastructure/adapter/tushare/base.py"),
    ("infrastructure/adapter/data/tushare/parser.py",   "contexts/data/infrastructure/adapter/tushare/parser.py"),
    ("infrastructure/adapter/data/tushare/tech.py",     "contexts/data/infrastructure/adapter/tushare/tech.py"),
    ("infrastructure/adapter/data/tushare/capital.py",  "contexts/data/infrastructure/adapter/tushare/capital.py"),
    ("infrastructure/adapter/data/tushare/fundamental.py", "contexts/data/infrastructure/adapter/tushare/fundamental.py"),
    ("infrastructure/adapter/data/tushare/reference.py", "contexts/data/infrastructure/adapter/tushare/reference.py"),
    ("infrastructure/adapter/data/pytdx/__init__.py", "contexts/data/infrastructure/adapter/pytdx/__init__.py"),
    ("infrastructure/adapter/data/pytdx/client.py",   "contexts/data/infrastructure/adapter/pytdx/client.py"),
    ("infrastructure/adapter/data/pytdx/tech.py",     "contexts/data/infrastructure/adapter/pytdx/tech.py"),
    ("infrastructure/adapter/data/adata/__init__.py", "contexts/data/infrastructure/adapter/adata/__init__.py"),
    ("infrastructure/adapter/data/adata/client.py",   "contexts/data/infrastructure/adapter/adata/client.py"),
    ("infrastructure/adapter/data/adata/concept.py",  "contexts/data/infrastructure/adapter/adata/concept.py"),
]

MARKET_MOVES = [
    ("domain/entitys/kline/entity.py",         "contexts/market/domain/kline/entity.py"),
    ("domain/entitys/kline/vo.py",             "contexts/market/domain/kline/vo.py"),
    ("domain/entitys/kline/repository.py",     "contexts/market/domain/kline/repository.py"),
    ("domain/entitys/stock_info/entity.py",    "contexts/market/domain/stock_info/entity.py"),
    ("domain/entitys/stock_info/vo.py",        "contexts/market/domain/stock_info/vo.py"),
    ("domain/entitys/stock_info/repository.py","contexts/market/domain/stock_info/repository.py"),
    ("domain/entitys/mkt_calendar/entity.py",      "contexts/market/domain/mkt_calendar/entity.py"),
    ("domain/entitys/mkt_calendar/repository.py",  "contexts/market/domain/mkt_calendar/repository.py"),
    ("domain/entitys/mkt_market_daily/entity.py",  "contexts/market/domain/mkt_market_daily/entity.py"),
    ("domain/entitys/mkt_market_daily/repository.py","contexts/market/domain/mkt_market_daily/repository.py"),
    ("domain/entitys/mkt_sector_daily/entity.py",  "contexts/market/domain/mkt_sector_daily/entity.py"),
    ("domain/entitys/mkt_sector_daily/repository.py","contexts/market/domain/mkt_sector_daily/repository.py"),
    ("domain/entitys/mkt_index_member/entity.py",  "contexts/market/domain/mkt_index_member/entity.py"),
    ("domain/entitys/mkt_index_member/repository.py","contexts/market/domain/mkt_index_member/repository.py"),
    ("domain/entitys/fin_daily_basic/entity.py",  "contexts/market/domain/fin_daily_basic/entity.py"),
    ("domain/entitys/fin_daily_basic/repository.py","contexts/market/domain/fin_daily_basic/repository.py"),
    ("domain/entitys/fin_report/entity.py",       "contexts/market/domain/fin_report/entity.py"),
    ("domain/entitys/fin_report/repository.py",   "contexts/market/domain/fin_report/repository.py"),
    ("domain/entitys/fin_top10_holders/entity.py","contexts/market/domain/fin_top10_holders/entity.py"),
    ("domain/entitys/fin_top10_holders/repository.py","contexts/market/domain/fin_top10_holders/repository.py"),
    ("domain/entitys/fin_top10_float/entity.py",  "contexts/market/domain/fin_top10_float/entity.py"),
    ("domain/entitys/fin_top10_float/repository.py","contexts/market/domain/fin_top10_float/repository.py"),
    ("domain/entitys/cap_top_list/entity.py",     "contexts/market/domain/cap_top_list/entity.py"),
    ("domain/entitys/cap_top_list/repository.py", "contexts/market/domain/cap_top_list/repository.py"),
    ("domain/entitys/cap_top_inst/entity.py",     "contexts/market/domain/cap_top_inst/entity.py"),
    ("domain/entitys/cap_top_inst/repository.py", "contexts/market/domain/cap_top_inst/repository.py"),
    ("domain/entitys/cap_moneyflow/entity.py",    "contexts/market/domain/cap_moneyflow/entity.py"),
    ("domain/entitys/cap_moneyflow/repository.py","contexts/market/domain/cap_moneyflow/repository.py"),
    ("domain/entitys/cap_margin/entity.py",       "contexts/market/domain/cap_margin/entity.py"),
    ("domain/entitys/cap_margin/repository.py",   "contexts/market/domain/cap_margin/repository.py"),
    ("domain/entitys/cap_margin_detail/entity.py","contexts/market/domain/cap_margin_detail/entity.py"),
    ("domain/entitys/cap_margin_detail/repository.py","contexts/market/domain/cap_margin_detail/repository.py"),
    ("domain/entitys/cap_block_trade/entity.py",  "contexts/market/domain/cap_block_trade/entity.py"),
    ("domain/entitys/cap_block_trade/repository.py","contexts/market/domain/cap_block_trade/repository.py"),
    ("domain/entitys/cap_holder_num/entity.py",   "contexts/market/domain/cap_holder_num/entity.py"),
    ("domain/entitys/cap_holder_num/repository.py","contexts/market/domain/cap_holder_num/repository.py"),
    ("domain/entitys/base_suspend/entity.py",     "contexts/market/domain/base_suspend/entity.py"),
    ("domain/entitys/base_suspend/repository.py", "contexts/market/domain/base_suspend/repository.py"),
    ("domain/entitys/base_name_change/entity.py","contexts/market/domain/base_name_change/entity.py"),
    ("domain/entitys/base_name_change/repository.py","contexts/market/domain/base_name_change/repository.py"),
    ("domain/entitys/base_adj_factor/entity.py",  "contexts/market/domain/base_adj_factor/entity.py"),
    ("domain/entitys/base_adj_factor/repository.py","contexts/market/domain/base_adj_factor/repository.py"),
    ("domain/entitys/base_dividend/entity.py",    "contexts/market/domain/base_dividend/entity.py"),
    ("domain/entitys/base_dividend/repository.py","contexts/market/domain/base_dividend/repository.py"),
    ("domain/entitys/panel/vo.py",                "contexts/market/domain/panel/vo.py"),
    ("domain/entitys/panel/repository.py",        "contexts/market/domain/panel/repository.py"),
    ("domain/service/indicator_calculator.py",    "contexts/market/domain/service/indicator_calculator.py"),
    ("domain/service/signal_detector.py",         "contexts/market/domain/service/signal_detector.py"),
    ("domain/service/market_session.py",         "contexts/market/domain/service/market_session.py"),
    ("application/service/stock_info_service.py","contexts/market/application/service/stock_info_service.py"),
    ("route/api/v1/kline.py",             "contexts/market/interface/route_kline.py"),
    ("route/api/v1/minute_kline.py",      "contexts/market/interface/route_minute_kline.py"),
    ("route/api/v1/data.py",              "contexts/market/interface/route_data.py"),
    ("route/api/v1/data_board.py",        "contexts/market/interface/route_data_board.py"),
    ("route/api/v1/panel.py",             "contexts/market/interface/route_panel.py"),
    ("route/api/v1/stock.py",             "contexts/market/interface/route_stock.py"),
    ("route/api/v1/stock_analysis.py",    "contexts/market/interface/route_stock_analysis.py"),
    ("route/dto/request/kline.py",        "contexts/market/interface/dto/request/kline.py"),
    ("route/dto/request/stock.py",        "contexts/market/interface/dto/request/stock.py"),
    ("route/dto/response/kline.py",       "contexts/market/interface/dto/response/kline.py"),
    ("route/dto/response/panel.py",       "contexts/market/interface/dto/response/panel.py"),
    ("route/dto/response/stock_analysis.py","contexts/market/interface/dto/response/stock_analysis.py"),
    # market ORM (16 个 models + 16 个 repositories)
    ("infrastructure/persistence/models/kline.py",     "contexts/market/infrastructure/persistence/models/kline.py"),
    ("infrastructure/persistence/models/tech_kline.py","contexts/market/infrastructure/persistence/models/tech_kline.py"),
    ("infrastructure/persistence/models/stock_info.py","contexts/market/infrastructure/persistence/models/stock_info.py"),
    ("infrastructure/persistence/models/fin_daily_basic.py",  "contexts/market/infrastructure/persistence/models/fin_daily_basic.py"),
    ("infrastructure/persistence/models/fin_report.py",       "contexts/market/infrastructure/persistence/models/fin_report.py"),
    ("infrastructure/persistence/models/fin_top10_holders.py","contexts/market/infrastructure/persistence/models/fin_top10_holders.py"),
    ("infrastructure/persistence/models/fin_top10_float.py",  "contexts/market/infrastructure/persistence/models/fin_top10_float.py"),
    ("infrastructure/persistence/models/cap_top_list.py",     "contexts/market/infrastructure/persistence/models/cap_top_list.py"),
    ("infrastructure/persistence/models/cap_top_inst.py",     "contexts/market/infrastructure/persistence/models/cap_top_inst.py"),
    ("infrastructure/persistence/models/cap_moneyflow.py",    "contexts/market/infrastructure/persistence/models/cap_moneyflow.py"),
    ("infrastructure/persistence/models/cap_margin.py",       "contexts/market/infrastructure/persistence/models/cap_margin.py"),
    ("infrastructure/persistence/models/cap_margin_detail.py","contexts/market/infrastructure/persistence/models/cap_margin_detail.py"),
    ("infrastructure/persistence/models/cap_block_trade.py",  "contexts/market/infrastructure/persistence/models/cap_block_trade.py"),
    ("infrastructure/persistence/models/cap_holder_num.py",   "contexts/market/infrastructure/persistence/models/cap_holder_num.py"),
    ("infrastructure/persistence/models/base_suspend.py",     "contexts/market/infrastructure/persistence/models/base_suspend.py"),
    ("infrastructure/persistence/models/base_name_change.py","contexts/market/infrastructure/persistence/models/base_name_change.py"),
    ("infrastructure/persistence/models/base_adj_factor.py",  "contexts/market/infrastructure/persistence/models/base_adj_factor.py"),
    ("infrastructure/persistence/models/base_dividend.py",    "contexts/market/infrastructure/persistence/models/base_dividend.py"),
    ("infrastructure/persistence/models/mkt_calendar.py",      "contexts/market/infrastructure/persistence/models/mkt_calendar.py"),
    ("infrastructure/persistence/models/mkt_market_daily.py",  "contexts/market/infrastructure/persistence/models/mkt_market_daily.py"),
    ("infrastructure/persistence/models/mkt_sector_daily.py",  "contexts/market/infrastructure/persistence/models/mkt_sector_daily.py"),
    ("infrastructure/persistence/models/mkt_index_member.py",  "contexts/market/infrastructure/persistence/models/mkt_index_member.py"),
    ("infrastructure/persistence/models/panel_compose.py",     "contexts/market/infrastructure/persistence/models/panel_compose.py"),
    ("infrastructure/persistence/repositories/kline_repository.py",     "contexts/market/infrastructure/persistence/repositories/kline_repository.py"),
    ("infrastructure/persistence/repositories/stock_repository.py",     "contexts/market/infrastructure/persistence/repositories/stock_repository.py"),
    ("infrastructure/persistence/repositories/panel_compose_repository.py","contexts/market/infrastructure/persistence/repositories/panel_compose_repository.py"),
    ("infrastructure/persistence/repositories/fin_daily_basic_repository.py","contexts/market/infrastructure/persistence/repositories/fin_daily_basic_repository.py"),
    ("infrastructure/persistence/repositories/fin_report_repository.py",     "contexts/market/infrastructure/persistence/repositories/fin_report_repository.py"),
    ("infrastructure/persistence/repositories/fin_top10_holders_repository.py","contexts/market/infrastructure/persistence/repositories/fin_top10_holders_repository.py"),
    ("infrastructure/persistence/repositories/fin_top10_float_repository.py", "contexts/market/infrastructure/persistence/repositories/fin_top10_float_repository.py"),
    ("infrastructure/persistence/repositories/cap_top_list_repository.py",   "contexts/market/infrastructure/persistence/repositories/cap_top_list_repository.py"),
    ("infrastructure/persistence/repositories/cap_top_inst_repository.py",   "contexts/market/infrastructure/persistence/repositories/cap_top_inst_repository.py"),
    ("infrastructure/persistence/repositories/cap_moneyflow_repository.py",  "contexts/market/infrastructure/persistence/repositories/cap_moneyflow_repository.py"),
    ("infrastructure/persistence/repositories/cap_margin_detail_repository.py","contexts/market/infrastructure/persistence/repositories/cap_margin_detail_repository.py"),
    ("infrastructure/persistence/repositories/cap_holder_num_repository.py", "contexts/market/infrastructure/persistence/repositories/cap_holder_num_repository.py"),
    ("infrastructure/persistence/repositories/cap_block_trade_repository.py","contexts/market/infrastructure/persistence/repositories/cap_block_trade_repository.py"),
    ("infrastructure/persistence/repositories/base_suspend_repository.py",   "contexts/market/infrastructure/persistence/repositories/base_suspend_repository.py"),
    ("infrastructure/persistence/repositories/base_name_change_repository.py","contexts/market/infrastructure/persistence/repositories/base_name_change_repository.py"),
    ("infrastructure/persistence/repositories/base_adj_factor_repository.py","contexts/market/infrastructure/persistence/repositories/base_adj_factor_repository.py"),
    ("infrastructure/persistence/repositories/base_dividend_repository.py", "contexts/market/infrastructure/persistence/repositories/base_dividend_repository.py"),
    ("infrastructure/persistence/repositories/_symboled_dated_repo.py",      "contexts/market/infrastructure/persistence/repositories/_symboled_dated_repo.py"),
]

CONCEPT_MOVES = [
    ("domain/entitys/concept/entity.py",     "contexts/concept/domain/entity.py"),
    ("domain/entitys/concept/vo.py",         "contexts/concept/domain/vo.py"),
    ("domain/entitys/concept/repository.py", "contexts/concept/domain/repository.py"),
    ("domain/service/concept_brief_service.py", "contexts/concept/domain/service/concept_brief_service.py"),
    ("application/service/concept_service.py",      "contexts/concept/application/service/concept_service.py"),
    ("application/service/concept_board_service.py", "contexts/concept/application/service/concept_board_service.py"),
    ("application/service/concept_realtime.py",     "contexts/concept/application/service/concept_realtime.py"),
    ("route/api/v1/concept.py",                     "contexts/concept/interface/route.py"),
    ("route/dto/request/concept_board.py",          "contexts/concept/interface/dto/request/concept_board.py"),
    ("route/dto/response/concept.py",               "contexts/concept/interface/dto/response/concept.py"),
    ("route/dto/response/concept_board.py",         "contexts/concept/interface/dto/response/concept_board.py"),
    ("infrastructure/persistence/models/concept.py",         "contexts/concept/infrastructure/persistence/models/concept.py"),
    ("infrastructure/persistence/repositories/concept_repository.py", "contexts/concept/infrastructure/persistence/repositories/concept_repository.py"),
]

# ═══════════════════════════════════════════════════════════════
# 阶段 E：user
# ═══════════════════════════════════════════════════════════════
USER_MOVES = [
    ("domain/entitys/stock_pool/entity.py",     "contexts/user/domain/stock_pool/entity.py"),
    ("domain/entitys/stock_pool/vo.py",         "contexts/user/domain/stock_pool/vo.py"),
    ("domain/entitys/stock_pool/repository.py", "contexts/user/domain/stock_pool/repository.py"),
    ("application/service/stock_pool_service.py", "contexts/user/application/service/stock_pool_service.py"),
    ("application/port/operation_dispatcher_port.py", "contexts/user/application/port/operation_dispatcher_port.py"),
    ("route/api/v1/pool.py",                   "contexts/user/interface/route_pool.py"),
    ("route/dto/request/pool.py",              "contexts/user/interface/dto/request/pool.py"),
    ("route/dto/request/pool_operation.py",    "contexts/user/interface/dto/request/pool_operation.py"),
    ("route/dto/response/pool.py",             "contexts/user/interface/dto/response/pool.py"),
    ("infrastructure/persistence/models/pool.py", "contexts/user/infrastructure/persistence/models/pool.py"),
    ("infrastructure/persistence/repositories/pool_repository.py", "contexts/user/infrastructure/persistence/repositories/pool_repository.py"),
    ("infrastructure/persistence/repositories/pool_operation_repository.py", "contexts/user/infrastructure/persistence/repositories/pool_operation_repository.py"),
    ("infrastructure/adapter/background/operation_dispatcher.py", "contexts/user/infrastructure/adapter/background/operation_dispatcher.py"),
]

ALL_MOVES = SHARED_MOVES + AUTH_MOVES + COLLECT_MOVES + DATA_MOVES + MARKET_MOVES + CONCEPT_MOVES + USER_MOVES

# ═══════════════════════════════════════════════════════════════
# Import 重写规则
# ═══════════════════════════════════════════════════════════════
# A. 完整路径
# B. 缩略路径（如 from application.service import XxxService）
IMPORT_REWRITES = [
    # ── shared（路径完整）──
    (r"^from domain\.base\b",                  "from contexts.shared.domain.base"),
    (r"^from domain\.repository\b",            "from contexts.shared.domain.repository"),
    (r"^from application\.port\.page\b",       "from contexts.shared.application.port.page"),
    (r"^from route\.api\._response\b",         "from contexts.shared.interface.response"),
    (r"^from infrastructure\.config\.settings\b", "from contexts.shared.infrastructure.config.settings"),
    (r"^from infrastructure\.config\b",        "from contexts.shared.infrastructure.config"),
    (r"^from infrastructure\.persistence\.connection\b",   "from contexts.shared.infrastructure.persistence.connection"),
    (r"^from infrastructure\.persistence\.schema_init\b",  "from contexts.shared.infrastructure.persistence.schema_init"),
    (r"^from infrastructure\.persistence\.base\b",         "from contexts.shared.infrastructure.persistence.orm_base"),
    (r"^from infrastructure\.persistence\.mixins\b",       "from contexts.shared.infrastructure.persistence.mixins"),
    (r"^from infrastructure\.adapter\.cache\.redis_client\b", "from contexts.shared.infrastructure.cache.redis_client"),
    (r"^from infrastructure\.adapter\.cache\b", "from contexts.shared.infrastructure.cache"),
    # ── auth（路径完整）──
    (r"^from domain\.entitys\.auth\b",                  "from contexts.auth.domain"),
    (r"^from application\.service\.auth_service\b",     "from contexts.auth.application.service.auth_service"),
    (r"^from route\.api\.v1\.auth\b",           "from contexts.auth.interface.route"),
    (r"^from route\.api\.v1\.user\b",           "from contexts.auth.interface.route_user"),
    (r"^from route\.api\.v1\.role\b",           "from contexts.auth.interface.route_role"),
    (r"^from route\.api\.v1\.permission\b",     "from contexts.auth.interface.route_permission"),
    (r"^from route\.api\.v1\.deps_auth\b",      "from contexts.auth.interface.deps"),
    (r"^from route\.dto\.request\.auth\b",      "from contexts.auth.interface.dto.request.auth"),
    (r"^from route\.dto\.response\.auth\b",     "from contexts.auth.interface.dto.response.auth"),
    (r"^from infrastructure\.security\b",       "from contexts.auth.infrastructure.security"),
    (r"^from infrastructure\.adapter\.auth_port_adapters\b", "from contexts.auth.infrastructure.adapter.auth_port_adapters"),
    (r"^from infrastructure\.adapter\.email_verification\b",  "from contexts.auth.infrastructure.adapter.email_verification"),
    (r"^from infrastructure\.persistence\.models\.user\b",      "from contexts.auth.infrastructure.persistence.models.user"),
    (r"^from infrastructure\.persistence\.models\.user_role\b", "from contexts.auth.infrastructure.persistence.models.user_role"),
    (r"^from infrastructure\.persistence\.repositories\.auth_repository\b", "from contexts.auth.infrastructure.persistence.repositories.auth_repository"),
    # ── collect ──
    (r"^from application\.collect\b",                 "from contexts.collect.application.collect"),
    (r"^from application\.service\.collect_manage_service\b", "from contexts.collect.application.service.collect_manage_service"),
    (r"^from application\.port\.collect_port\b",      "from contexts.collect.application.port.collect_port"),
    (r"^from application\.port\.scheduler_port\b",    "from contexts.collect.application.port.scheduler_port"),
    (r"^from route\.api\.v1\.collect_task\b",         "from contexts.collect.interface.route"),
    (r"^from route\.dto\.request\.collect\b",         "from contexts.collect.interface.dto.request.collect"),
    (r"^from route\.dto\.response\.collect\b",        "from contexts.collect.interface.dto.response.collect"),
    (r"^from domain\.entitys\.collect_plan\b",        "from contexts.collect.domain.vo_collect_plan"),
    (r"^from domain\.entitys\.collect_task\b",        "from contexts.collect.domain.vo_collect_task"),
    (r"^from domain\.service\.concept_collection_policy\b", "from contexts.collect.domain.service.concept_collection_policy"),
    (r"^from infrastructure\.persistence\.collect\b", "from contexts.collect.infrastructure.persistence.collect"),
    (r"^from infrastructure\.persistence\.models\.collect_config\b",  "from contexts.collect.infrastructure.persistence.models.collect_config"),
    (r"^from infrastructure\.persistence\.models\.sys_collect_task\b", "from contexts.collect.infrastructure.persistence.models.sys_collect_task"),
    (r"^from infrastructure\.persistence\.repositories\.collect_config_repository\b", "from contexts.collect.infrastructure.persistence.repositories.collect_config_repository"),
    (r"^from infrastructure\.adapter\.scheduler\.apscheduler_adapter\b", "from contexts.collect.infrastructure.adapter.scheduler.apscheduler_adapter"),
    (r"^from infrastructure\.adapter\.cache\.collect_progress\b",       "from contexts.collect.infrastructure.adapter.cache.collect_progress"),
    (r"^from infrastructure\.adapter\.background\.task_registry\b",     "from contexts.collect.infrastructure.adapter.background.task_registry"),
    # ── data ──
    (r"^from application\.port\.data\b",        "from contexts.data.application.port"),
    (r"^from application\.service\.data_query_service\b", "from contexts.data.application.service.data_query_service"),
    (r"^from infrastructure\.adapter\.data\b",  "from contexts.data.infrastructure.adapter"),
    # ── market ──
    (r"^from domain\.entitys\.kline\b",         "from contexts.market.domain.kline"),
    (r"^from domain\.entitys\.stock_info\b",    "from contexts.market.domain.stock_info"),
    (r"^from domain\.entitys\.mkt_calendar\b",  "from contexts.market.domain.mkt_calendar"),
    (r"^from domain\.entitys\.mkt_market_daily\b", "from contexts.market.domain.mkt_market_daily"),
    (r"^from domain\.entitys\.mkt_sector_daily\b", "from contexts.market.domain.mkt_sector_daily"),
    (r"^from domain\.entitys\.mkt_index_member\b", "from contexts.market.domain.mkt_index_member"),
    (r"^from domain\.entitys\.fin_daily_basic\b",  "from contexts.market.domain.fin_daily_basic"),
    (r"^from domain\.entitys\.fin_report\b",       "from contexts.market.domain.fin_report"),
    (r"^from domain\.entitys\.fin_top10_holders\b","from contexts.market.domain.fin_top10_holders"),
    (r"^from domain\.entitys\.fin_top10_float\b",  "from contexts.market.domain.fin_top10_float"),
    (r"^from domain\.entitys\.cap_top_list\b",     "from contexts.market.domain.cap_top_list"),
    (r"^from domain\.entitys\.cap_top_inst\b",     "from contexts.market.domain.cap_top_inst"),
    (r"^from domain\.entitys\.cap_moneyflow\b",    "from contexts.market.domain.cap_moneyflow"),
    (r"^from domain\.entitys\.cap_margin\b",       "from contexts.market.domain.cap_margin"),
    (r"^from domain\.entitys\.cap_margin_detail\b","from contexts.market.domain.cap_margin_detail"),
    (r"^from domain\.entitys\.cap_block_trade\b",  "from contexts.market.domain.cap_block_trade"),
    (r"^from domain\.entitys\.cap_holder_num\b",   "from contexts.market.domain.cap_holder_num"),
    (r"^from domain\.entitys\.base_suspend\b",     "from contexts.market.domain.base_suspend"),
    (r"^from domain\.entitys\.base_name_change\b","from contexts.market.domain.base_name_change"),
    (r"^from domain\.entitys\.base_adj_factor\b",  "from contexts.market.domain.base_adj_factor"),
    (r"^from domain\.entitys\.base_dividend\b",    "from contexts.market.domain.base_dividend"),
    (r"^from domain\.entitys\.panel\b",            "from contexts.market.domain.panel"),
    (r"^from domain\.service\.indicator_calculator\b", "from contexts.market.domain.service.indicator_calculator"),
    (r"^from domain\.service\.signal_detector\b",  "from contexts.market.domain.service.signal_detector"),
    (r"^from domain\.service\.market_session\b",  "from contexts.market.domain.service.market_session"),
    (r"^from application\.service\.stock_info_service\b", "from contexts.market.application.service.stock_info_service"),
    (r"^from route\.api\.v1\.kline\b",             "from contexts.market.interface.route_kline"),
    (r"^from route\.api\.v1\.minute_kline\b",      "from contexts.market.interface.route_minute_kline"),
    (r"^from route\.api\.v1\.data\b",              "from contexts.market.interface.route_data"),
    (r"^from route\.api\.v1\.data_board\b",        "from contexts.market.interface.route_data_board"),
    (r"^from route\.api\.v1\.panel\b",             "from contexts.market.interface.route_panel"),
    (r"^from route\.api\.v1\.stock\b",             "from contexts.market.interface.route_stock"),
    (r"^from route\.api\.v1\.stock_analysis\b",    "from contexts.market.interface.route_stock_analysis"),
    (r"^from route\.dto\.request\.kline\b",        "from contexts.market.interface.dto.request.kline"),
    (r"^from route\.dto\.request\.stock\b",        "from contexts.market.interface.dto.request.stock"),
    (r"^from route\.dto\.response\.kline\b",       "from contexts.market.interface.dto.response.kline"),
    (r"^from route\.dto\.response\.panel\b",       "from contexts.market.interface.dto.response.panel"),
    (r"^from route\.dto\.response\.stock_analysis\b","from contexts.market.interface.dto.response.stock_analysis"),
    # market ORM
    (r"^from infrastructure\.persistence\.models\.kline\b",     "from contexts.market.infrastructure.persistence.models.kline"),
    (r"^from infrastructure\.persistence\.models\.tech_kline\b","from contexts.market.infrastructure.persistence.models.tech_kline"),
    (r"^from infrastructure\.persistence\.models\.stock_info\b","from contexts.market.infrastructure.persistence.models.stock_info"),
    (r"^from infrastructure\.persistence\.models\.fin_daily_basic\b",  "from contexts.market.infrastructure.persistence.models.fin_daily_basic"),
    (r"^from infrastructure\.persistence\.models\.fin_report\b",       "from contexts.market.infrastructure.persistence.models.fin_report"),
    (r"^from infrastructure\.persistence\.models\.fin_top10_holders\b","from contexts.market.infrastructure.persistence.models.fin_top10_holders"),
    (r"^from infrastructure\.persistence\.models\.fin_top10_float\b",  "from contexts.market.infrastructure.persistence.models.fin_top10_float"),
    (r"^from infrastructure\.persistence\.models\.cap_top_list\b",     "from contexts.market.infrastructure.persistence.models.cap_top_list"),
    (r"^from infrastructure\.persistence\.models\.cap_top_inst\b",     "from contexts.market.infrastructure.persistence.models.cap_top_inst"),
    (r"^from infrastructure\.persistence\.models\.cap_moneyflow\b",    "from contexts.market.infrastructure.persistence.models.cap_moneyflow"),
    (r"^from infrastructure\.persistence\.models\.cap_margin\b",       "from contexts.market.infrastructure.persistence.models.cap_margin"),
    (r"^from infrastructure\.persistence\.models\.cap_margin_detail\b","from contexts.market.infrastructure.persistence.models.cap_margin_detail"),
    (r"^from infrastructure\.persistence\.models\.cap_block_trade\b",  "from contexts.market.infrastructure.persistence.models.cap_block_trade"),
    (r"^from infrastructure\.persistence\.models\.cap_holder_num\b",   "from contexts.market.infrastructure.persistence.models.cap_holder_num"),
    (r"^from infrastructure\.persistence\.models\.base_suspend\b",     "from contexts.market.infrastructure.persistence.models.base_suspend"),
    (r"^from infrastructure\.persistence\.models\.base_name_change\b","from contexts.market.infrastructure.persistence.models.base_name_change"),
    (r"^from infrastructure\.persistence\.models\.base_adj_factor\b",  "from contexts.market.infrastructure.persistence.models.base_adj_factor"),
    (r"^from infrastructure\.persistence\.models\.base_dividend\b",    "from contexts.market.infrastructure.persistence.models.base_dividend"),
    (r"^from infrastructure\.persistence\.models\.mkt_calendar\b",      "from contexts.market.infrastructure.persistence.models.mkt_calendar"),
    (r"^from infrastructure\.persistence\.models\.mkt_market_daily\b",  "from contexts.market.infrastructure.persistence.models.mkt_market_daily"),
    (r"^from infrastructure\.persistence\.models\.mkt_sector_daily\b",  "from contexts.market.infrastructure.persistence.models.mkt_sector_daily"),
    (r"^from infrastructure\.persistence\.models\.mkt_index_member\b",  "from contexts.market.infrastructure.persistence.models.mkt_index_member"),
    (r"^from infrastructure\.persistence\.models\.panel_compose\b",     "from contexts.market.infrastructure.persistence.models.panel_compose"),
    (r"^from infrastructure\.persistence\.repositories\.kline_repository\b",     "from contexts.market.infrastructure.persistence.repositories.kline_repository"),
    (r"^from infrastructure\.persistence\.repositories\.stock_repository\b",     "from contexts.market.infrastructure.persistence.repositories.stock_repository"),
    (r"^from infrastructure\.persistence\.repositories\.panel_compose_repository\b","from contexts.market.infrastructure.persistence.repositories.panel_compose_repository"),
    (r"^from infrastructure\.persistence\.repositories\.fin_daily_basic_repository\b","from contexts.market.infrastructure.persistence.repositories.fin_daily_basic_repository"),
    (r"^from infrastructure\.persistence\.repositories\.fin_report_repository\b",     "from contexts.market.infrastructure.persistence.repositories.fin_report_repository"),
    (r"^from infrastructure\.persistence\.repositories\.fin_top10_holders_repository\b","from contexts.market.infrastructure.persistence.repositories.fin_top10_holders_repository"),
    (r"^from infrastructure\.persistence\.repositories\.fin_top10_float_repository\b", "from contexts.market.infrastructure.persistence.repositories.fin_top10_float_repository"),
    (r"^from infrastructure\.persistence\.repositories\.cap_top_list_repository\b",   "from contexts.market.infrastructure.persistence.repositories.cap_top_list_repository"),
    (r"^from infrastructure\.persistence\.repositories\.cap_top_inst_repository\b",   "from contexts.market.infrastructure.persistence.repositories.cap_top_inst_repository"),
    (r"^from infrastructure\.persistence\.repositories\.cap_moneyflow_repository\b",  "from contexts.market.infrastructure.persistence.repositories.cap_moneyflow_repository"),
    (r"^from infrastructure\.persistence\.repositories\.cap_margin_detail_repository\b","from contexts.market.infrastructure.persistence.repositories.cap_margin_detail_repository"),
    (r"^from infrastructure\.persistence\.repositories\.cap_holder_num_repository\b", "from contexts.market.infrastructure.persistence.repositories.cap_holder_num_repository"),
    (r"^from infrastructure\.persistence\.repositories\.cap_block_trade_repository\b","from contexts.market.infrastructure.persistence.repositories.cap_block_trade_repository"),
    (r"^from infrastructure\.persistence\.repositories\.base_suspend_repository\b",   "from contexts.market.infrastructure.persistence.repositories.base_suspend_repository"),
    (r"^from infrastructure\.persistence\.repositories\.base_name_change_repository\b","from contexts.market.infrastructure.persistence.repositories.base_name_change_repository"),
    (r"^from infrastructure\.persistence\.repositories\.base_adj_factor_repository\b","from contexts.market.infrastructure.persistence.repositories.base_adj_factor_repository"),
    (r"^from infrastructure\.persistence\.repositories\.base_dividend_repository\b", "from contexts.market.infrastructure.persistence.repositories.base_dividend_repository"),
    (r"^from infrastructure\.persistence\.repositories\._symboled_dated_repo\b",      "from contexts.market.infrastructure.persistence.repositories._symboled_dated_repo"),
    # ── concept ──
    (r"^from domain\.entitys\.concept\b",                 "from contexts.concept.domain"),
    (r"^from domain\.service\.concept_brief_service\b",  "from contexts.concept.domain.service.concept_brief_service"),
    (r"^from application\.service\.concept_service\b",    "from contexts.concept.application.service.concept_service"),
    (r"^from application\.service\.concept_board_service\b","from contexts.concept.application.service.concept_board_service"),
    (r"^from application\.service\.concept_realtime\b",   "from contexts.concept.application.service.concept_realtime"),
    (r"^from route\.api\.v1\.concept\b",                  "from contexts.concept.interface.route"),
    (r"^from route\.dto\.request\.concept_board\b",       "from contexts.concept.interface.dto.request.concept_board"),
    (r"^from route\.dto\.response\.concept\b",            "from contexts.concept.interface.dto.response.concept"),
    (r"^from route\.dto\.response\.concept_board\b",      "from contexts.concept.interface.dto.response.concept_board"),
    (r"^from infrastructure\.persistence\.models\.concept\b",         "from contexts.concept.infrastructure.persistence.models.concept"),
    (r"^from infrastructure\.persistence\.repositories\.concept_repository\b", "from contexts.concept.infrastructure.persistence.repositories.concept_repository"),
    # ── user ──
    (r"^from domain\.entitys\.stock_pool\b",                 "from contexts.user.domain.stock_pool"),
    (r"^from application\.service\.stock_pool_service\b",   "from contexts.user.application.service.stock_pool_service"),
    (r"^from application\.port\.operation_dispatcher_port\b","from contexts.user.application.port.operation_dispatcher_port"),
    (r"^from route\.api\.v1\.pool\b",                       "from contexts.user.interface.route_pool"),
    (r"^from route\.dto\.request\.pool\b",                  "from contexts.user.interface.dto.request.pool"),
    (r"^from route\.dto\.request\.pool_operation\b",        "from contexts.user.interface.dto.request.pool_operation"),
    (r"^from route\.dto\.response\.pool\b",                 "from contexts.user.interface.dto.response.pool"),
    (r"^from route\.dto\.response\.stock_pool\b",           "from contexts.user.interface.dto.response.pool"),
    (r"^from infrastructure\.persistence\.models\.pool\b",  "from contexts.user.infrastructure.persistence.models.pool"),
    (r"^from infrastructure\.persistence\.repositories\.pool_repository\b",            "from contexts.user.infrastructure.persistence.repositories.pool_repository"),
    (r"^from infrastructure\.persistence\.repositories\.pool_operation_repository\b",  "from contexts.user.infrastructure.persistence.repositories.pool_operation_repository"),
    (r"^from infrastructure\.adapter\.background\.operation_dispatcher\b",            "from contexts.user.infrastructure.adapter.background.operation_dispatcher"),
    # ── 缩略 import（v2 新增）──
    (r"^from application\.service import cancel_background\b", "from contexts.collect.application.service.collect_manage_service import cancel_background"),
    (r"^from application\.service import AuthService\b",       "from contexts.auth.application.service.auth_service import AuthService"),
    (r"^from application\.service import StockPoolService\b",  "from contexts.user.application.service.stock_pool_service import StockPoolService"),
    (r"^from application\.service import StockInfoService\b",  "from contexts.market.application.service.stock_info_service import StockInfoService"),
    (r"^from application\.service import CollectManageService\b", "from contexts.collect.application.service.collect_manage_service import CollectManageService"),
    (r"^from application\.service import ConceptBoardService, ConceptService\b",
        "from contexts.concept.application.service.concept_board_service import ConceptBoardService\nfrom contexts.concept.application.service.concept_service import ConceptService"),
    (r"^from application\.service import CollectManageService, StockInfoService\b",
        "from contexts.collect.application.service.collect_manage_service import CollectManageService\nfrom contexts.market.application.service.stock_info_service import StockInfoService"),
    (r"^from application\.service import\s*\(\s*ConceptBoardService,\s*ConceptService\s*\)",
        "from contexts.concept.application.service.concept_board_service import ConceptBoardService\nfrom contexts.concept.application.service.concept_service import ConceptService"),
    # 缩略 `from route.api import _response`
    (r"^from route\.api import _response", "from contexts.shared.interface.response"),
    (r"^from route\.api import _response as R", "from contexts.shared.interface import response as R"),
    # 缩略 `from route.api.router import api_router`
    (r"^from route\.api\.router import api_router", "from contexts.shared.interface.router_compat import api_router"),
    # 缩略 `from domain.service import ...`
    (r"^from domain\.service import WARMUP_BARS, IndicatorCalculator",
        "from contexts.market.domain.service.indicator_calculator import WARMUP_BARS, IndicatorCalculator"),
    (r"^from domain\.service import ConceptBriefService",
        "from contexts.concept.domain.service.concept_brief_service import ConceptBriefService"),
    (r"^from domain\.service import\s*\(\s*ConceptBriefService,\s*ConceptCollectionPolicy,\s*IndicatorCalculator,\s*\)",
        "from contexts.concept.domain.service.concept_brief_service import ConceptBriefService\nfrom contexts.collect.domain.service.concept_collection_policy import ConceptCollectionPolicy\nfrom contexts.market.domain.service.indicator_calculator import IndicatorCalculator"),
    # ORM 缩略 import
    (r"^from infrastructure\.persistence\.models\.user_role import RolePermissionDB, UserRoleDB",
        "from contexts.auth.infrastructure.persistence.models.user_role import RolePermissionDB, UserRoleDB"),
    (r"^from infrastructure\.persistence\.models\.user import PermissionDB, RoleDB, UserDB",
        "from contexts.auth.infrastructure.persistence.models.user import PermissionDB, RoleDB, UserDB"),
]


def do_moves():
    moved = 0
    for old, new in ALL_MOVES:
        old_p = ROOT / old
        new_p = ROOT / new
        if old_p.exists():
            new_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_p), str(new_p))
            moved += 1
    print(f"  移动 {moved} 个文件（共 {len(ALL_MOVES)}）")
    return moved


def do_rewrites():
    rewrite_count = 0
    for path in ROOT.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        for old_pattern, new_str in IMPORT_REWRITES:
            text = re.sub(old_pattern, new_str, text, flags=re.MULTILINE)
        if text != original:
            path.write_text(text, encoding="utf-8")
            rewrite_count += 1
    print(f"  改 import {rewrite_count} 个文件")
    return rewrite_count


def verify_violations():
    old_prefixes = [
        r"^from domain\.",
        r"^from application\.",
        r"^from infrastructure\.",
        r"^from route\.",
    ]
    violations = []
    for path in ROOT.rglob("*.py"):
        if "__pycache__" in str(path) or "_legacy_compat" in str(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for p in old_prefixes:
            for m in re.finditer(p, text, re.MULTILINE):
                line_num = text[:m.start()].count("\n") + 1
                violations.append((str(path.relative_to(ROOT)), line_num, m.group(0),
                                   text.split("\n")[line_num-1].strip()[:100]))
    print(f"  剩余违规: {len(violations)}")
    for v in violations[:30]:
        print(f"    {v[0]}:{v[1]}  {v[2]}  →  {v[3]}")
    return len(violations)


def main():
    print("=" * 60)
    print("step6 v2 完整迁移")
    print("=" * 60)
    print("\n[1] 物理移动")
    do_moves()
    print("\n[2] 改 import")
    do_rewrites()
    print("\n[3] 静态校验")
    n = verify_violations()
    if n == 0:
        print("\n[OK] 全部通过")
    else:
        print(f"\n[FAIL] 还有 {n} 处")


if __name__ == "__main__":
    main()

"""聚合所有 context 的 router，提供给 main.py 一次性 include。

按 DDD 规范：
- 各 context 的 route 文件统一在 `contexts/<ctx>/interface/route/` 目录
- 业务子模块一个文件（如 auth_login.py / auth_password.py / auth_register.py）
- router 变量在本文件统一 re-export
"""
from fastapi import APIRouter

from shared.infrastructure.config.settings import get_settings

settings = get_settings()
api_router = APIRouter(prefix=settings.API_V1_PREFIX)

# ── auth 上下文：认证 + 用户/角色/权限管理 ──
# /api/v1/auth/*, /api/v1/users/*, /api/v1/roles/*, /api/v1/permissions/*
from contexts.auth.interface.route.auth_login import router as auth_login_router
from contexts.auth.interface.route.auth_register import router as auth_register_router
from contexts.auth.interface.route.auth_password import router as auth_password_router
from contexts.auth.interface.route_user import router as auth_user_router
from contexts.auth.interface.route_role import router as auth_role_router
from contexts.auth.interface.route_permission import router as auth_permission_router

# ── market 上下文：K线/股票/面板/分钟K线/数据面/AI归因 ──
# /api/v1/klines/*, /api/v1/stocks/*, /api/v1/stock-panel/*, /api/v1/minute-klines/*,
# /api/v1/data/*, /api/v1/data-board/*, /api/v1/stocks/* (AI归因)
from contexts.market.interface.route.kline import router as market_kline_router
from contexts.market.interface.route.stock import router as market_stock_router
from contexts.market.interface.route.panel import router as market_panel_router
from contexts.market.interface.route.minute_kline import router as market_minute_kline_router
from contexts.market.interface.route.data_board import router as market_data_board_router
from contexts.market.interface.route.stock_analysis import router as market_stock_analysis_router

# ── concept 上下文：概念相关 ──
# /api/v1/concepts/*
from contexts.concept.interface.route.concept_board import router as concept_board_router
from contexts.concept.interface.route.concept_query import router as concept_query_router
from contexts.concept.interface.route.concept_quote import router as concept_quote_router

# ── collect 上下文：catalog + 日志 + 5 个 facet ──
# /api/collect/catalog              service catalog
# /api/collect/logs/{service}       日志查询
# /api/collect/query/{name}        实时查询
# /api/collect/{facet}/{service}   各 facet 采集入口
from contexts.collect.interface.route.catalog import router as collect_catalog_router
from contexts.collect.interface.route.log import router as collect_log_router
from contexts.collect.interface.route.tech import router as collect_tech_router
from contexts.collect.interface.route.capital import router as collect_capital_router
from contexts.collect.interface.route.fundamental import router as collect_fundamental_router
from contexts.collect.interface.route.news import router as collect_news_router
from contexts.collect.interface.route.sentiment import router as collect_sentiment_router

# ── user 上下文：操作池（自选股） ──
from contexts.user.interface.route.pool import router as user_pool_router

# ═══════════════════════════════════════════════════════════════════════════════
# 聚合：按依赖顺序挂载（基础 → 上层）
# ═══════════════════════════════════════════════════════════════════════════════

# market 先挂（基础数据）
api_router.include_router(market_kline_router)
api_router.include_router(market_stock_router)
api_router.include_router(market_panel_router)
api_router.include_router(market_minute_kline_router)
api_router.include_router(market_data_board_router)
api_router.include_router(market_stock_analysis_router)

# concept
api_router.include_router(concept_board_router)
api_router.include_router(concept_query_router)
api_router.include_router(concept_quote_router)

# user
api_router.include_router(user_pool_router)

# auth（认证 + 登录 + 密码 + 注册 + 用户/角色/权限管理）
api_router.include_router(auth_login_router)
api_router.include_router(auth_register_router)
api_router.include_router(auth_password_router)
api_router.include_router(auth_user_router)
api_router.include_router(auth_role_router)
api_router.include_router(auth_permission_router)

# collect（catalog + 日志 + 5 个 facet）
api_router.include_router(collect_catalog_router)
api_router.include_router(collect_log_router)
api_router.include_router(collect_tech_router)
api_router.include_router(collect_capital_router)
api_router.include_router(collect_fundamental_router)
api_router.include_router(collect_news_router)
api_router.include_router(collect_sentiment_router)

__all__ = ["api_router", "settings"]

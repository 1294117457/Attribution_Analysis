"""聚合所有 context 的 router，提供给 main.py 一次性 include。

各 context 已独立定义 `router` 变量（本文件不再做 prefix 硬编码）：
- 前缀读取 settings.API_V1_PREFIX，可在 .env 中调整
- 每个 context 的 router 自带自己的 prefix（如 /auth、/stocks 等）
"""
from fastapi import APIRouter

from shared.infrastructure.config.settings import get_settings

settings = get_settings()
api_router = APIRouter(prefix=settings.API_V1_PREFIX)

# ── auth 上下文：认证 + 用户/角色/权限管理 ──
# /api/v1/auth/*, /api/v1/users/*, /api/v1/roles/*, /api/v1/permissions/*
from contexts.auth.interface.route import router as auth_router
from contexts.auth.interface.route_user import router as auth_user_router
from contexts.auth.interface.route_role import router as auth_role_router
from contexts.auth.interface.route_permission import router as auth_permission_router

# ── market 上下文：K线/股票/面板/分钟K线/数据面/AI归因 ──
# /api/v1/klines/*, /api/v1/stocks/*, /api/v1/stock-panel/*, /api/v1/minute-klines/*,
# /api/v1/data/*, /api/v1/data-board/*, /api/v1/stocks/* (AI归因)
from contexts.market.interface.route_kline import router as market_kline_router
from contexts.market.interface.route_stock import router as market_stock_router
from contexts.market.interface.route_panel import router as market_panel_router
from contexts.market.interface.route_minute_kline import router as market_minute_kline_router
from contexts.market.interface.route_data import router as market_data_router
from contexts.market.interface.route_data_board import router as market_data_board_router
from contexts.market.interface.route_stock_analysis import router as market_stock_analysis_router

# ── concept 上下文：概念相关 ──
# /api/v1/concepts/*
from contexts.concept.interface.route import router as concept_router

# ── collect 上下文：采集任务管理 ──
# /api/v1/collect/*
from contexts.collect.interface.route import router as collect_router

# ── user 上下文：操作池（自选股） ──
from contexts.user.interface.route_pool import router as user_pool_router

# ═══════════════════════════════════════════════════════════════════════════════
# 聚合：按依赖顺序挂载（基础 → 上层）
# data → market → concept → user → auth → collect
# 注：上面已 import 各 router（无副作用），现在统一 include
# ═══════════════════════════════════════════════════════════════════════════════

# market 先挂（基础数据）
api_router.include_router(market_kline_router)
api_router.include_router(market_stock_router)
api_router.include_router(market_panel_router)
api_router.include_router(market_minute_kline_router)
api_router.include_router(market_data_router)
api_router.include_router(market_data_board_router)
api_router.include_router(market_stock_analysis_router)

# concept
api_router.include_router(concept_router)

# user
api_router.include_router(user_pool_router)

# auth（认证）
api_router.include_router(auth_router)
api_router.include_router(auth_user_router)
api_router.include_router(auth_role_router)
api_router.include_router(auth_permission_router)

# collect
api_router.include_router(collect_router)


__all__ = ["api_router", "settings"]

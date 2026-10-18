"""collect.interface.router — 采集管理面所有 HTTP 路由的汇总

目录结构（与 fetcher/ service/ 镜像，按基本面 5 个 facet 拆分）：
    route/tech/         技术面  5 个 service / 5 个 POST endpoint
    route/capital/      资金面  9 个 service / 9 个 POST endpoint
    route/fundamental/  基本面 12 个 service / 12 个 POST endpoint
    route/news/         新闻    1 个 service / 1 个 POST endpoint
    route/sentiment/    情绪面  1 个 service / 1 个 POST endpoint
                        ─── 28 service / 28 POST endpoint

URL 规则（API_V1_PREFIX = /api）：
    POST /api/collect/{facet}/{service_name}     采集入口（写库 or 实时）
    GET  /api/collect/services                   28 service 元数据 catalog（在 router_compat.py 单独挂）
    GET  /api/collect/query/{service_name}       实时查询入口（在 router_compat.py 单独挂）

⚠️ 旧的 registry 自动注册、dynamic dispatch、4 个 manage 接口已全部删除。
⚠️ schedule / log / APScheduler 相关功能暂时不做（先做最基础的全量/条件采集）

⚠️ 5 个 facet router 的 prefix 已写死为 "/collect/{facet}"，本文件不再 include 它们；
    它们由 router_compat.py 直接 include 到 api_router（prefix="/api"）。
    /services 和 /query 在本文件以 standalone router 形式提供给 router_compat。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from shared.interface import _response as R
from shared.infrastructure.config.settings import get_settings
from contexts.collect.application.service.tech import (
    DailyKlineService, MinuteKlineService, AdjFactorService,
    SuspendService, NameChangeService,
)
from contexts.collect.application.service.capital import (
    MoneyflowService, MoneyflowHsgtService, TopListService, TopInstService,
    BlockTradeService, MarginService, HsgtTop10Service, LimitListService,
    HolderNumberService,
)
from contexts.collect.application.service.fundamental import (
    DailyBasicService, FinIncomeService, Top10HoldersService,
    Top10FloatHoldersService, DividendService, StockBasicService,
    StockConceptsService, ConceptListService, ConceptMembersService,
    ConceptIndexDailyService, ConceptMinuteService, ConceptSnapshotService,
)
from contexts.collect.application.service.news import NewsService
from contexts.collect.application.service.sentiment import SentimentService

from contexts.collect.interface.route.tech import router as tech_router
from contexts.collect.interface.route.capital import router as capital_router
from contexts.collect.interface.route.fundamental import router as fundamental_router
from contexts.collect.interface.route.news import router as news_router
from contexts.collect.interface.route.sentiment import router as sentiment_router


# 导出 5 个 facet router 给 router_compat.py 用（由它直接挂到 api_router）
facet_routers = (
    tech_router,
    capital_router,
    fundamental_router,
    news_router,
    sentiment_router,
)


# ═══════════════════════════════════════════════════════════════════════
#  /collect/services + /collect/query — catalog + 实时查询
#  （这两个 endpoint 不属于任何 facet，单独立个 router）
# ═══════════════════════════════════════════════════════════════════════

# 实时查询 service 集合（这些 service 不入库，collect() 无副作用，仅 get() 实时拉）
_REAL_TIME_ONLY: frozenset[str] = frozenset({
    "minute_kline",      # 分K线
    "concept_minute",    # 概念分时
    "concept_snapshot",  # 概念快照
})

# 空壳 / 占位 service —— catalog 中隐藏（前端不展示）
_HIDDEN_SERVICES: frozenset[str] = frozenset({
    "sentiment",  # 暂无 fetcher
})


def _infer_param_ui(key: str, default: Any) -> dict[str, Any]:
    """根据 DEFAULT_PARAMS 的 key/value 推导前端 ui schema

    返回 dict 含: key, ui, required, description（前端 CollectActionCard 用）
    """
    k = key.lower()
    val = default

    # ── 列表类 ──
    if isinstance(val, list):
        if k == "symbols":
            ui = "symbols_list"
        elif k == "index_codes":
            ui = "index_codes_list"
        else:
            ui = "str_list"
        return {
            "key": key, "ui": ui, "required": True,
            "description": f"{key}（列表）",
        }

    # ── 字符串类（含 None 默认值）──
    if isinstance(val, str) or val is None:
        if k.endswith("_date") or k == "date":
            ui = "date_str"
        elif k == "symbol":
            ui = "symbol_str"
        elif k == "ts_code":
            ui = "ts_code_str"
        elif k == "index_code":
            ui = "index_code_str"
        elif k == "list_status":
            ui = "list_status"
        elif k == "exchange":
            ui = "exchange_multi"
        elif k == "interval":
            ui = "interval_kline"
        elif k == "period":
            ui = "period_kline"
        else:
            ui = "str"
        return {
            "key": key, "ui": ui, "required": False,
            "description": f"{key}",
        }

    # ── 整数类 ──
    if isinstance(val, int) and not isinstance(val, bool):
        if k == "minutes":
            ui = "minutes_int"
        elif k == "days":
            ui = "days_int"
        elif k == "years":
            ui = "years_int"
        elif k == "limit":
            ui = "limit_int"
        else:
            ui = "int"
        return {
            "key": key, "ui": ui, "required": False,
            "description": f"{key}",
        }

    # ── 布尔 ──
    if isinstance(val, bool):
        return {
            "key": key, "ui": "bool_flag", "required": False,
            "description": f"{key}",
        }

    # 兜底
    return {
        "key": key, "ui": "str", "required": False,
        "description": f"{key}",
    }


def _derive_param_schema(default_params: dict[str, Any]) -> list[dict[str, Any]]:
    """从 DEFAULT_PARAMS 推导前端 param_schema（每个 param 的 ui 类型）"""
    return [_infer_param_ui(k, v) for k, v in default_params.items()]


def _build_catalog() -> tuple[list[dict[str, Any]], dict[str, type]]:
    """从每个 service class 反射出元数据（读 class attribute，不实例化）

    Returns:
        items:    catalog list（前端用）
        cls_map:  name → service class（query endpoint 用）
    """
    services = [
        # tech 5
        DailyKlineService, MinuteKlineService, AdjFactorService,
        SuspendService, NameChangeService,
        # capital 9
        MoneyflowService, MoneyflowHsgtService, TopListService, TopInstService,
        BlockTradeService, MarginService, HsgtTop10Service, LimitListService,
        HolderNumberService,
        # fundamental 12
        DailyBasicService, FinIncomeService, Top10HoldersService,
        Top10FloatHoldersService, DividendService, StockBasicService,
        StockConceptsService, ConceptListService, ConceptMembersService,
        ConceptIndexDailyService, ConceptMinuteService, ConceptSnapshotService,
        # news 1
        NewsService,
        # sentiment 1
        SentimentService,
    ]

    api_prefix = get_settings().API_V1_PREFIX  # "/api"

    items: list[dict[str, Any]] = []
    cls_map: dict[str, type] = {}
    for cls in services:
        name = cls.name
        if name in _HIDDEN_SERVICES:
            continue  # 空壳/占位 service，catalog 中不展示
        default_params = dict(getattr(cls, "DEFAULT_PARAMS", {}) or {})
        facet = getattr(cls, "facet", "") or ""
        has_get = hasattr(cls, "get") and callable(getattr(cls, "get", None))
        cls_map[name] = cls

        # 决定 kind：
        #   realtime = 不入库、只实时查询（白名单）
        #   both     = 既能 collect 也能 query
        #   collect  = 只能 collect
        if name in _REAL_TIME_ONLY:
            kind = "realtime"
        elif has_get:
            kind = "both"
        else:
            kind = "collect"

        items.append({
            "name": name,
            "facet": facet,
            "sub_facet": getattr(cls, "sub_facet", ""),
            "label": getattr(cls, "label", "") or name,
            "description": getattr(cls, "description", ""),
            "default_params": default_params,
            "param_schema": _derive_param_schema(default_params),
            "rate_limit": getattr(cls, "RATE_LIMIT", None),
            "concurrency": int(getattr(cls, "CONCURRENCY", 1) or 1),
            "supports_query": has_get,
            "kind": kind,
            # 实际可调用的 POST 路径：/api/collect/{facet}/{name}
            "path": f"{api_prefix}/collect/{facet}/{name}",
            # 实时查询（仅 has_get 时使用）
            "query_path": f"{api_prefix}/collect/query/{name}" if has_get else None,
        })
    items.sort(key=lambda x: (x["facet"], x["sub_facet"], x["name"]))
    return items, cls_map


_SERVICE_CATALOG, _SERVICE_CLS_BY_NAME = _build_catalog()
_SERVICE_BY_NAME: dict[str, dict[str, Any]] = {s["name"]: s for s in _SERVICE_CATALOG}


# catalog + query 的 standalone router（prefix="/collect"）—— 由 router_compat.py 挂到 api_router
catalog_router = APIRouter(prefix="/collect", tags=["采集-管理"])


@catalog_router.get(
    "/services",
    summary="28 service 元数据 catalog（前端左侧目录树数据源）",
    response_description="{ total, items: [...] }",
)
async def list_services_endpoint() -> dict[str, Any]:
    """列出全部 28 service 的元数据

    响应 data: { total, items: [{name, facet, sub_facet, label, description,
                                 default_params, param_schema, rate_limit,
                                 concurrency, supports_query, kind, path, query_path}, ...] }
    """
    return R.ok({"total": len(_SERVICE_CATALOG), "items": _SERVICE_CATALOG})


@catalog_router.get(
    "/query/{service_name}",
    summary="实时查询 service.get()",
    response_description="list[dict]（service 决定）",
)
async def query_service_endpoint(
    service_name: str,
    params: str = "",  # JSON-encoded kwargs; 留空表示无参数
) -> dict[str, Any]:
    """对 supports_query=true 的 service 调 get(**kwargs)

    入参用 query string `params=<JSON>`，例如：
        ?params={"symbol":"000001","interval":"5","days":1}

    留空表示无参数（service.get() 不带 kwargs 调用）。
    这种"传一个 JSON 串"的形式是为了不被 FastAPI 当成未声明的 query 参数而 422。
    """
    meta = _SERVICE_BY_NAME.get(service_name)
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"service {service_name!r} 不存在",
        )
    if not meta.get("supports_query"):
        raise HTTPException(
            status_code=400,
            detail=f"service {service_name!r} 不支持实时查询（supports_query=false）",
        )

    import json as _json
    if params.strip():
        try:
            kwargs = _json.loads(params)
        except _json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"params 不是合法 JSON: {e}",
            )
        if not isinstance(kwargs, dict):
            raise HTTPException(
                status_code=400,
                detail="params 必须是 JSON object",
            )
    else:
        kwargs = {}

    cls = _SERVICE_CLS_BY_NAME[service_name]
    svc = cls()  # 无状态 DefaultConstruct
    try:
        result = await svc.get(**kwargs)
    except TypeError as e:
        # get() 签名不匹配 / 缺参数
        raise HTTPException(status_code=400, detail=f"参数错误: {e}")
    return R.ok(result)


# 供测试 / 其他模块调用
def list_all_services() -> list[dict[str, Any]]:
    return list(_SERVICE_CATALOG)


__all__ = ["catalog_router", "facet_routers", "list_all_services"]

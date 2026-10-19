"""manage/catalog_service — catalog 业务逻辑

从 collect 模块 5 个 facet 下的 28 个 service class 反射出元数据，
提供给前端的 GET /collect/catalog 端点（2026-10 从 /services 改名为 /catalog）。

service 自己声明 UI_SCHEMA（class attribute），catalog 直接读取，不再推导。
"""
from __future__ import annotations

from typing import Any

from shared.infrastructure.config.settings import get_settings


# ═══════════════════════════════════════════════════════════════════════
# 导入 28 个 service class（按 facet 分组，与 application/service/{facet}/__init__.py 镜像）
# ═══════════════════════════════════════════════════════════════════════
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


# catalog 中隐藏（前端不展示）
_HIDDEN_SERVICES: frozenset[str] = frozenset({
    "sentiment",  # 暂无 fetcher（空壳）
})

# 实时查询 service（只 get()，无 collect() 入库）
_REAL_TIME_ONLY: frozenset[str] = frozenset({
    "minute_kline",      # 分 K 线
    "concept_minute",    # 概念分时
    "concept_snapshot",  # 概念快照
})


class CatalogService:
    """catalog 业务：service class 列表 → 元数据 dict list

    启动时一次性反射 28 个 service class，构造 items 列表；
    list() / get() 都是 O(n) 内存扫描，规模 28，无需缓存。
    """

    def __init__(self, services: tuple[type, ...] | None = None) -> None:
        # 注入式：测试时可传入假 service 列表
        self._services = services or self._default_services()
        self._api_prefix = get_settings().API_V1_PREFIX  # "/api"
        self._cls_by_name: dict[str, type] = {
            self._name_of(cls): cls for cls in self._services
        }
        self._items: list[dict[str, Any]] = [
            self._to_item(cls) for cls in self._services
        ]
        self._items.sort(key=lambda x: (x["facet"], x["name"]))

    @staticmethod
    def _name_of(cls: type) -> str:
        """兼容 META 写法：取 service 名"""
        meta = getattr(cls, "META", None)
        if meta is not None:
            return meta.name
        return getattr(cls, "name", cls.__name__)

    @staticmethod
    def _default_services() -> tuple[type, ...]:
        """默认 28 个 service class 列表"""
        return (
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
        )

    def list(self) -> list[dict[str, Any]]:
        """返回过滤后的 catalog（去掉 _HIDDEN_SERVICES）"""
        return [it for it in self._items if it["name"] not in _HIDDEN_SERVICES]

    def get(self, name: str) -> dict[str, Any] | None:
        for it in self._items:
            if it["name"] == name:
                if it["name"] in _HIDDEN_SERVICES:
                    return None
                return it
        return None

    def get_class(self, name: str) -> type | None:
        return self._cls_by_name.get(name)

    def _to_item(self, cls: type) -> dict[str, Any]:
        """service class → catalog item dict

        兼容两种写法：
            v1 旧写法: class attribute  (cls.name / cls.facet / cls.label / ...)
            v2 新写法: META dataclass    (cls.META.name / cls.META.facet / ...)
        优先读 META，没有再 fallback 到 class attribute。
        """
        # ★ 优先读 META（新写法）
        meta = getattr(cls, "META", None)
        if meta is not None:
            name = meta.name
            facet = meta.facet
            label = meta.label or name
            description = meta.description or ""
        else:
            # fallback: 旧写法（class attribute）
            name = getattr(cls, "name", cls.__name__)
            facet = getattr(cls, "facet", "") or ""
            label = getattr(cls, "label", "") or name
            description = getattr(cls, "description", "")

        default_params = dict(getattr(cls, "DEFAULT_PARAMS", {}) or {})
        has_get = hasattr(cls, "get") and callable(getattr(cls, "get", None))

        # kind 决定：优先读 META（新写法）；回退到黑名单（兼容旧 service）
        meta_kind = getattr(meta, "kind", None) if meta is not None else None
        if meta_kind is not None:
            # META 已声明（v2 新写法）
            kind = meta_kind.value
        elif name in _REAL_TIME_ONLY:
            kind = "realtime"
        elif has_get:
            kind = "both"
        else:
            kind = "collect"

        # incremental：是否需要时间范围（前端用于显示时间选择器）
        #   - INCREMENTAL → True
        #   - FULL_REFRESH / REALTIME / 旧 service 无 META → False
        if meta_kind is not None:
            incremental = meta_kind.value == "incremental"
        else:
            incremental = False

        return {
            "name": name,
            "facet": facet,
            "label": label,
            "description": description,
            "default_params": default_params,
            "param_schema": [],
            "rate_limit": None,
            "concurrency": 1,
            "supports_query": has_get,
            "kind": kind,
            # 增量采集标志（true → 前端显示时间选择器）
            "incremental": incremental,
            # 实际可调用的 POST 路径
            "path": f"{self._api_prefix}/collect/{facet}/{name}",
            # 实时查询（仅 has_get 时使用）
            "query_path": f"{self._api_prefix}/collect/query/{name}" if has_get else None,
        }


__all__ = ["CatalogService"]

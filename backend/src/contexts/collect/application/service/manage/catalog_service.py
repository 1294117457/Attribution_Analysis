"""manage/catalog_service — catalog 业务逻辑

从 collect 模块 5 个 facet 下的 28 个 service class 反射出元数据，
提供给前端的 GET /collect/catalog 端点（2026-10 从 /services 改名为 /catalog）。

service 只需在 META 中声明：
  - name        全局唯一标识（对应 fetcher 索引 key）
  - facet       大类（tech / capital / fundamental / news / sentiment）
  - label       前端展示名
  - description 描述
  - kind        采集类型（incremental / full_refresh / realtime）— 决定 UI 展示

可选的运行期配置：
  - rate_limit  (source, count, window)
  - concurrency 并发上限
"""
from __future__ import annotations

from typing import Any

from shared.infrastructure.config.settings import get_settings


# ═══════════════════════════════════════════════════════════════════════
# 导入 28 个 service class（按 facet 分组，与 application/service/{facet}/__init__.py 镜像）
# ═══════════════════════════════════════════════════════════════════════
from contexts.collect.application.service.tech import (
    DailyService, MinuteService, AdjFactorService,
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
            DailyService, MinuteService, AdjFactorService,
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

        直接读 cls.META（service 唯一元数据来源），不再有 class 层级 fallback。
        返回字段：
          name            全局唯一标识
          facet           大类
          label           前端展示名
          description     描述
          kind            采集类型（incremental/full_refresh/realtime）— 决定 UI
          supports_query  是否有 get() 方法（用于实时查询）
          path            POST 触发路径
          query_path      GET 实时查询路径（仅 supports_query=true）
        """
        meta = getattr(cls, "META", None)
        if meta is None:
            # 兜底：旧写法（class attribute）；但所有 service 都应该用 META
            name = getattr(cls, "name", cls.__name__)
            facet = getattr(cls, "facet", "") or ""
            label = getattr(cls, "label", "") or name
            description = getattr(cls, "description", "")
            kind = "full_refresh"
        else:
            name = meta.name
            facet = meta.facet
            label = meta.label or name
            description = meta.description
            kind = meta.kind.value

        has_get = hasattr(cls, "get") and callable(getattr(cls, "get", None))

        return {
            "name": name,
            "facet": facet,
            "label": label,
            "description": description,
            "kind": kind,
            "supports_query": has_get,
            # 实际可调用的 POST 路径
            "path": f"{self._api_prefix}/collect/{facet}/{name}",
            # 实时查询（仅 has_get 时使用）
            "query_path": f"{self._api_prefix}/collect/query/{name}" if has_get else None,
        }


__all__ = ["CatalogService"]

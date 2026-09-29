"""单元解析器（UnitResolver）

把 UnitSpec 翻译成实际的 unit 列表。

支持的 unit_source：
  - "stock_infos"   从 stock_infos 表拉所有在市股票
  - "trading_dates" 从交易日历拉交易日
  - "concepts"      从 concepts 表拉所有激活概念
  - "none"          noop，单元数为 1
  - 自定义：未来扩展

P0 阶段数据源用 fixture/内存实现，避免引入数据库依赖；后续接入真实 DB。
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, AsyncIterator, Callable

from infrastructure.adapter.pipeline.pipeline import UnitSpec

logger = logging.getLogger(__name__)

# 单元解析器注册表
_unit_resolvers: dict[str, Callable[[UnitSpec, dict], AsyncIterator[dict]]] = {}


def register_unit_resolver(name: str, fn: Callable[[UnitSpec, dict], AsyncIterator[dict]]) -> None:
    """注册自定义单元解析器"""
    _unit_resolvers[name] = fn


class UnitResolver:
    """UnitSpec → AsyncIterator[unit dict]"""

    async def resolve(self, spec: UnitSpec, params: dict) -> AsyncIterator[dict]:
        """解析 unit 列表，逐个 yield

        unit dict 形态（per_unit 风格）：
            {
                "label": "600519",          # 显示用
                "symbol": "600519",          # 业务字段（unit_template 定义）
                ...其他 unit_template 字段
            }
        """
        if spec.style == "one_shot":
            yield self._merge_defaults({}, spec.default_unit_args, {"label": spec.unit_source or "once"})
            return

        if spec.style == "streaming":
            yield {"label": "stream"}
            return

        # per_unit
        resolver = _unit_resolvers.get(spec.unit_source)
        if resolver is None:
            raise ValueError(f"未知的 unit_source: {spec.unit_source!r}")

        async for raw_unit in resolver(spec, params):
            # 用 unit_template 渲染单元 dict
            unit = {}
            for key, tmpl in spec.unit_template.items():
                unit[key] = _render_simple(tmpl, raw_unit)
            unit["label"] = unit.get("label") or str(raw_unit.get("symbol") or raw_unit.get("date") or raw_unit.get("index_code") or "")
            # 合并 unit-level 默认参数（如 days=7）
            for k, v in spec.default_unit_args.items():
                unit.setdefault(k, v)
            yield unit

    @staticmethod
    def _merge_defaults(*dicts: dict) -> dict:
        """合并多个 dict，后面的覆盖前面的"""
        result = {}
        for d in dicts:
            result.update(d)
        return result


# ═══════════════════════════════════════════════════════════════════════
# 内置 unit resolvers（fixture 版）
# ═══════════════════════════════════════════════════════════════════════


async def _resolve_stocks(spec: UnitSpec, params: dict) -> AsyncIterator[dict]:
    """股票池 unit resolver

    优先从 params.stock_symbols 拿（手动触发时传入），
    否则从内置 fixture 拿（10 只测试股票）。
    """
    if params.get("stock_symbols"):
        for sym in params["stock_symbols"]:
            yield {"symbol": sym}
        return

    # fixture: 10 只常见股票
    fix = params.get("_fixture_stocks") or [
        "600519", "000001", "601318", "600036", "000858",
        "600276", "601012", "002594", "300750", "688981",
    ]
    for sym in fix:
        yield {"symbol": sym}


async def _resolve_dates(spec: UnitSpec, params: dict) -> AsyncIterator[dict]:
    """交易日 unit resolver

    优先从 params.trade_dates 拿（手动触发时传入），
    否则按 params.days 回算（默认 1 个，最近 1 个交易日）。
    """
    if params.get("trade_dates"):
        for d in params["trade_dates"]:
            yield {"date": str(d)}
        return

    # 默认最近 1 天
    days = params.get("days", 1) or 1
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        yield {"date": d.strftime("%Y%m%d")}


async def _resolve_concepts(spec: UnitSpec, params: dict) -> AsyncIterator[dict]:
    """概念 unit resolver

    fixture: 5 个常见概念 index_code。
    """
    fix = params.get("_fixture_concepts") or [
        "885001", "885002", "885003", "885004", "885005",
    ]
    for c in fix:
        yield {"index_code": c, "name": c}


async def _resolve_concepts_by_stock(spec: UnitSpec, params: dict) -> AsyncIterator[dict]:
    """股票→概念 unit resolver（与 _resolve_stocks 共用）"""
    async for u in _resolve_stocks(spec, params):
        yield u


# 注册内置 resolvers
register_unit_resolver("stock_infos", _resolve_stocks)
register_unit_resolver("trading_dates", _resolve_dates)
register_unit_resolver("concepts", _resolve_concepts)
register_unit_resolver("concepts_by_stock", _resolve_concepts_by_stock)


# ═══════════════════════════════════════════════════════════════════════
# 工具
# ═══════════════════════════════════════════════════════════════════════


def _render_simple(template: str, ctx: dict) -> str:
    """单层模板渲染（unit_template 专用）"""
    import re
    return re.sub(
        r"\{\{\s*([^{}]+?)\s*\}\}",
        lambda m: str(ctx.get(m.group(1).strip(), "")),
        template,
    )


__all__ = ["UnitResolver", "register_unit_resolver"]

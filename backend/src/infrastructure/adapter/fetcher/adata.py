"""adata 概念采集器（同花顺数据源）

概念相关数据全部由本采集器提供（清单 / 成分股 / 股票所属概念 / 指数日 K / 实时行情）。
全链路以同花顺指数编码 index_code（885xxx）为业务键。

adata 的两个行为需要在这里兜住：
- 被同花顺限流时部分接口 `return Exception(...)` 而不是 raise
- 接口正常但确实无数据时返回空 DataFrame —— 与"失败"必须区分，
  成分股任务据此决定是否删除旧关系

配套设计文档：docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.1
"""

from __future__ import annotations

import logging
import math
import time
from datetime import date, datetime
from typing import Any, Callable, Optional

import pandas as pd

from application.port.collector_port import ConceptFetcher
from infrastructure.adapter.fetcher.base import BaseCollector
from route.dto.request.concept import (
    ConceptIndexTHBO,
    ConceptListBO,
    ConceptMinuteBO,
    ConceptMinutePoint,
    ConceptOfStockBO,
)

logger = logging.getLogger(__name__)


class AdataThrottledError(RuntimeError):
    """adata 返回了 Exception 对象（通常是同花顺 IP 限流）"""


class AdataConceptFetcher(BaseCollector):
    """adata · 同花顺概念采集器（实现 ConceptFetcher 协议）"""

    SOURCE_NAME = "Adata-THS"
    REQUEST_DELAY = 0.5
    RETRY_BACKOFF = (1.0, 3.0)

    def __init__(self):
        super().__init__()
        self._adata = self._ensure_adata()

    @staticmethod
    def _ensure_adata():
        try:
            import adata
            return adata
        except ImportError:
            raise RuntimeError("adata 未安装：pip install adata==2.9.5")

    # ── 清单 ─────────────────────────────────────────

    def fetch_concept_list(self) -> list[ConceptListBO]:
        """全部同花顺概念；丢弃 index_code 为空的行（问财接口偶发缺失）"""
        df = self._call(lambda: self._adata.stock.info.all_concept_code_ths())
        items: list[ConceptListBO] = []
        seen: set[str] = set()
        for row in _rows(df):
            index_code = _code(row.get("index_code"))
            name = _str(row.get("name"))
            if not index_code or not name or index_code in seen:
                continue
            seen.add(index_code)
            items.append(ConceptListBO(
                index_code=index_code,
                concept_code=_code(row.get("concept_code")),
                name=name,
            ))
        return items

    # ── 成分股 / 所属概念 ────────────────────────────

    def fetch_constituents(self, index_code: str, delay: Optional[float] = None) -> list[str]:
        """概念 → 股票（6 位 symbol，去重保序）；接口正常但无数据返回 []"""
        df = self._call(
            lambda: self._adata.stock.info.concept_constituent_ths(index_code=index_code),
            delay=delay,
        )
        symbols: list[str] = []
        seen: set[str] = set()
        for row in _rows(df):
            symbol = _symbol(row.get("stock_code"))
            if symbol and symbol not in seen:
                seen.add(symbol)
                symbols.append(symbol)
        return symbols

    def fetch_concepts_by_stock(self, symbol: str, delay: Optional[float] = None) -> list[ConceptOfStockBO]:
        """股票 → 概念（带入选理由）"""
        symbol = _symbol(symbol)
        if not symbol:
            return []
        try:
            df = self._call(
                lambda: self._adata.stock.info.get_concept_ths(stock_code=symbol),
                delay=delay,
            )
        except AttributeError:
            # F10 页面没有概念表格（无概念 / 新股）时 adata 内部 None.tbody
            return []
        items: list[ConceptOfStockBO] = []
        for row in _rows(df):
            index_code = _code(row.get("concept_code"))
            name = _str(row.get("name"))
            if not index_code or not name:
                continue
            items.append(ConceptOfStockBO(
                symbol=symbol,
                index_code=index_code,
                name=name,
                reason=_str(row.get("reason")),
            ))
        return items

    # ── 行情 ─────────────────────────────────────────

    def fetch_index_daily(
        self, index_code: str, concept_name: str = "", delay: Optional[float] = None,
    ) -> list[ConceptIndexTHBO]:
        """概念指数日 K（接口无日期参数，总是返回全部历史）"""
        df = self._call(
            lambda: self._adata.stock.market.get_market_concept_ths(index_code=index_code, k_type=1),
            delay=delay,
        )
        items: list[ConceptIndexTHBO] = []
        for row in _rows(df):
            trade_date = _date(row.get("trade_date"))
            close = _float(row.get("close"))
            if trade_date is None or close is None:
                continue
            items.append(ConceptIndexTHBO(
                index_code=index_code,
                concept_name=concept_name,
                trade_date=trade_date,
                open=_float(row.get("open")) or 0.0,
                high=_float(row.get("high")) or 0.0,
                low=_float(row.get("low")) or 0.0,
                close=close,
                volume=int(_float(row.get("volume")) or 0),
                amount=_float(row.get("amount")) or 0.0,
                change=_float(row.get("change")),
                change_pct=_float(row.get("change_pct")),
            ))
        return items

    def fetch_current_snapshot(self, index_code: str, delay: Optional[float] = None) -> Optional[dict]:
        """概念当前行情快照（adata stock.market.get_market_concept_current_ths）

        用于补全概念大盘 / 实时涨幅快照。返回 dict（不引入新 BO 类型）。
        """
        df = self._call(
            lambda: self._adata.stock.market.get_market_concept_current_ths(index_code=index_code),
            delay=delay,
        )
        for row in _rows(df):
            return {
                "index_code": index_code,
                "price": _float(row.get("price")),
                "change": _float(row.get("change")),
                "change_pct": _float(row.get("change_pct")),
                "volume": _float(row.get("volume")),
                "amount": _float(row.get("amount")),
                "open": _float(row.get("open")),
                "high": _float(row.get("high")),
                "low": _float(row.get("low")),
                "prev_close": _float(row.get("prev_close")),
                "turnover_rate": _float(row.get("turnover_rate")),
                "pe": _float(row.get("pe")),
                "pb": _float(row.get("pb")),
                "trade_time": _str(row.get("trade_time")),
            }
        return None

    def fetch_minute(self, index_code: str, delay: Optional[float] = 0) -> Optional[ConceptMinuteBO]:
        """概念当日分时（实时接口，默认不限速；限流由 RealtimeQueryFramework 的并发信号量控制）"""
        df = self._call(
            lambda: self._adata.stock.market.get_market_concept_min_ths(index_code=index_code),
            delay=delay,
        )
        points: list[ConceptMinutePoint] = []
        pre_close: Optional[float] = None
        last: dict = {}
        trade_date: Optional[str] = None
        for row in _rows(df):
            price = _float(row.get("price"))
            if price is None:
                continue
            change = _float(row.get("change"))
            if pre_close is None and change is not None:
                pre_close = round(price - change, 4)
            volume = _float(row.get("volume"))
            trade_time = _datetime(row.get("trade_time"))
            points.append(ConceptMinutePoint(
                trade_time=trade_time.strftime("%H:%M") if trade_time else _str(row.get("trade_time")) or "",
                price=price,
                avg_price=_float(row.get("avg_price")),
                volume=int(volume) if volume is not None else None,
                amount=_float(row.get("amount")),
                change_pct=_float(row.get("change_pct")),
            ))
            last = {"price": price, "change": change, "change_pct": _float(row.get("change_pct")),
                    "trade_time": trade_time.strftime("%Y-%m-%d %H:%M") if trade_time else None}
            trade_date = _str(row.get("trade_date")) or trade_date
        if not points:
            return None
        return ConceptMinuteBO(
            index_code=index_code,
            trade_date=trade_date,
            pre_close=pre_close,
            price=last["price"],
            change=last["change"],
            change_pct=last["change_pct"],
            trade_time=last["trade_time"],
            points=points,
        )

    # ── 调用封装 ─────────────────────────────────────

    def _call(self, fn: Callable[[], Any], delay: Optional[float] = None) -> Any:
        """限速 + 重试；adata 返回 Exception 对象视为限流"""
        attempts = len(self.RETRY_BACKOFF) + 1
        for i in range(attempts):
            time.sleep(self.REQUEST_DELAY if delay is None else delay)
            try:
                result = fn()
                if isinstance(result, Exception):
                    raise AdataThrottledError(str(result))
                return result
            except AttributeError:
                raise
            except Exception as e:
                if i == attempts - 1:
                    raise
                backoff = self.RETRY_BACKOFF[i]
                logger.debug("adata 请求失败，%.0fs 后重试 %d/%d: %s", backoff, i + 1, attempts - 1, e)
                time.sleep(backoff)


AdataConceptFetcher.__implements_protocol__ = ConceptFetcher


# ── 解析辅助 ───────────────────────────────────────────


def _rows(df) -> list[dict]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.to_dict("records")


def _is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and not v.strip())


def _str(v) -> Optional[str]:
    if _is_missing(v):
        return None
    return str(v).strip() or None


def _code(v) -> Optional[str]:
    s = _str(v)
    if s is None:
        return None
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _symbol(v) -> Optional[str]:
    s = _code(v)
    if s is None:
        return None
    s = s.zfill(6)
    return s if len(s) == 6 and s.isdigit() else None


def _float(v) -> Optional[float]:
    if _is_missing(v):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _date(v) -> Optional[date]:
    if _is_missing(v):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _datetime(v) -> Optional[datetime]:
    if _is_missing(v):
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.strptime(str(v)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
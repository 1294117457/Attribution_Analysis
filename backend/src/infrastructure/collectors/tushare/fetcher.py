"""Tushare Pro 数据采集器（ACL 实现）

实现 FetcherProtocol，使用 tushare.pro_api() 拉取数据：
- 日线行情（daily）
- 股票基本信息（stock_basic）

环境变量:
- TUSHARE_TOKEN  (在 .env 中配置，Pydantic-Settings 读取)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from domain.kline.schemas import KlineBO
from domain.stock_info.schemas import StockInfoBO
from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.collectors.tushare.parser import TushareKlineParser

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 股票代码 → Tushare ts_code 转换
# ═══════════════════════════════════════════════════════════════

def symbol_to_ts_code(symbol: str) -> str:
    """把 6 位股票代码转换为 Tushare ts_code。"""
    if not symbol or len(symbol) != 6 or not symbol.isdigit():
        raise ValueError(f"无效的股票代码: {symbol!r}，应为 6 位数字")

    prefix2 = symbol[:2]
    prefix3 = symbol[:3]

    if prefix2 in ("83", "87", "43", "82"):
        return f"{symbol}.BJ"

    if prefix3 in ("600", "601", "603", "605", "688", "689"):
        return f"{symbol}.SH"

    return f"{symbol}.SZ"


def parse_list_date(s) -> Optional[date]:
    """YYYYMMDD 字符串 → date"""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip()
    if not s or s == "0" or s == "00000000":
        return None
    try:
        return pd.to_datetime(s, format="%Y%m%d").date()
    except Exception:
        try:
            return pd.to_datetime(s).date()
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════
# 主类
# ═══════════════════════════════════════════════════════════════

class TushareFetcher(BaseCollector):
    """Tushare 数据采集器"""

    def __init__(self, data_type: type = KlineBO):
        super().__init__()
        self._kline_type = data_type
        if data_type is not KlineBO:
            raise ValueError(
                f"TushareFetcher 仅支持 KlineBO，当前类型: {data_type.__name__}"
            )
        self._parser = TushareKlineParser()
        self._name_cache: dict[str, str] = {}

        # 延迟导入，避免未安装时影响 AKShare 路径
        import tushare as ts  # noqa: WPS433
        from infrastructure.config import get_settings

        token = get_settings().TUSHARE_TOKEN
        if not token:
            raise RuntimeError(
                "TUSHARE_TOKEN 未配置，请在 .env 中设置"
            )
        ts.set_token(token)
        self._pro = ts.pro_api()

    @property
    def source_name(self) -> str:
        return "Tushare"

    # ── K线采集 ─────────────────────────────────────────────

    def _resolve_name(self, symbol: str, ts_code: str) -> str:
        """查询股票名称（带缓存）"""
        if symbol in self._name_cache:
            return self._name_cache[symbol]
        try:
            df = self._pro.stock_basic(
                ts_code=ts_code,
                fields="ts_code,name",
            )
            if df is not None and not df.empty:
                name = str(df.iloc[0]["name"])
                self._name_cache[symbol] = name
                return name
        except Exception as e:
            self._log("warning", f"查询股票名称失败 {symbol}: {e}")
        return ""

    def fetch(self, params: CollectParams) -> list[KlineBO]:
        """K 线采集"""
        if not params.symbol:
            raise ValueError("采集 K 线需要提供 symbol")

        ts_code = symbol_to_ts_code(params.symbol)
        stock_name = self._resolve_name(params.symbol, ts_code)

        end_date = params.end_date or date.today()
        start_date = params.start_date or (end_date - timedelta(days=params.days))

        buf_start = start_date - timedelta(days=2)
        start_str = buf_start.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        self._log("info", f"开始采集: {params.symbol} ({ts_code}) {buf_start}→{end_date}")

        try:
            df = self._pro.daily(
                ts_code=ts_code,
                start_date=start_str,
                end_date=end_str,
            )
        except Exception as e:
            raise self._wrap_error(f"调用 Tushare daily() 失败", e)

        if df is None or df.empty:
            self._log("warning", f"{params.symbol}: Tushare 返回空数据")
            return []

        df = df.sort_values("trade_date").reset_index(drop=True)
        klines = self._parser.parse(df, params.symbol)

        if stock_name:
            for k in klines:
                k.name = stock_name

        self._log(
            "info",
            f"采集完成: {params.symbol}, 获取 {len(klines)} 条, name={stock_name!r}",
        )
        return klines

    # ── 股票基本信息采集 ────────────────────────────────────

    def fetch_stock_basic(self, params: CollectParams) -> list[StockInfoBO]:
        """全量拉取 A 股股票基本信息

        Args:
            params.list_status: L=上市, D=退市, P=暂停上市, 默认 L
        """
        list_status = (params.list_status or "L").upper()
        self._log("info", f"开始拉取 stock_basic: list_status={list_status}")

        all_stocks: list[StockInfoBO] = []
        # Tushare 单次最多 6000 条，A 股 ~5400 条，一次取完即可
        # 但为稳妥起见，按交易所分批
        exchanges = ["SSE", "SZSE", "BSE"]

        for ex in exchanges:
            try:
                df = self._pro.stock_basic(
                    exchange=ex,
                    list_status=list_status,
                    fields="ts_code,symbol,name,area,industry,market,exchange,list_date,delist_date,list_status,is_hs",
                )
            except Exception as e:
                self._log("warning", f"拉取 {ex} stock_basic 失败: {e}")
                continue

            if df is None or df.empty:
                self._log("info", f"{ex}: 无数据")
                continue

            for _, row in df.iterrows():
                try:
                    bo = self._row_to_stock_info_bo(row)
                    if bo:
                        all_stocks.append(bo)
                except Exception as e:
                    logger.warning("跳过无效行: %s", e)
                    continue

        self._log("info", f"stock_basic 同步完成，共 {len(all_stocks)} 条")
        return all_stocks

    @staticmethod
    def _row_to_stock_info_bo(row: pd.Series) -> Optional[StockInfoBO]:
        """DataFrame 行 → StockInfoBO"""
        symbol = row.get("symbol")
        if not symbol or pd.isna(symbol):
            return None
        return StockInfoBO(
            symbol=str(symbol).zfill(6),
            ts_code=row.get("ts_code") or None,
            name=str(row.get("name") or ""),
            area=row.get("area") or None,
            industry=row.get("industry") or None,
            market=row.get("market") or None,
            exchange=row.get("exchange") or None,
            list_date=parse_list_date(row.get("list_date")),
            delist_date=parse_list_date(row.get("delist_date")),
            list_status=str(row.get("list_status") or "L"),
            is_hs=str(row.get("is_hs") or "N"),
        )

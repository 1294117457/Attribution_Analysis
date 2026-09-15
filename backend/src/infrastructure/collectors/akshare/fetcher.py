"""AkShare 数据采集器（ACL 实现）

实现 FetcherProtocol，支持：
- 日线行情（stock_zh_a_hist）
- 股票基本信息（stock_info_a_code_name / stock_zh_a_spot_em）
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import akshare as ak
import pandas as pd

from domain.kline.schemas import KlineBO
from domain.stock_info.schemas import StockInfoBO
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.akshare.parser import KlineParser

logger = logging.getLogger(__name__)


def parse_yyyymmdd(s) -> Optional[date]:
    """YYYYMMDD 字符串 → date"""
    if s is None:
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


def infer_exchange(symbol: str) -> Optional[str]:
    """根据股票代码推断交易所"""
    if not symbol or len(symbol) != 6 or not symbol.isdigit():
        return None
    prefix2 = symbol[:2]
    prefix3 = symbol[:3]
    if prefix2 in ("83", "87", "43", "82"):
        return "BSE"
    if prefix3 in ("600", "601", "603", "605", "688", "689"):
        return "SSE"
    return "SZSE"


class AkShareFetcher(BaseCollector):
    """AkShare 数据采集器"""

    def __init__(self, data_type: type = KlineBO):
        super().__init__()
        self._kline_type = data_type
        if data_type is not KlineBO:
            raise ValueError(f"AkShareFetcher 仅支持 KlineBO，当前类型: {data_type.__name__}")
        self._parser = KlineParser()
        self._name_cache: dict[str, str] = {}

    @property
    def source_name(self) -> str:
        return "AkShare"

    # ── K线采集 ─────────────────────────────────────────────

    def fetch(self, params: CollectParams) -> list[KlineBO]:
        """执行 K 线采集"""
        self._log("info", f"开始采集: {params.symbol}")

        if not params.symbol:
            raise ValueError("采集K线需要提供 symbol")

        end_date = params.end_date or date.today()
        start_date = params.start_date or (end_date - timedelta(days=params.days))

        try:
            df = ak.stock_zh_a_hist(
                symbol=params.symbol,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=params.adjust,
            )
        except Exception as e:
            raise self._wrap_error(f"获取 {params.symbol} K线失败", e)

        klines = self._parser.parse(df, params.symbol)
        name = self._get_stock_name(params.symbol)
        for kline in klines:
            kline.name = name

        self._log("info", f"采集完成: {params.symbol}, 获取 {len(klines)} 条数据")
        return klines

    # ── 股票基本信息采集 ────────────────────────────────────

    def fetch_stock_basic(self, params: CollectParams) -> list[StockInfoBO]:
        """全量拉取 A 股股票基本信息

        AkShare 提供 stock_info_a_code_name（沪深京 A 股代码名称对照表），
        含 symbol/name，可作为全量列表。
        """
        self._log("info", "开始拉取 stock_basic（AkShare）")

        try:
            # 接口1：沪深京 A 股代码名称（轻量、含全量）
            df = ak.stock_info_a_code_name()
        except Exception as e:
            raise self._wrap_error("拉取 stock_info_a_code_name 失败", e)

        if df is None or df.empty:
            self._log("warning", "stock_info_a_code_name 返回空")
            return []

        # 列名映射（不同版本可能略不同）
        col_map = {
            "code": "symbol",
            "name": "name",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        if "symbol" not in df.columns or "name" not in df.columns:
            self._log("error", f"列名不匹配: {list(df.columns)}")
            return []

        results: list[StockInfoBO] = []
        for _, row in df.iterrows():
            symbol = str(row.get("symbol") or "").strip()
            if not symbol or len(symbol) != 6 or not symbol.isdigit():
                continue
            name = str(row.get("name") or "").strip()
            exchange = infer_exchange(symbol)

            results.append(StockInfoBO(
                symbol=symbol,
                ts_code=f"{symbol}.{ 'SH' if exchange == 'SSE' else 'SZ' if exchange == 'SZSE' else 'BJ' if exchange == 'BSE' else ''}",
                name=name,
                exchange=exchange,
                list_status="L",
                is_hs="N",
            ))

        self._log("info", f"stock_basic 同步完成，共 {len(results)} 条")
        return results

    # ── 辅助方法 ────────────────────────────────────────────

    def _get_stock_name(self, symbol: str) -> str:
        if symbol in self._name_cache:
            return self._name_cache[symbol]
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if not row.empty:
                name = str(row.iloc[0]["名称"])
                self._name_cache[symbol] = name
                return name
        except Exception as e:
            self._log("warning", f"获取股票名称失败: {symbol}", error=str(e))
        return ""

    def get_realtime_quote(self, symbol: str) -> dict:
        """获取实时行情（扩展接口）"""
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if not row.empty:
                return row.iloc[0].to_dict()
        except Exception as e:
            self._log("error", f"获取实时行情失败: {symbol}", error=str(e))
        return {}

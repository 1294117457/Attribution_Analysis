"""Tushare Pro 数据采集器（ACL 实现）

实现 FetcherProtocol，使用 tushare.pro_api() 拉取 A 股日线数据。

环境变量:
- TUSHARE_TOKEN  (在 .env 中配置，Pydantic-Settings 读取)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from domain.kline.schemas import KlineBO
from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.collectors.tushare.parser import TushareKlineParser

logger = logging.getLogger(__name__)


# ═────────────────────────────────────────────────────────────────────
# 股票代码 → Tushare ts_code 转换
# ═────────────────────────────────────────────────────────────────────

def symbol_to_ts_code(symbol: str) -> str:
    """把 6 位股票代码转换为 Tushare ts_code。

    判断规则（按前缀）：
      - SH: 600 / 601 / 603 / 605 / 688
      - BJ: 8 / 4
      - SZ: 其他（A 股主板/中小板/创业板）
    """
    if not symbol or len(symbol) != 6 or not symbol.isdigit():
        raise ValueError(f"无效的股票代码: {symbol!r}，应为 6 位数字")

    prefix2 = symbol[:2]
    prefix3 = symbol[:3]

    # 北交所
    if prefix2 in ("83", "87", "43", "82"):
        return f"{symbol}.BJ"

    # 上交所（主板 + 科创板）
    if prefix3 in ("600", "601", "603", "605", "688", "689"):
        return f"{symbol}.SH"

    # 深交所（主板、中小板、创业板）
    return f"{symbol}.SZ"


# ═────────────────────────────────────────────────────────────────────
# 主类
# ═────────────────────────────────────────────────────────────────────

class TushareFetcher(BaseCollector):
    """Tushare 数据采集器

    实现 FetcherProtocol。
    """

    def __init__(self, data_type: type = KlineBO):
        super().__init__()
        if data_type is not KlineBO:
            raise ValueError(
                f"TushareFetcher 仅支持 KlineBO，当前类型: {data_type.__name__}"
            )
        self._data_type = data_type
        self._parser = TushareKlineParser()
        self._name_cache: dict[str, str] = {}
        # 延迟导入，避免未安装时影响 AKShare 路径
        import tushare as ts  # noqa: WPS433
        from infrastructure.config import get_settings

        token = get_settings().TUSHARE_TOKEN
        if not token:
            raise RuntimeError(
                "TUSHARE_TOKEN 未配置，请在 .env 中设置或注入 COLLECTOR_SOURCE=akshare"
            )
        ts.set_token(token)
        self._pro = ts.pro_api()

    @property
    def source_name(self) -> str:
        return "Tushare"

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
        """执行采集，返回 KlineBO 列表"""
        if not params.symbol:
            raise ValueError("采集 K 线需要提供 symbol")

        ts_code = symbol_to_ts_code(params.symbol)

        # 提前拉股票名称（用于填充 KlineBO.name）
        stock_name = self._resolve_name(params.symbol, ts_code)

        end_date = params.end_date or date.today()
        start_date = params.start_date or (end_date - timedelta(days=params.days))

        # 留 2 天 buffer 防止周末/节假日边界
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

        # Tushare 默认按日期降序，统一一下让上层一致
        df = df.sort_values("trade_date").reset_index(drop=True)

        klines = self._parser.parse(df, params.symbol)

        # 把股票名填到每条 BO（domain 已知不依赖外部数据，name 是 metadata）
        if stock_name:
            for k in klines:
                k.name = stock_name

        self._log(
            "info",
            f"采集完成: {params.symbol}, 获取 {len(klines)} 条, name={stock_name!r}",
        )
        return klines

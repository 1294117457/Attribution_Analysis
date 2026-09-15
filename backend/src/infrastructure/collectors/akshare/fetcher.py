"""AkShare 数据采集器（ACL 实现）"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional, Any

import akshare as ak

from domain.kline.schemas import KlineBO
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.akshare.parser import KlineParser

logger = logging.getLogger(__name__)


class AkShareFetcher(BaseCollector):
    """AkShare 数据采集器

    实现 FetcherProtocol。
    """

    def __init__(self, data_type: type = KlineBO):
        super().__init__()
        if data_type is not KlineBO:
            raise ValueError(f"AkShareFetcher 仅支持 KlineBO，当前类型: {data_type.__name__}")
        self._data_type = data_type
        self._parser = KlineParser()
        self._name_cache: dict[str, str] = {}

    @property
    def source_name(self) -> str:
        return "AkShare"

    def fetch(self, params: CollectParams) -> list[KlineBO]:
        """执行采集，返回 KlineBO 列表"""
        self._log("info", f"开始采集: {params.symbol}")

        if not params.symbol:
            raise ValueError("采集K线需要提供 symbol")

        # 计算日期范围
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

        # 解析
        klines = self._parser.parse(df, params.symbol)

        # 补充股票名称
        name = self._get_stock_name(params.symbol)
        for kline in klines:
            kline.name = name

        self._log("info", f"采集完成: {params.symbol}, 获取 {len(klines)} 条数据")
        return klines

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

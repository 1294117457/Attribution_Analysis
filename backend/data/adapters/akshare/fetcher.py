"""AkShare 数据源适配器"""

import akshare as ak
from datetime import date, timedelta
from typing import Optional

from data.schemas.base import BaseData
from data.schemas.kline import DailyKline, StockInfo
from data.interfaces.fetcher import FetcherProtocol, CollectParams
from data.parsers.kline_parser import KlineParser


class AkShareFetcher:
    """AkShare 适配器，满足 FetcherProtocol

    根据 data_type 分发到对应的采集方法：
        AkShareFetcher(DailyKline)  → 采集日K线
    """

    def __init__(self, data_type: type[BaseData]):
        self._dispatch = {
            DailyKline: self._fetch_daily_kline,
        }
        handler = self._dispatch.get(data_type)
        if handler is None:
            supported = [t.__name__ for t in self._dispatch]
            raise ValueError(f"AkShareFetcher 不支持 {data_type.__name__}，支持: {supported}")
        self._handler = handler
        self._parser = KlineParser()

    def fetch(self, params: CollectParams) -> list[BaseData]:
        """执行采集，满足 FetcherProtocol"""
        return self._handler(params)

    # ── 私有采集方法 ──────────────────────────────────────────

    def _fetch_daily_kline(self, params: CollectParams) -> list[DailyKline]:
        """采集日K线数据"""
        end_date = params.end_date or date.today()
        start_date = params.start_date or (end_date - timedelta(days=params.days))

        try:
            df = ak.stock_zh_a_hist(
                symbol=params.symbol,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq",
            )
        except Exception as e:
            raise RuntimeError(f"获取 {params.symbol} K线失败: {e}")

        klines = self._parser.parse_kline_df(df, params.symbol)

        # 补充股票名称
        name = self._get_stock_name(params.symbol)
        for k in klines:
            k.name = name

        return klines

    def _get_stock_name(self, symbol: str) -> str:
        """获取股票名称"""
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if not row.empty:
                return row.iloc[0]["名称"]
        except Exception:
            pass
        return ""

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票基本信息（供外部直接调用）"""
        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            info = dict(zip(df["Item"], df["Content"]))
            return StockInfo(
                symbol=symbol,
                name=info.get("股票简称", ""),
                industry=info.get("行业", None),
                market=info.get("上市时间", None),
            )
        except Exception:
            return None

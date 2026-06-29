"""
数据采集服务。
整合 AkShare 客户端和数据存储。
"""

from typing import Optional
from datetime import datetime

from app.modules.collector.akshare_client import AkShareClient
from app.modules.collector.storage import KLineStorage
from app.modules.collector.schemas import (
    KLineRecord,
    StockInfo,
    CollectionResult,
    BatchCollectionResult,
)
from app.modules.config import CollectorConfig


class CollectorService:
    """数据采集服务"""

    def __init__(self, config: Optional[CollectorConfig] = None):
        self.config = config or CollectorConfig()
        self.client = AkShareClient(self.config)
        self.storage = KLineStorage()

    def collect_single(
        self,
        code: str,
        name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> CollectionResult:
        """
        采集单只股票数据。

        Args:
            code: 股票代码
            name: 股票名称
            start_date: 开始日期（YYYYMMDD），默认5年前
            end_date: 结束日期（YYYYMMDD），默认今天

        Returns:
            CollectionResult: 采集结果
        """
        # 默认5年回看
        if start_date is None:
            years_ago = datetime.now().year - self.config.lookback_years
            start_date = f"{years_ago}0101"

        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            klines = self.client.fetch_klines(code, start_date, end_date)

            if not klines:
                return CollectionResult(
                    code=code,
                    name=name,
                    collected=0,
                    saved=0,
                    success=False,
                    error="数据为空",
                )

            # 注入名称
            for kline in klines:
                kline.name = name

            saved = self.storage.save(klines)

            return CollectionResult(
                code=code,
                name=name,
                collected=len(klines),
                saved=saved,
                success=True,
            )

        except Exception as e:
            return CollectionResult(
                code=code,
                name=name,
                collected=0,
                saved=0,
                success=False,
                error=str(e),
            )

    def collect_batch(
        self,
        stocks: list[tuple[str, str]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> BatchCollectionResult:
        """
        批量采集多只股票数据。

        Args:
            stocks: 股票列表 [(代码, 名称), ...]
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            BatchCollectionResult: 批量采集结果
        """
        results = []
        total_collected = 0
        total_saved = 0
        success_count = 0

        for code, name in stocks:
            result = self.collect_single(code, name, start_date, end_date)
            results.append(result)

            total_collected += result.collected
            total_saved += result.saved
            if result.success:
                success_count += 1

        return BatchCollectionResult(
            total=len(stocks),
            success=success_count,
            failed=len(stocks) - success_count,
            total_collected=total_collected,
            total_saved=total_saved,
            results=results,
        )

    def collect_index(
        self,
        index_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> BatchCollectionResult:
        """
        采集某指数所有成分股数据。

        Args:
            index_code: 指数代码，如 "000300"（沪深300）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            BatchCollectionResult: 采集结果
        """
        stocks = self.client.get_index_components(index_code)

        if not stocks:
            return BatchCollectionResult(
                total=0,
                success=0,
                failed=0,
                total_collected=0,
                total_saved=0,
                results=[],
            )

        return self.collect_batch(stocks, start_date, end_date)

    def incremental_collect(
        self,
        stocks: list[tuple[str, str]],
    ) -> BatchCollectionResult:
        """
        增量采集：只采集最新数据（跳过已有数据）。

        Args:
            stocks: 股票列表

        Returns:
            BatchCollectionResult: 采集结果
        """
        results = []
        total_collected = 0
        total_saved = 0
        success_count = 0

        for code, name in stocks:
            # 获取最新日期
            latest_date = self.storage.get_latest_date(code)

            if latest_date:
                # 转换为 YYYYMMDD 格式
                date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
                start_date = date_obj.strftime("%Y%m%d")
            else:
                start_date = None

            result = self.collect_single(code, name, start_date, None)
            results.append(result)

            total_collected += result.collected
            total_saved += result.saved
            if result.success:
                success_count += 1

        return BatchCollectionResult(
            total=len(stocks),
            success=success_count,
            failed=len(stocks) - success_count,
            total_collected=total_collected,
            total_saved=total_saved,
            results=results,
        )

    def get_stock_info(self, code: str) -> Optional[StockInfo]:
        """获取股票基本信息"""
        return self.client.fetch_stock_info(code)

    def get_index_components(self, index_code: str) -> list[tuple[str, str]]:
        """获取指数成分股"""
        return self.client.get_index_components(index_code)

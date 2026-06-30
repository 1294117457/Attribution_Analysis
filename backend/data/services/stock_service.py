"""数据服务 - 采集 + 存储"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from data.collectors import StockCollector
from data.schemas import StockKline
from app.database.models import StockKlineDB


class StockService:
    """股票数据服务"""

    def __init__(self, db: Session):
        self.db = db
        self.collector = StockCollector()

    def get_klines(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
    ) -> list[StockKlineDB]:
        """
        从数据库获取 K 线数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量

        Returns:
            list[StockKlineDB]
        """
        query = self.db.query(StockKlineDB).filter(StockKlineDB.symbol == symbol)

        if start_date:
            query = query.filter(StockKlineDB.date >= start_date)
        if end_date:
            query = query.filter(StockKlineDB.date <= end_date)

        return query.order_by(StockKlineDB.date.desc()).limit(limit).all()

    def collect_and_save(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """
        采集并存储股票数据

        Args:
            symbol: 股票代码
            days: 采集天数
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            存储数量
        """
        # 采集数据
        klines = self.collector.collect(symbol, days, start_date, end_date)

        if not klines:
            return 0

        # 存储到数据库
        saved_count = 0
        for kline in klines:
            exists = self.db.query(StockKlineDB).filter(
                StockKlineDB.symbol == kline.symbol,
                StockKlineDB.date == kline.date,
            ).first()

            if not exists:
                db_obj = StockKlineDB(
                    symbol=kline.symbol,
                    name=kline.name,
                    date=kline.date,
                    open=kline.open,
                    high=kline.high,
                    low=kline.low,
                    close=kline.close,
                    volume=kline.volume,
                    amount=kline.amount,
                    change_pct=kline.change_pct,
                )
                self.db.add(db_obj)
                saved_count += 1

        self.db.commit()
        return saved_count

    def collect_batch_and_save(
        self,
        symbols: list[str],
        days: int = 30,
    ) -> dict[str, int]:
        """
        批量采集并存储

        Args:
            symbols: 股票代码列表
            days: 采集天数

        Returns:
            dict[symbol, count]
        """
        results = {}
        for symbol in symbols:
            try:
                count = self.collect_and_save(symbol, days=days)
                results[symbol] = count
            except Exception as e:
                print(f"采集 {symbol} 失败: {e}")
                results[symbol] = 0
        return results

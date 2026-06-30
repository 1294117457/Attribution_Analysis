"""股票数据服务 - 采集 + 存储"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from data.collectors.collector import Collector
from data.adapters.akshare import AkShareFetcher
from data.interfaces.fetcher import CollectParams
from data.schemas.kline import DailyKline
from infra.database.models import DailyKlineDB


class StockService:
    """股票数据服务（装配层：决定用哪个 Collector + Fetcher 组合）"""

    def __init__(self, db: Session):
        self.db = db
        self.collector = Collector(AkShareFetcher(DailyKline))

    def get_klines(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 365,
    ) -> list[DailyKlineDB]:
        """从数据库查询日K线"""
        query = self.db.query(DailyKlineDB).filter(DailyKlineDB.symbol == symbol)

        if start_date:
            query = query.filter(DailyKlineDB.date >= start_date)
        if end_date:
            query = query.filter(DailyKlineDB.date <= end_date)

        return query.order_by(DailyKlineDB.date.desc()).limit(limit).all()

    def collect_and_save(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> int:
        """采集并存储日K线数据"""
        params = CollectParams(
            symbol=symbol,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        klines: list[DailyKline] = self.collector.collect(params)

        if not klines:
            return 0

        saved_count = 0
        for kline in klines:
            exists = self.db.query(DailyKlineDB).filter(
                DailyKlineDB.symbol == kline.symbol,
                DailyKlineDB.date == kline.trade_date,
            ).first()

            if not exists:
                self.db.add(DailyKlineDB(
                    symbol=kline.symbol,
                    name=kline.name,
                    date=kline.trade_date,
                    open=kline.open,
                    high=kline.high,
                    low=kline.low,
                    close=kline.close,
                    volume=kline.volume,
                    amount=kline.amount,
                    change_pct=kline.change_pct,
                ))
                saved_count += 1

        self.db.commit()
        return saved_count

    def collect_batch_and_save(
        self,
        symbols: list[str],
        days: int = 30,
    ) -> dict[str, int]:
        """批量采集并存储"""
        results = {}
        for symbol in symbols:
            try:
                count = self.collect_and_save(symbol, days=days)
                results[symbol] = count
            except Exception as e:
                print(f"采集 {symbol} 失败: {e}")
                results[symbol] = 0
        return results

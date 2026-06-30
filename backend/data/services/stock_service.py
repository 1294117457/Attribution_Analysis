"""股票数据服务 - 采集 + 存储 + 管理"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from data.collectors.collector import Collector
from data.adapters.akshare import AkShareFetcher
from data.interfaces.fetcher import CollectParams
from data.schemas.kline import DailyKline
from infra.database.models import DailyKlineDB, StockInfoDB


class StockService:
    """股票数据服务（采集 + 存储 + 管理）"""

    def __init__(self, db: Session):
        self.db = db
        self.collector = Collector(AkShareFetcher(DailyKline))

    # ============ K线操作 ============

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
    ) -> tuple[int, str]:
        """采集并存储日K线数据，返回 (新增条数, 股票名称)"""
        params = CollectParams(
            symbol=symbol,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        klines: list[DailyKline] = self.collector.collect(params)

        if not klines:
            return 0, ""

        stock_name = klines[0].name if klines else ""

        # 保存/更新股票信息
        self._save_stock_info(symbol, stock_name)

        # 保存K线数据
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
        return saved_count, stock_name

    def collect_batch_and_save(
        self,
        symbols: list[str],
        days: int = 30,
    ) -> dict[str, int]:
        """批量采集并存储"""
        results = {}
        for symbol in symbols:
            try:
                count, _ = self.collect_and_save(symbol, days=days)
                results[symbol] = count
            except Exception as e:
                print(f"采集 {symbol} 失败: {e}")
                results[symbol] = 0
        return results

    def delete_stock(self, symbol: str) -> int:
        """删除股票的所有K线数据"""
        deleted = self.db.query(DailyKlineDB).filter(
            DailyKlineDB.symbol == symbol
        ).delete()
        self.db.commit()
        return deleted

    def delete_kline(self, symbol: str, del_date: date) -> int:
        """删除单条K线数据"""
        deleted = self.db.query(DailyKlineDB).filter(
            DailyKlineDB.symbol == symbol,
            DailyKlineDB.date == del_date,
        ).delete()
        self.db.commit()
        return deleted

    # ============ 股票信息管理 ============

    def _save_stock_info(self, symbol: str, name: str) -> None:
        """保存或更新股票基本信息"""
        info = self.db.query(StockInfoDB).filter(StockInfoDB.symbol == symbol).first()
        if not info:
            info = StockInfoDB(symbol=symbol, name=name)
            self.db.add(info)
        else:
            info.name = name

    def get_stock_info(self, symbol: str) -> Optional[StockInfoDB]:
        """获取股票信息"""
        return self.db.query(StockInfoDB).filter(StockInfoDB.symbol == symbol).first()

    def list_stocks(self) -> list[dict]:
        """获取所有已采集的股票列表（含统计信息）"""
        results = (
            self.db.query(
                StockInfoDB.symbol,
                StockInfoDB.name,
                StockInfoDB.industry,
                StockInfoDB.market,
                func.count(DailyKlineDB.id).label("record_count"),
                func.min(DailyKlineDB.date).label("kline_start"),
                func.max(DailyKlineDB.date).label("kline_end"),
            )
            .outerjoin(DailyKlineDB, StockInfoDB.symbol == DailyKlineDB.symbol)
            .group_by(StockInfoDB.id)
            .order_by(StockInfoDB.symbol)
            .all()
        )

        return [
            {
                "symbol": r.symbol,
                "name": r.name,
                "industry": r.industry,
                "market": r.market,
                "record_count": r.record_count,
                "kline_start": r.kline_start,
                "kline_end": r.kline_end,
            }
            for r in results
        ]

    def update_stock_info(
        self,
        symbol: str,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> Optional[StockInfoDB]:
        """更新股票信息"""
        info = self.db.query(StockInfoDB).filter(StockInfoDB.symbol == symbol).first()
        if not info:
            info = StockInfoDB(symbol=symbol)
            self.db.add(info)

        if name is not None:
            info.name = name
        if industry is not None:
            info.industry = industry
        if market is not None:
            info.market = market

        self.db.commit()
        return info

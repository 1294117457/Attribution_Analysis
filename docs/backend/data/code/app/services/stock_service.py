"""股票服务"""

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from datetime import date, timedelta
from typing import Optional

from app.models.stock import StockKlineDB
from data.schemas import (
    StockKlineResponse,
    StockKline,
    CollectResponse,
)
from data.akshare_client import AkShareClient


class StockService:
    """股票服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_stock(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[StockKlineResponse]:
        """获取股票数据"""
        query = self.db.query(StockKlineDB).filter(StockKlineDB.symbol == symbol)

        if start_date:
            query = query.filter(StockKlineDB.date >= start_date)
        if end_date:
            query = query.filter(StockKlineDB.date <= end_date)

        query = query.order_by(StockKlineDB.date.desc())

        return [StockKlineResponse.model_validate(r) for r in query.all()]

    def list_stocks(self, limit: int = 100) -> list[StockKlineResponse]:
        """获取股票列表"""
        query = (
            self.db.query(StockKlineDB)
            .distinct(StockKlineDB.symbol)
            .order_by(StockKlineDB.symbol)
            .limit(limit)
        )
        return [StockKlineResponse.model_validate(r) for r in query.all()]

    def collect_stock(self, symbol: str, days: int = 365) -> CollectResponse:
        """采集股票数据"""
        client = AkShareClient()

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        try:
            # 获取数据
            klines = client.get_stock_kline(symbol, start_date, end_date)

            if not klines:
                return CollectResponse(
                    status="failed",
                    symbol=symbol,
                    count=0,
                    message="未获取到数据",
                )

            # 存储数据
            count = 0
            for kline in klines:
                self._upsert_kline(kline)
                count += 1

            self.db.commit()

            return CollectResponse(
                status="success",
                symbol=symbol,
                count=count,
                message=f"成功采集 {count} 条数据",
            )

        except Exception as e:
            self.db.rollback()
            return CollectResponse(
                status="failed",
                symbol=symbol,
                count=0,
                message=f"采集失败: {str(e)}",
            )

    def _upsert_kline(self, kline: StockKline) -> None:
        """Upsert K 线数据"""
        stmt = insert(StockKlineDB).values(
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

        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                "name": stmt.excluded.name,
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "amount": stmt.excluded.amount,
                "change_pct": stmt.excluded.change_pct,
            },
        )

        self.db.execute(stmt)

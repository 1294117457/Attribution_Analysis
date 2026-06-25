"""K线数据服务"""

from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session

from app.models.kline import KLine
from app.schemas.kline import KLineResponse


class KLineService:
    """K线数据服务"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_code_and_date(
        self, symbol: str, trade_date: date
    ) -> Optional[KLine]:
        """根据股票代码和日期获取K线"""
        return (
            self.db.query(KLine)
            .filter(
                KLine.code == symbol,
                KLine.date == trade_date,
            )
            .first()
        )

    def get_by_date_range(
        self, symbol: str, start_date: date, end_date: date
    ) -> List[KLine]:
        """根据日期范围获取K线"""
        return (
            self.db.query(KLine)
            .filter(
                KLine.code == symbol,
                KLine.date >= start_date,
                KLine.date <= end_date,
            )
            .order_by(KLine.date)
            .all()
        )

    def get_latest(self, symbol: str, limit: int = 100) -> List[KLine]:
        """获取最近N条K线"""
        return (
            self.db.query(KLine)
            .filter(KLine.code == symbol)
            .order_by(KLine.date.desc())
            .limit(limit)
            .all()
        )

    def to_response(self, kline: KLine) -> KLineResponse:
        """转换为响应模型"""
        return KLineResponse(
            code=kline.code,
            name=kline.name,
            date=kline.date,
            open=kline.open,
            high=kline.high,
            low=kline.low,
            close=kline.close,
            volume=kline.volume,
            amount=kline.amount,
            change_pct=kline.change_pct,
            turnover_rate=kline.turnover_rate,
        )

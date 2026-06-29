"""异常服务"""

from sqlalchemy import Column, String, Float, Integer, Date, Index
from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.models.mixins import TimestampMixin
from app.schemas.anomaly import AnomalyCreate, AnomalyResponse


class AnomalyDB(Base, TimestampMixin):
    """异常数据 ORM 模型"""

    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False)
    type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)

    __table_args__ = (Index("idx_symbol_date", "symbol", "date"),)


class AnomalyService:
    """异常服务"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: AnomalyCreate) -> AnomalyResponse:
        """创建异常记录"""
        db_obj = AnomalyDB(**data.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return AnomalyResponse.model_validate(db_obj)

    def list_by_symbol(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AnomalyResponse]:
        """查询股票的异常记录"""
        query = self.db.query(AnomalyDB).filter(AnomalyDB.symbol == symbol)

        if start_date:
            query = query.filter(AnomalyDB.date >= start_date)
        if end_date:
            query = query.filter(AnomalyDB.date <= end_date)

        return [AnomalyResponse.model_validate(r) for r in query.all()]

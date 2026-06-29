from sqlalchemy.orm import Session
from typing import list
from app.database.models.anomaly_db import AnomalyDB
from app.models.anomaly import AnomalyCreate, AnomalyResponse
from core.models.anomaly import AnomalyRecord

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

    def to_record(self, response: AnomalyResponse) -> AnomalyRecord:
        """转换为核心领域模型"""
        return AnomalyRecord(
            id=str(response.id),
            symbol=response.symbol,
            date=response.date,
            type=response.type,
            value=response.value,
            threshold=response.threshold,
            score=response.score,
            description=response.description,
        )
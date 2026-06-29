from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.anomaly_service import AnomalyService
from app.services.stock_service import StockService

def get_anomaly_service(db: Session = Depends(get_db)) -> AnomalyService:
    return AnomalyService(db)

def get_stock_service(db: Session = Depends(get_db)) -> StockService:
    return StockService(db)
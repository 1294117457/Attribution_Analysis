from fastapi import APIRouter
from app.api import health, stocks, anomalies, analysis

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(stocks.router)
api_router.include_router(anomalies.router)
api_router.include_router(analysis.router)
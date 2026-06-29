from pydantic import BaseModel, Field
from datetime import date
from core.types import AnomalyType

class AnomalyCreate(BaseModel):
    """创建异常请求"""
    symbol: str
    date: date
    type: AnomalyType
    value: float
    threshold: float
    score: float = Field(..., ge=0, le=1)
    description: str | None = None

class AnomalyResponse(BaseModel):
    """异常响应"""
    id: int
    symbol: str
    date: date
    type: AnomalyType
    value: float
    threshold: float
    score: float
    description: str | None

    class Config:
        from_attributes = True  # 支持从 ORM 模型转换

class AnomalyListResponse(BaseModel):
    """异常列表响应"""
    total: int
    items: list[AnomalyResponse]
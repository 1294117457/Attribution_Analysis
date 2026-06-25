"""分析服务 Schema"""

from typing import Optional, List, Literal
from datetime import date
from pydantic import BaseModel, Field, ConfigDict


class AnomalyResult(BaseModel):
    """异常检测结果"""

    type: str = Field(..., description="异常类型")
    severity: Literal["low", "medium", "high"] = Field(..., description="严重程度")
    value: float = Field(..., description="异常值")
    description: str = Field(..., description="异常描述")
    date: Optional[str] = Field(None, description="发生日期")


class AnalyzeRequest(BaseModel):
    """分析请求"""

    symbol: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="股票代码",
        examples=["600519", "000858"],
    )
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    analysis_type: Literal["anomaly", "attribution", "full"] = Field(
        "full",
        description="分析类型：anomaly=仅异常检测, attribution=仅归因分析, full=完整分析",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "600519",
                "start_date": "2026-01-01",
                "end_date": "2026-06-25",
                "analysis_type": "full",
            }
        }
    )


class AnalyzeResponse(BaseModel):
    """分析响应"""

    symbol: str = Field(..., description="股票代码")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    is_anomaly: bool = Field(..., description="是否检测到异常")
    anomalies: List[AnomalyResult] = Field(default_factory=list, description="异常列表")
    report: Optional[str] = Field(None, description="分析报告(Markdown)")
    confidence: Optional[float] = Field(None, description="置信度(0-1)")

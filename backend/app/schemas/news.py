"""新闻数据 Schema"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class NewsResponse(BaseModel):
    """新闻响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="新闻ID")
    code: Optional[str] = Field(None, description="股票代码")
    title: str = Field(..., description="新闻标题")
    content: Optional[str] = Field(None, description="新闻内容摘要")
    url: Optional[str] = Field(None, description="原文链接")
    source: Optional[str] = Field(None, description="新闻来源")
    publish_time: Optional[datetime] = Field(None, description="发布时间")
    created_at: datetime = Field(..., description="创建时间")


class NewsQueryRequest(BaseModel):
    """新闻查询请求"""

    symbol: Optional[str] = Field(None, min_length=6, max_length=6, description="股票代码")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    limit: int = Field(100, ge=1, le=1000, description="返回条数")


class NewsListResponse(BaseModel):
    """新闻列表响应"""

    total: int = Field(..., description="总条数")
    data: List[NewsResponse] = Field(..., description="新闻列表")

"""表元信息响应 DTO"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TableInfoDTO(BaseModel):
    """表元信息（list_tables 接口用）"""

    name: str = Field(..., description="表名")
    row_count: int = Field(..., description="估算行数")
    size_mb: float = Field(..., description="占用空间（MB）")
    category: Literal["system", "market", "financial", "concept", "business"] = Field(
        "business", description="分类"
    )
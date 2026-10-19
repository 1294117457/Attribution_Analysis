"""采集 trigger 请求 DTO（POST 触发）

Phase3 后：覆盖原 CollectJobSaveRequest，统一用业务语义命名。
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class CollectRequest(BaseModel):
    """POST /api/collect/{facet}/{service_name} 请求体

    仅传 params，service 内部根据 META.kind 决定执行策略：
      - kind=full_refresh → 全量覆盖（DELETE + INSERT）
      - kind=incremental → 增量采集（按 start_date / end_date / trade_date）
      - kind=realtime    → 不走此接口（走 /query）
    """
    params: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def _strip_empty(self) -> "CollectRequest":
        """过滤空字符串/空数组/None，避免「symbols 必填」误报"""
        cleaned = {k: v for k, v in self.params.items()
                   if v not in (None, "", [], {})}
        self.params = cleaned
        return self


__all__ = ["CollectRequest"]

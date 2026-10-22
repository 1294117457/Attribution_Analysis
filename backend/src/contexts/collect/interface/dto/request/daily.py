"""日 K 线采集请求 DTO（POST /collect/tech/daily_kline）

为什么单独一份 DTO（而不是通用 CollectRequest.params: dict）：
    - DailyService v5 的入参契约已经收敛成「只有时间范围」：
      start_date / end_date 必填，symbol 固定取自 stock_basic，不接受前端指定
    - 用强类型模型把契约前移到 HTTP 层：
      缺字段 / 日期格式错 → FastAPI 直接 422（不再让 service 抛 InvalidParams）
      start > end         → 同样 422，语义更直观
    - 未知字段（前端多传的 symbols 等）被 pydantic 默认忽略，
      最终只把 start_date / end_date 交给 service

请求体形状（与前端 collect-manage 保持一致，仍是 params 包裹）：
    {
      "params": {
        "start_date": "2026-01-01",
        "end_date":   "2026-10-21"
      }
    }

★ 时间跨度上限（1095 天）属于业务规则，仍由 DailyService._validate_params
  校验（不通过 → HTTP 400）。DTO 只负责「字段形状 + 顺序」这类传输层约束，
  避免同一个魔法数字在两层各写一份。
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class DailyRangeParams(BaseModel):
    """日 K 线采集的时间范围参数"""

    start_date: date = Field(
        ...,
        description="起始日期（含），格式 YYYY-MM-DD",
        examples=["2026-01-01"],
    )
    end_date: date = Field(
        ...,
        description="结束日期（含），格式 YYYY-MM-DD",
        examples=["2026-10-21"],
    )

    @model_validator(mode="after")
    def _check_order(self) -> "DailyRangeParams":
        """start_date 不能晚于 end_date"""
        if self.start_date > self.end_date:
            raise ValueError(
                f"start_date（{self.start_date}）不能晚于 end_date（{self.end_date}）"
            )
        return self


class DailyCollectRequest(BaseModel):
    """POST /collect/tech/daily_kline 请求体"""

    params: DailyRangeParams = Field(
        ...,
        description="采集参数：仅时间范围，symbol 由后端从 stock_basic 读取",
    )

    def to_service_params(self) -> dict:
        """转成 service 期望的 params dict（ISO 字符串，service 会写进 JSONB）"""
        return {
            "start_date": self.params.start_date.isoformat(),
            "end_date": self.params.end_date.isoformat(),
        }


__all__ = ["DailyCollectRequest", "DailyRangeParams"]

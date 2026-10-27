from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from shared.interface.validators import TradeDate


class DailyCollectRequest(BaseModel):
    """日 K 线采集请求体（按时间范围采全市场）"""

    start_date: TradeDate = Field(..., description="起始日期（含）")
    end_date: TradeDate = Field(..., description="结束日期（含）")

    @model_validator(mode="after")
    def _check_range(self) -> "DailyCollectRequest":
        """区间不可倒挂"""
        if self.start_date > self.end_date:
            raise ValueError(
                f"start_date（{self.start_date}）"
                f"不能晚于 end_date（{self.end_date}）"
            )
        return self


__all__ = ["DailyCollectRequest"]

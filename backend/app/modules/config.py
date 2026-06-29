"""
模块配置。
"""

from pydantic import BaseModel
from typing import Optional


class CollectorConfig(BaseModel):
    """采集模块配置"""
    batch_size: int = 50
    request_delay: float = 1.0
    retry_times: int = 3
    lookback_years: int = 5


class DetectorConfig(BaseModel):
    """检测模块配置"""

    # Z-Score 配置（价格异常）
    zscore_threshold: float = 2.5
    zscore_lookback_days: int = 30
    zscore_weight: float = 0.30

    # IQR 配置（量能异常）
    iqr_k: float = 1.5
    iqr_lookback_days: int = 30
    iqr_weight: float = 0.25

    # 波动配置
    volatility_percentile_high: float = 95.0
    volatility_percentile_low: float = 5.0
    volatility_lookback_days: int = 30
    volatility_weight: float = 0.20

    # 趋势配置
    ma_periods: list[int] = [5, 20, 60]
    boll_period: int = 20
    boll_std: float = 2.0
    trend_weight: float = 0.25

    # 异常等级阈值
    severity_critical: float = 0.90
    severity_high: float = 0.70
    severity_medium: float = 0.40
    severity_low: float = 0.0


# 全局配置实例
collector_config = CollectorConfig()
detector_config = DetectorConfig()

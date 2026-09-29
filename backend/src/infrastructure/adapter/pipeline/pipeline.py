"""Pipeline 编排调度框架（L2）

核心概念：
  - Pipeline    一个采集任务/工作流的完整定义（声明式配置）
  - APIStep     Pipeline 里的一个原子步骤 = "调一次数据源 API"
  - UnitSpec    单元定义（per_unit / one_shot / streaming）
  - ScheduleSpec "何时跑"（cron / interval / manual）
  - RateLimitConfig / RetryConfig 限速和重试参数

P0 设计要点（用户确认）：
  - args_template 仅支持 {{var}} 和 {{var.attr}}，**无 filter**
  - 默认值（如 days=7）在 UnitResolver 阶段填，模板只做替换
  - Pipeline 配置形式用 Python dataclass（类型安全 + IDE 跳转）
  - 群组用 Pipeline.tags 实现（零成本）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════════════════
# APIStep
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class APIStep:
    """Pipeline 中的一个原子步骤

    调用一次数据源 API。

    Args:
        name: 步骤名（pipeline 内唯一，用于 depends_on 引用）
        source: 数据源名（"Tushare" / "Adata-THS" / "Pytdx"）
        method: 数据源方法名（"fetch_kline" / "fetch_daily_basic" / ...）
        args_template: 调用参数模板（dict），仅支持 {{var}} 和 {{var.attr}}
        save_to: 可选，落表名（暂未实现，保留扩展）
        depends_on: 上游步骤名（用于工作流依赖）
        skip_if: 可选，Jinja 条件表达式（暂不实现，保留扩展）
        on_error: "fail" / "continue" / "retry"（P0 阶段仅支持 fail）
    """

    name: str
    source: str
    method: str
    args_template: dict[str, Any] = field(default_factory=dict)
    save_to: str | None = None
    depends_on: tuple[str, ...] = ()
    on_error: str = "fail"


# ═══════════════════════════════════════════════════════════════════════
# UnitSpec
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class UnitSpec:
    """单元定义：决定一次 pipeline 跑多少个 unit

    3 种风格：
    - one_shot:    steps 整体只跑 1 次（unit 数=1）
    - per_unit:    拉一组 unit（如所有 symbol / 所有日期 / 所有概念），对每个 unit 跑 1 次 steps
    - streaming:   不分 unit，steps 内部自行迭代（适合 adata.concept_list 等一次拿全）
    """

    style: str = "one_shot"          # per_unit | one_shot | streaming
    # per_unit 风格专用
    unit_source: str = ""            # "stock_infos" / "trading_dates" / "concepts"
    unit_filter: dict[str, Any] = field(default_factory=dict)
    unit_template: dict[str, str] = field(default_factory=dict)
    # ↑ 单元数据模板，如 {"label": "{{symbol}}", "symbol": "{{symbol}}"}
    # ↓ unit-level 默认参数（如 days 不传时填 7）
    default_unit_args: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# ScheduleSpec
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ScheduleSpec:
    """调度配置

    Args:
        kind: "cron" / "interval" / "manual"（None）
        cron: cron 表达式（如 "0 17 * * 1-5"）
        interval_seconds: 间隔秒数（kind=interval 用）
        enabled_by_default: 默认是否启用
        trading_day_only: 是否仅交易日执行
        description: 调度说明
    """

    kind: str = "manual"             # cron | interval | manual
    cron: str = ""
    interval_seconds: int = 0
    enabled_by_default: bool = True
    trading_day_only: bool = False
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════
# RateLimitConfig / RetryConfig
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class RateLimitConfig:
    """限速配置

    - per_request_delay: 每次请求后 sleep 秒数
    - per_chunk_delay: 每个 chunk（symbol 组）后 sleep 秒数
    - chunk_size: 并发池 chunk 大小
    - concurrency: 最大并发数
    """

    per_request_delay: float = 0.0
    per_chunk_delay: float = 0.0
    chunk_size: int = 100
    concurrency: int = 1


@dataclass(frozen=True)
class RetryConfig:
    """重试配置

    - max_retries: 最大重试次数
    - retry_delay: 重试间隔秒数
    - retry_on: 触发重试的 error_type 元组
    """

    max_retries: int = 0
    retry_delay: float = 1.0
    retry_on: tuple[str, ...] = ("rate_limited", "network")


# ═══════════════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Pipeline:
    """采集编排 Pipeline（声明式配置）

    一个 pipeline = 1 个采集任务或 1 个工作流。
    多 step 时按顺序执行，形成"多 API 工作流"。

    Args:
        pipeline_id: 全局唯一 ID（如 "daily_kline" / "after_market_sync"）
        name: UI 显示名
        description: 描述
        facet: facet 名（如 "tech" / "fundamental" / "concept"）
        sub_facet: sub_facet 名（如 "kline" / "valuation" / "member"）
        unit: 单元定义
        steps: 步骤序列
        schedule: 调度（None = 仅手动触发）
        rate_limit: 限速
        retry: 重试
        timeout_sec: 单次 pipeline 总超时（秒）
        enabled: 是否启用
        tags: 群组标签（如 ("Tushare", "全市场", "盘后")）
    """

    pipeline_id: str
    name: str
    description: str = ""

    facet: str = ""
    sub_facet: str = ""

    unit: UnitSpec = field(default_factory=UnitSpec)
    steps: tuple[APIStep, ...] = ()

    schedule: ScheduleSpec | None = None
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    timeout_sec: int = 7200

    enabled: bool = True
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.pipeline_id:
            raise ValueError("pipeline_id 不能为空")
        if not self.steps:
            raise ValueError(f"pipeline {self.pipeline_id!r} 必须至少有 1 个 step")
        # step 名唯一性
        names = [s.name for s in self.steps]
        if len(names) != len(set(names)):
            raise ValueError(f"pipeline {self.pipeline_id!r} 的 step 名重复: {names}")
        # depends_on 引用必须存在
        for s in self.steps:
            for dep in s.depends_on:
                if dep not in names:
                    raise ValueError(
                        f"pipeline {self.pipeline_id!r} step {s.name!r} 引用了不存在的上游 {dep!r}"
                    )


__all__ = [
    "APIStep",
    "UnitSpec",
    "ScheduleSpec",
    "RateLimitConfig",
    "RetryConfig",
    "Pipeline",
]

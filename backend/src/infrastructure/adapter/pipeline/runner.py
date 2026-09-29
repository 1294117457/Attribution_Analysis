"""Pipeline 执行器（PipelineRunner）

执行一个 Pipeline 的核心，不依赖具体的 fetcher / task 类，只依赖 DataSourceAPI 和模板渲染。

执行流程：
  1. resolve_units() → 生成 unit 列表
  2. 对每个 unit：
     a. 渲染所有 step 的 args_template（仅 {{var}} 替换）
     b. 按顺序执行 step
     c. 每个 step 调 source.method(**args)（按 method 名字符串 dispatch）
     d. 检查 CallResult.ok；False → 单元失败
     e. on_unit_done 上报
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from application.port.data_source_api import CallResult, DataSourceAPI
from infrastructure.adapter.data_source.registry import DataSourceRegistry
from infrastructure.adapter.pipeline.pipeline import Pipeline
from infrastructure.adapter.pipeline.template import render
from infrastructure.adapter.pipeline.unit_resolver import UnitResolver

logger = logging.getLogger(__name__)


@dataclass
class UnitResult:
    """单元执行结果"""

    success: bool
    detail: str = ""
    error: str | None = None
    step_results: list[CallResult] = field(default_factory=list)


@dataclass
class TaskSummary:
    """整个 pipeline 的执行汇总"""

    success: int = 0
    fail: int = 0
    total: int = 0
    elapsed_ms: int = 0
    cancelled: bool = False


# 单元进度回调签名
OnUnitDone = Callable[[UnitResult], Awaitable[None]]


class PipelineRunner:
    """执行一个 Pipeline 的核心"""

    def __init__(
        self,
        registry: DataSourceRegistry,
        pipeline: Pipeline,
        task_id: int | None = None,
    ) -> None:
        self._registry = registry
        self._pipeline = pipeline
        self._task_id = task_id
        self._resolver = UnitResolver()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def run(
        self,
        params: dict | None = None,
        on_unit_done: OnUnitDone | None = None,
    ) -> TaskSummary:
        """执行 pipeline

        Args:
            params: 外部传入的运行时参数
            on_unit_done: 单元完成回调（用于上报进度）
        """
        params = params or {}
        on_unit_done = on_unit_done or _noop_on_done
        sem = asyncio.Semaphore(self._pipeline.rate_limit.concurrency)

        summary = TaskSummary()
        t0 = time.time()

        units = []
        async for unit in self._resolver.resolve(self._pipeline.unit, params):
            units.append(unit)

        summary.total = len(units)
        logger.info(
            "[%s] 启动 pipeline: units=%d, steps=%d",
            self._pipeline.pipeline_id,
            summary.total,
            len(self._pipeline.steps),
        )

        for unit in units:
            if self._cancelled:
                summary.cancelled = True
                break
            async with sem:
                unit_result = await self._run_unit(unit, params)
                if unit_result.success:
                    summary.success += 1
                else:
                    summary.fail += 1
                await on_unit_done(unit_result)
            # 限速
            if self._pipeline.rate_limit.per_request_delay > 0:
                await asyncio.sleep(self._pipeline.rate_limit.per_request_delay)

        summary.elapsed_ms = int((time.time() - t0) * 1000)
        logger.info(
            "[%s] pipeline 完成: success=%d fail=%d total=%d elapsed=%dms",
            self._pipeline.pipeline_id,
            summary.success,
            summary.fail,
            summary.total,
            summary.elapsed_ms,
        )
        return summary

    async def _run_unit(self, unit: dict, params: dict) -> UnitResult:
        """执行 1 个 unit 的所有 step"""
        step_results: list[CallResult] = []
        ctx = {**unit, **params, "params": params}  # params.days 用

        for step in self._pipeline.steps:
            # 渲染 args 模板（仅替换 {{var}}）
            try:
                args = render(step.args_template, ctx)
            except Exception as e:
                return UnitResult(
                    success=False,
                    detail=str(unit.get("label", "")),
                    error=f"step {step.name!r} 模板渲染失败: {e}",
                    step_results=step_results,
                )

            # 取数据源实例
            try:
                source = self._registry.get(step.source)
            except KeyError as e:
                return UnitResult(
                    success=False,
                    detail=str(unit.get("label", "")),
                    error=f"step {step.name!r} 数据源 {step.source!r} 未注册: {e}",
                    step_results=step_results,
                )

            # 取方法（按 method 名字符串 dispatch）
            method = getattr(source, step.method, None)
            if method is None:
                return UnitResult(
                    success=False,
                    detail=str(unit.get("label", "")),
                    error=f"step {step.name!r} 数据源 {step.source!r} 不支持方法 {step.method!r}",
                    step_results=step_results,
                )

            # 类型自动转换：模板渲染后 str 化，按方法签名还原成 int/float/bool
            try:
                args = _coerce_args(method, args)
            except Exception as e:
                return UnitResult(
                    success=False,
                    detail=str(unit.get("label", "")),
                    error=f"step {step.name!r} 参数类型转换失败: {e}",
                    step_results=step_results,
                )

            # 调用
            try:
                result: CallResult = await method(**args)
            except Exception as e:
                return UnitResult(
                    success=False,
                    detail=str(unit.get("label", "")),
                    error=f"step {step.name!r} 调用异常: {e}",
                    step_results=step_results,
                )

            step_results.append(result)
            if not result.ok:
                # P0 阶段仅支持 fail：单步失败整个 unit 失败
                return UnitResult(
                    success=False,
                    detail=str(unit.get("label", "")),
                    error=f"step {step.name!r} 失败: {result.error}",
                    step_results=step_results,
                )

        return UnitResult(
            success=True,
            detail=str(unit.get("label", "")),
            step_results=step_results,
        )


async def _noop_on_done(result: UnitResult) -> None:
    """默认 on_unit_done（不做任何事）"""


# ═══════════════════════════════════════════════════════════════════════
# 类型自动转换
# ═══════════════════════════════════════════════════════════════════════


_BASIC_TYPE_COERCERS = {
    int: lambda v: int(v) if v != "" else 0,
    float: lambda v: float(v) if v != "" else 0.0,
    bool: lambda v: v.lower() in ("true", "1", "yes") if isinstance(v, str) else bool(v),
}


def _coerce_args(method, args: dict) -> dict:
    """根据方法签名把 args 中的 str 值转换为目标类型

    模板渲染后所有值都是 str，需要还原成方法签名期望的类型（int / float / bool）。
    """
    import inspect
    try:
        sig = inspect.signature(method)
    except (ValueError, TypeError):
        return args

    coerced = {}
    for arg_name, arg_val in args.items():
        if arg_name not in sig.parameters:
            coerced[arg_name] = arg_val
            continue

        param = sig.parameters[arg_name]
        target_type = param.annotation

        # 没标注类型或类型不是基本类型 → 原样返回
        if target_type is inspect.Parameter.empty or target_type not in _BASIC_TYPE_COERCERS:
            coerced[arg_name] = arg_val
            continue

        # 是 str 且需要转换
        if isinstance(arg_val, str) and arg_val != "":
            try:
                coerced[arg_name] = _BASIC_TYPE_COERCERS[target_type](arg_val)
            except (ValueError, TypeError):
                coerced[arg_name] = arg_val  # 转换失败时原样保留
        else:
            coerced[arg_name] = arg_val

    return coerced


__all__ = ["PipelineRunner", "UnitResult", "TaskSummary", "OnUnitDone"]

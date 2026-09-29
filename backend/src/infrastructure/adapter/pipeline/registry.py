"""Pipeline 注册中心（L2）

管理「pipeline_id → Pipeline 配置」的映射。

支持：
  - 注册/查询 pipeline
  - 按 facet / tag / source 筛选
  - 启动期校验（pipeline.method 必须在 source.available_methods 中）

加新采集任务 = 注册 1 个 Pipeline 配置（不动代码）。
"""

from __future__ import annotations

import logging
import threading
from typing import Iterable

from infrastructure.adapter.data_source.registry import DataSourceRegistry
from infrastructure.adapter.pipeline.pipeline import Pipeline

logger = logging.getLogger(__name__)


class PipelineRegistry:
    """Pipeline 注册中心"""

    def __init__(self, data_source_registry: DataSourceRegistry | None = None) -> None:
        self._pipelines: dict[str, Pipeline] = {}
        self._data_source_registry = data_source_registry
        self._lock = threading.Lock()

    def set_data_source_registry(self, registry: DataSourceRegistry) -> None:
        self._data_source_registry = registry

    # ── 注册 ──

    def register(self, pipeline: Pipeline) -> None:
        """注册一个 pipeline 配置"""
        with self._lock:
            self._pipelines[pipeline.pipeline_id] = pipeline
        logger.info(
            "注册 pipeline: %s (facet=%s/%s, steps=%d, tags=%s)",
            pipeline.pipeline_id,
            pipeline.facet,
            pipeline.sub_facet,
            len(pipeline.steps),
            pipeline.tags,
        )

    def register_all(self, pipelines: Iterable[Pipeline]) -> None:
        for p in pipelines:
            self.register(p)

    # ── 查询 ──

    def get(self, pipeline_id: str) -> Pipeline:
        if pipeline_id not in self._pipelines:
            raise KeyError(f"未注册 pipeline {pipeline_id!r}")
        return self._pipelines[pipeline_id]

    def has(self, pipeline_id: str) -> bool:
        return pipeline_id in self._pipelines

    def list(self) -> list[Pipeline]:
        return list(self._pipelines.values())

    def list_ids(self) -> list[str]:
        return list(self._pipelines.keys())

    def list_by_facet(self, facet: str, sub_facet: str | None = None) -> list[Pipeline]:
        results = [p for p in self._pipelines.values() if p.facet == facet]
        if sub_facet is not None:
            results = [p for p in results if p.sub_facet == sub_facet]
        return results

    def list_by_tag(self, tag: str) -> list[Pipeline]:
        return [p for p in self._pipelines.values() if tag in p.tags]

    def list_by_source(self, source: str) -> list[Pipeline]:
        """列出所有 step 引用了某数据源的 pipeline"""
        return [
            p for p in self._pipelines.values()
            if any(s.source == source for s in p.steps)
        ]

    def list_scheduled(self) -> list[Pipeline]:
        """列出有 schedule 配置的 pipeline"""
        return [p for p in self._pipelines.values() if p.schedule is not None]

    # ── 校验 ──

    def validate(self) -> list[str]:
        """校验所有 pipeline 的 step.method 是否在 source.available_methods 中

        Returns:
            错误消息列表（空 = 全部合法）
        """
        errors: list[str] = []
        if self._data_source_registry is None:
            return errors

        for p in self._pipelines.values():
            for step in p.steps:
                if not self._data_source_registry.has(step.source):
                    errors.append(
                        f"pipeline {p.pipeline_id!r} step {step.name!r}: "
                        f"数据源 {step.source!r} 未注册"
                    )
                    continue
                if not self._data_source_registry.validate_method(step.source, step.method):
                    errors.append(
                        f"pipeline {p.pipeline_id!r} step {step.name!r}: "
                        f"数据源 {step.source!r} 不支持方法 {step.method!r}"
                    )
        return errors

    def __repr__(self) -> str:
        return f"PipelineRegistry(count={len(self._pipelines)})"


# ═══════════════════════════════════════════════════════════════════════
# 全局注册中心（模块单例）
# ═══════════════════════════════════════════════════════════════════════

_registry: PipelineRegistry | None = None


def get_pipeline_registry() -> PipelineRegistry:
    """获取全局 pipeline 注册中心（延迟初始化）"""
    global _registry
    if _registry is None:
        from infrastructure.adapter.data_source.registry import get_data_source_registry
        _registry = PipelineRegistry(data_source_registry=get_data_source_registry())
    return _registry


__all__ = ["PipelineRegistry", "get_pipeline_registry"]

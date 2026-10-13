"""DataGateway：统一入口（门面）+ 选源（策略 / 责任链）

- 指定 source：只用这一个实现（策略），不换源
- 不指定：按 priority 逐个尝试（责任链），只有 RateLimited / SourceUnavailable 换源
- 全部实现 supports()=False → NotSupported；至少试过一个且都失败 → SourceUnavailable
- policy=QUERY 且 Port 声明了 cache → 先过 CacheDecorator
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from application.port.data.base import (
    AdapterInfo,
    CallPolicy,
    DataCommand,
    DataPort,
    DataResult,
    InvalidParams,
    NotSupported,
    PortInfo,
    RateLimited,
    SourceUnavailable,
)
from domain.service.market_session import market_now
from infrastructure.adapter.data.core.base import ORIGIN_LABELS
from infrastructure.adapter.data.core.cache import CacheDecorator
from infrastructure.adapter.data.core.context import call_policy
from infrastructure.adapter.data.core.decorators import read_stats
from infrastructure.adapter.data.core.registry import DataPortRegistry


class DataGateway:
    def __init__(self, registry: DataPortRegistry, cache: Optional[CacheDecorator] = None) -> None:
        self._registry = registry
        self._cache = cache or CacheDecorator()

    # ── 类型化调用 ────────────────────────────────────────────

    async def fetch(
        self,
        port: type[DataPort],
        params: BaseModel | dict,
        *,
        source: Optional[str] = None,
        policy: CallPolicy = CallPolicy.COLLECT,
    ) -> DataResult:
        p = self._validate(port, params)
        token = call_policy.set(policy)
        started = time.perf_counter()
        try:
            if policy is CallPolicy.QUERY and port.cache is not None:
                result = await self._cache.get_or_load(port, p, lambda: self._select(port, p, source))
            else:
                result = await self._select(port, p, source)
        finally:
            call_policy.reset(token)
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        return result

    async def fetch_many(
        self,
        port: type[DataPort],
        params_list: list[BaseModel | dict],
        *,
        policy: CallPolicy = CallPolicy.COLLECT,
    ) -> list[DataResult | Exception]:
        async def one(p: BaseModel | dict) -> DataResult | Exception:
            try:
                return await self.fetch(port, p, policy=policy)
            except Exception as e:
                return e

        return list(await asyncio.gather(*(one(p) for p in params_list)))

    # ── 按名调用 ──────────────────────────────────────────────

    async def invoke(self, cmd: DataCommand) -> DataResult:
        port = self._registry.port(cmd.name)
        return await self.fetch(port, cmd.params, source=cmd.source, policy=cmd.policy)

    async def invoke_many(self, cmds: list[DataCommand]) -> list[DataResult | Exception]:
        async def one(c: DataCommand) -> DataResult | Exception:
            try:
                return await self.invoke(c)
            except Exception as e:
                return e

        return list(await asyncio.gather(*(one(c) for c in cmds)))

    # ── 目录 / 统计 ───────────────────────────────────────────

    def catalog(self) -> list[PortInfo]:
        out: list[PortInfo] = []
        for port in self._registry.ports():
            adapters = tuple(
                AdapterInfo(
                    tool=a.tool,
                    origin=a.origin,
                    origin_label=ORIGIN_LABELS.get(a.origin, a.origin),
                    priority=a.priority,
                )
                for a in self._registry.raw_adapters(port)
            )
            out.append(PortInfo(
                name=port.name,
                label=port.label,
                facet=port.facet,
                sub_facet=port.sub_facet,
                description=port.description,
                unit=port.unit,
                realtime=port.cache is not None,
                sort_order=port.sort_order,
                sample_params=dict(port.sample_params),
                params_schema=port.Params.model_json_schema(),
                item_schema=port.Item.model_json_schema(),
                adapters=adapters,
                ttl_trading=port.cache.ttl_trading if port.cache else None,
                consumers=tuple(port.cache.consumers) if port.cache else (),
            ))
        return out

    def is_realtime(self, name: str) -> bool:
        port = self._registry.find_port(name)
        return port is not None and port.cache is not None

    async def stats(self, name: str, days: int = 1) -> list[dict]:
        port = self._registry.port(name)
        tools = [a.tool for a in self._registry.raw_adapters(port)]
        return await read_stats(port.name, tools, days, with_cache=port.cache is not None)

    # ── 内部 ──────────────────────────────────────────────────

    @staticmethod
    def _validate(port: type[DataPort], params: Any) -> BaseModel:
        if isinstance(params, port.Params):
            return params
        if isinstance(params, BaseModel):
            params = params.model_dump()
        try:
            return port.Params.model_validate(params or {})
        except ValidationError as e:
            raise InvalidParams(_validation_message(port, e)) from e

    async def _select(self, port: type[DataPort], p: BaseModel, source: Optional[str]) -> DataResult:
        candidates = [a for a in self._registry.adapters(port) if source in (None, a.tool)]
        if not candidates:
            raise NotSupported(f"{port.name} 没有可用实现{f' {source}' if source else ''}")
        attempts: list[tuple[str, str]] = []
        for adapter in candidates:
            if not adapter.supports(p):
                continue
            try:
                items = await adapter.fetch(p)
            except InvalidParams:
                raise
            except (RateLimited, SourceUnavailable) as e:
                attempts.append((adapter.tool, repr(e)))
                if len(candidates) == 1:
                    e.attempts = attempts
                    raise
                continue
            return DataResult(items=items, source=adapter.tool, fetched_at=market_now(), attempts=attempts)
        if not attempts:
            raise NotSupported(f"{port.name} 没有支持该参数的实现")
        err = SourceUnavailable(f"{port.name} 全部数据源失败: {attempts}")
        err.attempts = attempts
        raise err


def _validation_message(port: type[DataPort], e: ValidationError) -> str:
    parts = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err.get("loc", ())) or "params"
        parts.append(f"{loc}: {err.get('msg')}")
    return f"{port.name} 参数错误: " + "; ".join(parts)


__all__ = ["DataGateway"]

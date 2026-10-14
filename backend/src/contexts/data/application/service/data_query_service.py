"""按名调用的统一应用层入口（HTTP /data/*、Agent 工具、采集管理"试查"）

固定 policy=QUERY：限频不等待，实时类 Port 自动走缓存。
其他应用层代码一律类型化调用 gateway.fetch(XxxPort, ...)，不经过这里。
"""
from __future__ import annotations

import logging
from typing import Optional

from contexts.data.application.port import DataGatewayPort
from contexts.data.application.port.base import CallPolicy, DataCommand, DataResult, InvalidParams, PortInfo

logger = logging.getLogger(__name__)

MAX_ITEMS = 5000


class DataQueryService:
    def __init__(self, gateway: DataGatewayPort) -> None:
        self._gateway = gateway

    def catalog(self) -> list[PortInfo]:
        return self._gateway.catalog()

    def has(self, name: str) -> bool:
        return any(p.name == name for p in self._gateway.catalog())

    def is_realtime(self, name: str) -> bool:
        return self._gateway.is_realtime(name)

    async def query(self, name: str, params: Optional[dict], *, source: Optional[str] = None) -> DataResult:
        res = await self._gateway.invoke(
            DataCommand(name=name, params=params or {}, source=source, policy=CallPolicy.QUERY)
        )
        if len(res.items) > MAX_ITEMS:
            raise InvalidParams(f"返回 {len(res.items)} 条，超过上限 {MAX_ITEMS}，请缩小范围或改用采集任务入库")
        logger.info("data.query %s source=%s n=%d %dms", name, res.source, len(res.items), res.latency_ms)
        return res

    async def stats(self, name: str, days: int = 1) -> list[dict]:
        return await self._gateway.stats(name, days)


def build_agent_tools(svc: DataQueryService) -> list[dict]:
    """由数据目录生成 Agent 工具定义；调用时 await svc.query(name, args)"""
    return [
        {
            "name": f"data_{p.name}",
            "description": f"{p.label}：{p.description}" if p.description else p.label,
            "parameters": p.params_schema,
        }
        for p in svc.catalog()
    ]


__all__ = ["DataQueryService", "MAX_ITEMS", "build_agent_tools"]

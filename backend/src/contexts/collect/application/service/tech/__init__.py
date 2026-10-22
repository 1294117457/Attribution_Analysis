"""tech — 技术面 service 集合（5 个）

每个 service 对应一个 fetcher + 一个 route，结构与 fetcher/tech/ 镜像。
"""
from contexts.collect.application.service.tech.daily_service import DailyService
from contexts.collect.application.service.tech.minute_service import MinuteService
from contexts.collect.application.service.tech.adj_factor_service import AdjFactorService
from contexts.collect.application.service.tech.suspend_service import SuspendService
from contexts.collect.application.service.tech.name_change_service import NameChangeService

__all__ = [
    "DailyService",
    "MinuteService",
    "AdjFactorService",
    "SuspendService",
    "NameChangeService",
]

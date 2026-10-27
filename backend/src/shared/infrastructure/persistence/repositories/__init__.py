"""shared.infrastructure.persistence.repositories

公共元数据仓储（跨 context 复用）：
- collect_log_repository: 采集日志仓储（collect_logs @ attribution_db）
"""
from shared.infrastructure.persistence.repositories.collect_log_repository import (
    CollectLogRepository,
)

__all__ = ["CollectLogRepository"]

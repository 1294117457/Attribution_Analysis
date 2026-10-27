"""Collect infrastructure models（ORM）

跨 context 的公共元数据模型：
- collect_log: 采集日志表（collect_logs @ attribution_db）
"""
from shared.infrastructure.persistence.models.collect_log import CollectLogDB

__all__ = ["CollectLogDB"]

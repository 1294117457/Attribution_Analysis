"""时间戳混入"""

from datetime import datetime
from sqlalchemy import Column, DateTime


class TimestampMixin:
    """为 ORM 模型自动添加 created_at / updated_at 字段"""

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

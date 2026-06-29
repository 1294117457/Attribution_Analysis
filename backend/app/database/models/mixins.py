"""数据库模型混入类"""

from sqlalchemy import Column, DateTime
from datetime import datetime


class TimestampMixin:
    """时间戳混入"""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

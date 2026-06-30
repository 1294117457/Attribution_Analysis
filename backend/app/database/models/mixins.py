"""时间戳混入"""

from datetime import datetime
from sqlalchemy import Column, DateTime


class TimestampMixin:
    """时间戳混入"""

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

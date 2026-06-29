from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import DateTime
from datetime import datetime
class Base(DeclarativeBase):
  pass

class TimestamMixin:
  created_at=Column(DateTime,default=datetime.utcnow)
  updated_at=Column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
  
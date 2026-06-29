from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from core.config import get_settings

settings=get_settings()

# 同步引擎
engine=create_engine(
  settings.DATABASE_URL,
  pool_pre_ping=True,
  poll_size=10,
  max_overflow=20,
)
# Session工厂
SessionLocal=sessionmaker(autocommit=False,autoflush=False,bind=engine)

@contextmanager
def get_db()->Session:
  db=SessionLocal()
  try:
    yield db 
  finally:
    db.close()
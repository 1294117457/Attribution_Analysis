"""数据库连接"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 连接前测试
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出
    echo=settings.DEBUG,  # 打印 SQL
    pool_recycle=3600,  # 一小时回收连接
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

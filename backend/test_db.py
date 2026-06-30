"""测试数据库连接和模型"""

from sqlalchemy import text
from app.database.connection import engine, SessionLocal
from app.database.models.stock import DailyKlineDB
from app.database.base import Base

# 测试连接
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("✅ 数据库连接成功!")

# 测试 Session
session = SessionLocal()
print("✅ Session 创建成功!")
session.close()

# 测试模型
print(f"DailyKlineDB 表名: {DailyKlineDB.__tablename__}")
print("✅ 模型加载成功!")

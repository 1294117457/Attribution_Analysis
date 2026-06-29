# test_db.py
from app.database.connection import engine, SessionLocal
from app.database.models.stock import StockKlineDB

# 测试连接
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("✅ 数据库连接成功!")

# 测试 Session
session = SessionLocal()
print("✅ Session 创建成功!")
session.close()

# 测试模型
from app.database.base import Base

print(f"StockKlineDB 表名: {StockKlineDB.__tablename__}")

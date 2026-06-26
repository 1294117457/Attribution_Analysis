"""
建表脚本：用 SQL 语句在数据库中创建 klines 表。
只需执行一次，之后不需要再运行。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings

# 建表 SQL
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS klines (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    amount FLOAT NOT NULL,
    change_pct FLOAT,
    turnover_rate FLOAT
);
"""

# 索引 SQL
CREATE_INDEXES_SQL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_code_date ON klines(code, date);",
    "CREATE INDEX IF NOT EXISTS idx_code ON klines(code);",
    "CREATE INDEX IF NOT EXISTS idx_date ON klines(date);",
]


def init_db():
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        # 建表
        conn.execute(text(CREATE_TABLE_SQL))
        print("✓ 表 klines 创建成功")

        # 建索引
        for idx_sql in CREATE_INDEXES_SQL:
            conn.execute(text(idx_sql))
        print("✓ 索引创建成功")

        conn.commit()

    print("数据库初始化完成！")


if __name__ == "__main__":
    init_db()

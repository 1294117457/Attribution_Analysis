"""数据库初始化脚本"""

import sys
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import engine, Base
from app.models import KLine, News, Report  # noqa: F401


def init_db():
    """初始化数据库（创建所有表）"""
    print("🔧 初始化数据库...")

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    print("✅ 数据库初始化完成！")
    print("📋 已创建表：klines, news, reports")


if __name__ == "__main__":
    init_db()

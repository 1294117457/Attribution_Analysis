"""采集单个股票数据

Usage:
    python -m data.scripts.collect_stock 000001
    python -m data.scripts.collect_stock 000001 --days 30
"""

import sys
import argparse
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import get_db_session
from data.services import StockService


def main():
    parser = argparse.ArgumentParser(description="采集股票数据")
    parser.add_argument("symbol", help="股票代码，如 000001")
    parser.add_argument("--days", type=int, default=365, help="采集天数")
    args = parser.parse_args()

    with get_db_session() as session:
        service = StockService(session)
        count = service.collect_and_save(args.symbol, days=args.days)
        print(f"✅ {args.symbol} 采集完成，存储 {count} 条数据")


if __name__ == "__main__":
    main()

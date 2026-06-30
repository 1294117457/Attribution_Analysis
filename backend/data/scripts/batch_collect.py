"""批量采集股票数据

Usage:
    python -m data.scripts.batch_collect
"""

import sys
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from infra.database import get_db_session
from data.services import StockService


# 默认采集的股票列表
DEFAULT_SYMBOLS = [
    "000001",  # 平安银行
    "000002",  # 万科A
    "600000",  # 浦发银行
    "600519",  # 贵州茅台
    "600036",  # 招商银行
]


def main():
    symbols = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_SYMBOLS

    print(f"开始批量采集 {len(symbols)} 只股票...")

    with get_db_session() as session:
        service = StockService(session)
        results = service.collect_batch_and_save(symbols, days=30)

        print("\n采集结果:")
        for symbol, count in results.items():
            status = "✅" if count > 0 else "⚠️"
            print(f"  {status} {symbol}: {count} 条")


if __name__ == "__main__":
    main()

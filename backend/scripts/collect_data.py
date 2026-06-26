"""
数据采集脚本：从 AkShare 获取 K 线数据，写入数据库。
调用 app.data.akshare_client 获取数据，写入 PostgreSQL。

用法：
    python scripts/collect_data.py
    python scripts/collect_data.py 600519 20200101 20250626
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from typing import Optional

from sqlalchemy import create_engine, text
from app.config import settings
from app.data.akshare_client import AkShareClient, get_client

# 默认采集的股票列表
DEFAULT_STOCKS = [
    ("600519", "贵州茅台"),
    ("000858", "五粮液"),
    ("000001", "平安银行"),
    ("601318", "中国平安"),
    ("600036", "招商银行"),
]


def save_klines(code: str, name: str, klines: list[dict]) -> int:
    """将 K 线数据批量写入数据库"""
    if not klines:
        return 0

    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        for kline in klines:
            conn.execute(
                text("""
                    INSERT INTO klines (code, name, date, open, high, low, close, volume, amount, change_pct, turnover_rate)
                    VALUES (:code, :name, :date, :open, :high, :low, :close, :volume, :amount, :change_pct, :turnover_rate)
                    ON CONFLICT (code, date) DO UPDATE SET
                        name = EXCLUDED.name,
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        amount = EXCLUDED.amount,
                        change_pct = EXCLUDED.change_pct,
                        turnover_rate = EXCLUDED.turnover_rate
                """),
                {
                    "code": kline["code"],
                    "name": name,
                    "date": kline["date"],
                    "open": kline["open"],
                    "high": kline["high"],
                    "low": kline["low"],
                    "close": kline["close"],
                    "volume": kline["volume"],
                    "amount": kline["amount"],
                    "change_pct": kline["change_pct"],
                    "turnover_rate": kline["turnover_rate"],
                },
            )
        conn.commit()

    return len(klines)


def collect_stock(client: AkShareClient, code: str, name: str, start_date: str, end_date: str) -> int:
    """采集单只股票数据"""
    print(f"正在采集 {code} {name}...")

    try:
        klines = client.fetch_klines(code, start_date, end_date)

        if not klines:
            print(f"  ✗ {code} 数据为空，跳过")
            return 0

        # 注入股票名称
        for kline in klines:
            kline["name"] = name

        saved = save_klines(code, name, klines)
        print(f"  ✓ {code} 写入 {saved} 条数据")
        return saved

    except Exception as e:
        print(f"  ✗ {code} 采集失败: {e}")
        return 0


def main(
    stocks: Optional[list[tuple[str, str]]] = None,
    start_date: str = "20200101",
    end_date: str = "20500101",
):
    """主函数"""
    if stocks is None:
        stocks = DEFAULT_STOCKS

    print("=" * 50)
    print(f"开始采集股票数据 ({start_date} ~ {end_date})")
    print(f"股票列表: {[s[0] for s in stocks]}")
    print("=" * 50)

    client = get_client(request_delay=1.0)
    total = 0

    for code, name in stocks:
        count = collect_stock(client, code, name, start_date, end_date)
        total += count

    print("=" * 50)
    print(f"采集完成，共写入 {total} 条数据")
    print("=" * 50)


if __name__ == "__main__":
    # 支持命令行参数：代码 开始日期 结束日期
    # python scripts/collect_data.py 600519 20200101 20250626
    if len(sys.argv) >= 4:
        code = sys.argv[1]
        start = sys.argv[2]
        end = sys.argv[3]
        main(stocks=[(code, code)], start_date=start, end_date=end)
    else:
        main()

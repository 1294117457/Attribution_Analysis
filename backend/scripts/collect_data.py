"""
数据采集脚本：从 AkShare 获取 K 线数据，写入数据库。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import akshare as ak
import pandas as pd
from sqlalchemy import create_engine, text
from app.config import settings

# 要采集的股票
STOCKS = [
    ("600519", "贵州茅台"),
    ("000858", "五粮液"),
]


def collect_stock(code: str, name: str) -> int:
    """采集单只股票数据"""
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

    print(f"正在采集 {code} {name}...")

    try:
        # 获取日 K 线数据（前复权）
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20200101", adjust="qfq")

        if df is None or df.empty:
            print(f"  ✗ {code} 数据为空，跳过")
            return 0

        inserted = 0
        with engine.connect() as conn:
            for _, row in df.iterrows():
                trade_date = row["日期"]
                # 转换日期格式：2024-01-01
                if isinstance(trade_date, str):
                    date_str = trade_date.replace("/", "-")
                else:
                    date_str = str(trade_date)[:10]

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
                        "code": code,
                        "name": name,
                        "date": date_str,
                        "open": float(row["开盘"]),
                        "high": float(row["最高"]),
                        "low": float(row["最低"]),
                        "close": float(row["收盘"]),
                        "volume": float(row["成交量"]),
                        "amount": float(row["成交额"]),
                        "change_pct": float(row["涨跌幅"]) if pd.notna(row["涨跌幅"]) else None,
                        "turnover_rate": float(row["换手率"]) if "换手率" in row and pd.notna(row["换手率"]) else None,
                    },
                )
                inserted += 1

            conn.commit()

        print(f"  ✓ {code} 写入 {inserted} 条数据")
        return inserted

    except Exception as e:
        print(f"  ✗ {code} 采集失败: {e}")
        return 0


def main():
    """主函数"""
    print("=" * 50)
    print("开始采集股票数据")
    print("=" * 50)

    total = 0
    for code, name in STOCKS:
        count = collect_stock(code, name)
        total += count
        time.sleep(1)  # 避免请求过快

    print("=" * 50)
    print(f"采集完成，共写入 {total} 条数据")
    print("=" * 50)


if __name__ == "__main__":
    main()

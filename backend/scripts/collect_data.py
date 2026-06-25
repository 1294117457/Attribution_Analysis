"""数据采集脚本 - 从 AkShare 采集A股数据"""

import sys
import asyncio
from datetime import date, timedelta
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.collector_service import CollectorService


async def collect_single_stock():
    """采集单只股票数据"""
    symbol = "600519"  # 贵州茅台
    end_date = date.today()
    start_date = end_date - timedelta(days=365)  # 一年数据

    print(f"📊 采集股票 {symbol} 数据...")
    print(f"📅 日期范围: {start_date} 至 {end_date}")

    db = SessionLocal()
    try:
        service = CollectorService(db)
        count = await service.collect_klines(symbol, start_date, end_date)
        print(f"✅ 采集完成，共 {count} 条数据")
    finally:
        db.close()


async def collect_batch_stocks():
    """批量采集多只股票数据"""
    symbols = [
        "600519",  # 贵州茅台
        "000858",  # 五粮液
        "601318",  # 中国平安
        "600036",  # 招商银行
        "000001",  # 平安银行
    ]
    end_date = date.today()
    start_date = end_date - timedelta(days=30)  # 最近一个月

    print(f"📊 批量采集 {len(symbols)} 只股票...")
    print(f"📅 日期范围: {start_date} 至 {end_date}")

    db = SessionLocal()
    try:
        service = CollectorService(db)
        results = await service.collect_klines_batch(symbols, start_date, end_date, delay=2)
        print(f"✅ 采集完成！")
        print(f"   成功: {results['success']} 只")
        print(f"   失败: {results['failed']} 只")
        print(f"   总数据: {results['total']} 条")
    finally:
        db.close()


async def collect_market():
    """采集全市场数据（耗时较长）"""
    print("⚠️ 全市场采集需要较长时间，请耐心等待...")

    db = SessionLocal()
    try:
        service = CollectorService(db)
        results = await service.collect_market_klines(
            market="all",
            start_date=None,
            days=7,  # 最近7天
        )
        print(f"✅ 采集完成！")
        print(f"   成功: {results['success']} 只")
        print(f"   失败: {results['failed']} 只")
        print(f"   总数据: {results['total']} 条")
    finally:
        db.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据采集脚本")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["single", "batch", "market"],
        default="single",
        help="采集模式",
    )
    args = parser.parse_args()

    if args.mode == "single":
        asyncio.run(collect_single_stock())
    elif args.mode == "batch":
        asyncio.run(collect_batch_stocks())
    elif args.mode == "market":
        asyncio.run(collect_market())


if __name__ == "__main__":
    main()

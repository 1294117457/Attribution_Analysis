"""
数据管理脚本。

用法：
    # 查看数据概况
    python scripts/data_manager.py --stats

    # 采集单只股票
    python scripts/data_manager.py --collect 000858

    # 采集多只股票
    python scripts/data_manager.py --collect 000858,600519,000001

    # 采集指数成分股
    python scripts/data_manager.py --collect-index 000300  # 沪深300
    python scripts/data_manager.py --collect-index 000905  # 中证500

    # 增量更新（采集最新数据）
    python scripts/data_manager.py --update

    # 查看股票列表
    python scripts/data_manager.py --list

    # 删除股票数据
    python scripts/data_manager.py --delete 000001

    # 检查数据完整性
    python scripts/data_manager.py --check 600519

    # 异常检测
    python scripts/data_manager.py --detect 600519
    python scripts/data_manager.py --detect-all
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime

from sqlalchemy import create_engine, text
from app.config import settings
from app.modules.collector.service import CollectorService
from app.modules.detector.service import DetectorService


def get_db():
    return create_engine(settings.DATABASE_URL)


def cmd_stats():
    """查看数据概况"""
    print("\n" + "=" * 60)
    print("📊 数据概况")
    print("=" * 60)

    engine = get_db()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT code, name, COUNT(*) as cnt,
                   MIN(date)::text as start_date,
                   MAX(date)::text as end_date
            FROM klines
            GROUP BY code, name
            ORDER BY code
        """))

        total = 0
        for row in result:
            print(f"  {row[0]} {row[1]}")
            print(f"    数据量: {row[2]} 条")
            print(f"    时间范围: {row[3]} ~ {row[4]}")
            total += row[2]

        print("-" * 40)
        print(f"  总计: {total} 条, {result.rowcount} 只股票")

        # 最新数据日期
        result = conn.execute(text("SELECT MAX(date)::text FROM klines"))
        print(f"  最新数据日期: {result.fetchone()[0]}")


def cmd_list():
    """查看股票列表"""
    print("\n" + "=" * 60)
    print("📋 已采集的股票列表")
    print("=" * 60)

    engine = get_db()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT code, name, COUNT(*) as cnt
            FROM klines
            GROUP BY code, name
            ORDER BY code
        """))

        if result.rowcount == 0:
            print("  暂无数据")
        else:
            for i, row in enumerate(result, 1):
                print(f"  {i}. {row[0]} {row[1]} ({row[2]}条)")


def cmd_check(code: str):
    """检查数据完整性"""
    print("\n" + "=" * 60)
    print(f"🔍 检查 {code} 数据完整性")
    print("=" * 60)

    engine = get_db()
    with engine.connect() as conn:
        # 基本信息
        result = conn.execute(text("""
            SELECT code, name, COUNT(*) as total,
                   COUNT(change_pct) as change_pct_count,
                   COUNT(turnover_rate) as turnover_rate_count,
                   MIN(date)::text, MAX(date)::text
            FROM klines WHERE code = :code
            GROUP BY code, name
        """), {"code": code})

        row = result.fetchone()
        if not row:
            print(f"  ❌ 股票 {code} 不存在")
            return

        print(f"  代码: {row[0]}")
        print(f"  名称: {row[1]}")
        print(f"  总记录数: {row[2]}")
        print(f"  涨跌幅数据: {row[3]}/{row[2]}")
        print(f"  换手率数据: {row[4]}/{row[2]}")
        print(f"  时间范围: {row[5]} ~ {row[6]}")

        # 计算缺失天数
        expected_days = (datetime.strptime(row[6], "%Y-%m-%d") -
                         datetime.strptime(row[5], "%Y-%m-%d")).days + 1
        missing = expected_days - row[2]
        if missing > 0:
            print(f"  ⚠️  预计缺失约 {missing} 个交易日（正常，周末/节假日）")
        else:
            print(f"  ✅ 数据完整")

        # 最新几条
        print("\n  最近5条数据:")
        result = conn.execute(text("""
            SELECT date::text, close, change_pct, volume
            FROM klines WHERE code = :code
            ORDER BY date DESC LIMIT 5
        """), {"code": code})
        for row in result:
            print(f"    {row[0]}: 收={row[1]} 涨跌={row[2]}% 量={row[3]}")


def cmd_collect(codes: list[str], days: int = 365 * 5):
    """采集股票数据"""
    print("\n" + "=" * 60)
    print(f"📥 采集股票数据")
    print("=" * 60)

    service = CollectorService()
    start_date = f"{datetime.now().year - 5}0101"
    end_date = datetime.now().strftime("%Y%m%d")

    for code in codes:
        # 尝试获取股票名称
        engine = get_db()
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM klines WHERE code = :code LIMIT 1"
            ), {"code": code})
            row = result.fetchone()
            name = row[0] if row else code

        print(f"\n正在采集 {code} {name}...")
        result = service.collect_single(code, name, start_date, end_date)

        if result.success:
            print(f"  ✅ 成功: 采集 {result.collected} 条，保存 {result.saved} 条")
        else:
            print(f"  ❌ 失败: {result.error}")


def cmd_collect_index(index_code: str):
    """采集指数成分股"""
    print("\n" + "=" * 60)
    print(f"📥 采集指数 {index_code} 成分股")
    print("=" * 60)

    service = CollectorService()
    start_date = f"{datetime.now().year - 5}0101"
    end_date = datetime.now().strftime("%Y%m%d")

    print("正在获取成分股列表...")
    result = service.collect_index(index_code, start_date, end_date)

    print(f"\n采集完成:")
    print(f"  总数: {result.total}")
    print(f"  成功: {result.success}")
    print(f"  失败: {result.failed}")
    print(f"  采集数据: {result.total_collected}")
    print(f"  保存数据: {result.total_saved}")

    if result.failed > 0:
        print("\n失败列表:")
        for r in result.results:
            if not r.success:
                print(f"  {r.code}: {r.error}")


def cmd_update():
    """增量更新所有股票"""
    print("\n" + "=" * 60)
    print("🔄 增量更新数据")
    print("=" * 60)

    # 获取已有股票列表
    engine = get_db()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT code, name FROM klines"))
        stocks = [(row[0], row[1]) for row in result]

    if not stocks:
        print("  暂无数据，请先采集")
        return

    print(f"发现 {len(stocks)} 只股票，开始增量更新...")

    service = CollectorService()
    result = service.incremental_collect(stocks)

    print(f"\n更新完成:")
    print(f"  总数: {result.total}")
    print(f"  成功: {result.success}")
    print(f"  新增数据: {result.total_saved}")


def cmd_delete(code: str):
    """删除股票数据"""
    print("\n" + "=" * 60)
    print(f"🗑️  删除 {code} 数据")
    print("=" * 60)

    engine = get_db()
    with engine.connect() as conn:
        # 先查看
        result = conn.execute(text(
            "SELECT COUNT(*) FROM klines WHERE code = :code"
        ), {"code": code})
        count = result.fetchone()[0]

        if count == 0:
            print(f"  股票 {code} 不存在")
            return

        print(f"  将删除 {count} 条数据")
        confirm = input("  确认删除? (y/N): ")

        if confirm.lower() == 'y':
            conn.execute(text("DELETE FROM klines WHERE code = :code"), {"code": code})
            conn.commit()
            print(f"  ✅ 已删除 {code} 的 {count} 条数据")
        else:
            print("  已取消")


def cmd_detect(code: str, days: int = 30):
    """检测异常"""
    print("\n" + "=" * 60)
    print(f"🔍 异常检测: {code}")
    print("=" * 60)

    service = DetectorService()
    result = service.detect(code, lookback_days=days)

    print(f"  代码: {result['code']}")
    print(f"  名称: {result.get('name', 'N/A')}")
    print(f"  日期: {result['trade_date']}")
    print(f"  是否异常: {'⚠️ 是' if result['is_anomaly'] else '✅ 否'}")
    print(f"  严重程度: {result['severity']}")
    print(f"  异常分数: {result['score']}")

    if result.get('triggers'):
        print("\n  触发原因:")
        for t in result['triggers']:
            print(f"    - [{t['detector']}] {t['reason']} (score={t['score']})")

    if result.get('kline'):
        k = result['kline']
        print(f"\n  K线数据:")
        print(f"    开盘: {k['open']}")
        print(f"    最高: {k['high']}")
        print(f"    最低: {k['low']}")
        print(f"    收盘: {k['close']}")
        print(f"    成交量: {k['volume']}")
        print(f"    涨跌幅: {k['change_pct']}%")


def cmd_detect_all():
    """批量检测所有股票"""
    print("\n" + "=" * 60)
    print("🔍 批量异常检测")
    print("=" * 60)

    # 获取股票列表
    engine = get_db()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT code FROM klines"))
        codes = [row[0] for row in result]

    if not codes:
        print("  暂无数据")
        return

    service = DetectorService()
    result = service.detect_batch(codes)

    print(f"  检测股票数: {result['total']}")
    print(f"  发现异常: {result['anomaly_count']}")

    if result['anomaly_count'] > 0:
        print("\n  异常列表:")
        for r in result['results']:
            if r['is_anomaly']:
                print(f"    {r['code']} {r.get('name', '')}")
                print(f"      严重程度: {r['severity']}, 分数: {r['score']}")


def main():
    parser = argparse.ArgumentParser(description="数据管理脚本")
    parser.add_argument("--stats", action="store_true", help="查看数据概况")
    parser.add_argument("--list", action="store_true", help="查看股票列表")
    parser.add_argument("--check", type=str, help="检查数据完整性")
    parser.add_argument("--collect", type=str, help="采集股票，逗号分隔")
    parser.add_argument("--collect-index", type=str, help="采集指数成分股")
    parser.add_argument("--update", action="store_true", help="增量更新")
    parser.add_argument("--delete", type=str, help="删除股票数据")
    parser.add_argument("--detect", type=str, help="检测异常")
    parser.add_argument("--detect-all", action="store_true", help="批量检测")
    parser.add_argument("--days", type=int, default=30, help="回看天数")

    args = parser.parse_args()

    if args.stats:
        cmd_stats()
    elif args.list:
        cmd_list()
    elif args.check:
        cmd_check(args.check)
    elif args.collect:
        codes = args.collect.split(",")
        cmd_collect(codes)
    elif args.collect_index:
        cmd_collect_index(args.collect_index)
    elif args.update:
        cmd_update()
    elif args.delete:
        cmd_delete(args.delete)
    elif args.detect:
        cmd_detect(args.detect, args.days)
    elif args.detect_all:
        cmd_detect_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

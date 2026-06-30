"""测试数据采集功能"""
import sys
sys.path.insert(0, '.')

from datetime import date, timedelta
from infra.database.base import Base
from infra.database.connection import engine, SessionLocal
from infra.database.models import DailyKlineDB
from data.services.stock_service import StockService


def setup_db():
    """初始化数据库"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库初始化完成")


def test_collect():
    """测试采集功能"""
    db = SessionLocal()
    service = StockService(db)

    print("\n=== 测试采集 000001 最近 5 天数据 ===")
    try:
        count = service.collect_and_save(symbol="000001", days=5)
        print(f"✅ 采集成功，新增 {count} 条数据")
    except Exception as e:
        print(f"❌ 采集失败: {e}")
        db.close()
        return
    db.close()


def test_query():
    """测试查询功能"""
    db = SessionLocal()
    service = StockService(db)

    print("\n=== 测试查询 000001 数据 ===")
    klines = service.get_klines("000001", limit=5)
    print(f"✅ 查询成功，返回 {len(klines)} 条数据")
    for k in klines:
        print(f"   {k.date} | 开:{k.open:.2f} 高:{k.high:.2f} 低:{k.low:.2f} 收:{k.close:.2f} 涨跌:{k.change_pct or 0:.2f}%")
    db.close()


def test_inventory():
    """测试数据清单"""
    db = SessionLocal()

    print("\n=== 测试数据清单 ===")
    from sqlalchemy import func
    results = (
        db.query(
            DailyKlineDB.symbol,
            func.max(DailyKlineDB.name).label("name"),
            func.count(DailyKlineDB.id).label("record_count"),
            func.min(DailyKlineDB.date).label("start_date"),
            func.max(DailyKlineDB.date).label("end_date"),
        )
        .group_by(DailyKlineDB.symbol)
        .all()
    )

    print(f"✅ 共 {len(results)} 只股票")
    for r in results:
        print(f"   {r.symbol} {r.name or ''}: {r.record_count} 条 ({r.start_date} ~ {r.end_date})")
    db.close()


def test_delete():
    """测试删除功能"""
    db = SessionLocal()

    print("\n=== 测试删除 000001 数据 ===")
    deleted = db.query(DailyKlineDB).filter(DailyKlineDB.symbol == "000001").delete()
    db.commit()
    print(f"✅ 删除成功，删除了 {deleted} 条数据")
    db.close()


def test_delete_single():
    """测试删除单条"""
    db = SessionLocal()
    service = StockService(db)

    # 先重新采集
    print("\n=== 测试删除单条数据 ===")
    service.collect_and_save(symbol="000001", days=2)

    # 获取一条数据
    kline = db.query(DailyKlineDB).filter(DailyKlineDB.symbol == "000001").first()
    if kline:
        deleted = db.query(DailyKlineDB).filter(
            DailyKlineDB.symbol == kline.symbol,
            DailyKlineDB.date == kline.date,
        ).delete()
        db.commit()
        print(f"✅ 删除单条成功: {kline.symbol} {kline.date}")
    db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("数据采集功能测试")
    print("=" * 50)

    setup_db()
    test_collect()
    test_query()
    test_inventory()
    test_delete()

    # 重新采集用于前端演示
    test_collect()

    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)

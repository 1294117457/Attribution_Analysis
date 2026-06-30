"""测试数据采集"""

from datetime import date, timedelta
from data.adapters.akshare import AkShareFetcher
from data.schemas.kline import DailyKline
from data.interfaces.fetcher import CollectParams
from data.services.stock_service import StockService
from infra.database.connection import get_db_session


def test_akshare_fetcher():
    """测试 AkShare 数据获取"""
    fetcher = AkShareFetcher(DailyKline)
    params = CollectParams(symbol="000001", days=30)
    klines = fetcher.fetch(params)

    print(f"获取到 {len(klines)} 条数据")
    if klines:
        print(f"最新数据: {klines[0]}")

    assert len(klines) > 0, "应该获取到数据"
    print("✅ test_akshare_fetcher 通过!")


def test_stock_service():
    """测试数据服务（需要数据库连接）"""
    with get_db_session() as db:
        service = StockService(db)
        klines = service.get_klines("000001", limit=10)
        print(f"查询到 {len(klines)} 条数据")
        print("✅ test_stock_service 通过!")


if __name__ == "__main__":
    test_akshare_fetcher()
    test_stock_service()
    print("\n🎉 所有测试通过!")

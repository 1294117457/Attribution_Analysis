"""测试数据采集"""

from datetime import date, timedelta
from data.akshare_client import AkShareClient
from data.service import DataService


def test_get_stock_kline():
    """测试获取 K 线数据"""
    client = AkShareClient()

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    klines = client.get_stock_kline("000001", start_date, end_date)

    print(f"获取到 {len(klines)} 条数据")
    if klines:
        print(f"最新数据: {klines[0]}")

    assert len(klines) > 0, "应该获取到数据"
    print("✅ test_get_stock_kline 通过!")


def test_get_stock_name():
    """测试获取股票名称"""
    client = AkShareClient()
    name = client.get_stock_name("000001")
    print(f"股票名称: {name}")
    assert name, "应该获取到股票名称"
    print("✅ test_get_stock_name 通过!")


def test_data_service():
    """测试数据服务"""
    service = DataService()
    klines = service.collect_stock("000001", days=7)

    print(f"采集到 {len(klines)} 条数据")
    if klines:
        kline = klines[0]
        print(f"代码: {kline.symbol}, 名称: {kline.name}")
        print(f"日期: {kline.date}, 收盘: {kline.close}")

    assert len(klines) > 0
    print("✅ test_data_service 通过!")


if __name__ == "__main__":
    test_get_stock_name()
    test_get_stock_kline()
    test_data_service()
    print("\n🎉 所有测试通过!")

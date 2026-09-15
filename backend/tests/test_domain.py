"""领域层单元测试

无需数据库、无需外部依赖。
"""

from datetime import date

import pytest

from domain.kline.entity import Kline
from domain.kline.value_objects import StockCode, TradeDate
from domain.stock_info.entity import StockInfo
from domain.stock_info.value_objects import Industry, Market


# ════════════════════════════════════════════════════════════════
# StockCode 值对象
# ════════════════════════════════════════════════════════════════

class TestStockCode:
    def test_valid_code(self):
        code = StockCode("000001")
        assert code.code == "000001"

    def test_invalid_code_length(self):
        with pytest.raises(ValueError):
            StockCode("12345")

    def test_invalid_code_non_digit(self):
        with pytest.raises(ValueError):
            StockCode("abc123")

    def test_is_shanghai(self):
        assert StockCode("600000").is_shanghai is True
        assert StockCode("688001").is_shanghai is True

    def test_is_shenzhen(self):
        assert StockCode("000001").is_shenzhen is True
        assert StockCode("300001").is_shenzhen is True

    def test_equality(self):
        assert StockCode("000001") == StockCode("000001")
        assert StockCode("000001") != StockCode("000002")

    def test_hashable(self):
        codes = {StockCode("000001"), StockCode("000002"), StockCode("000001")}
        assert len(codes) == 2


# ════════════════════════════════════════════════════════════════
# Kline 聚合根
# ════════════════════════════════════════════════════════════════

class TestKline:
    def test_create_valid_kline(self):
        k = Kline.create(
            symbol="000001",
            name="平安银行",
            trade_date=date(2024, 1, 1),
            open=10.0,
            high=11.0,
            low=9.0,
            close=10.5,
            volume=1000,
            amount=10000,
            change_pct=5.0,
        )
        assert k.symbol.code == "000001"
        assert k.trade_date.date == date(2024, 1, 1)
        assert k.is_up is True
        assert k.is_down is False
        assert k.price_range == 2.0

    def test_validation_high_less_than_low(self):
        with pytest.raises(ValueError, match="最高价不能低于最低价"):
            Kline.create(
                symbol="000001", name="test", trade_date=date(2024, 1, 1),
                open=10, high=8, low=10, close=9,
                volume=1000, amount=10000,
            )

    def test_validation_negative_volume(self):
        with pytest.raises(ValueError, match="成交量不能为负"):
            Kline.create(
                symbol="000001", name="test", trade_date=date(2024, 1, 1),
                open=10, high=11, low=9, close=10,
                volume=-100, amount=10000,
            )

    def test_validation_negative_amount(self):
        with pytest.raises(ValueError, match="成交额不能为负"):
            Kline.create(
                symbol="000001", name="test", trade_date=date(2024, 1, 1),
                open=10, high=11, low=9, close=10,
                volume=100, amount=-100,
            )

    def test_invalid_symbol(self):
        with pytest.raises(ValueError):
            Kline.create(
                symbol="invalid", name="test", trade_date=date(2024, 1, 1),
                open=10, high=11, low=9, close=10,
                volume=100, amount=100,
            )

    def test_equality(self):
        kwargs = dict(
            symbol="000001", name="test", trade_date=date(2024, 1, 1),
            open=10, high=11, low=9, close=10, volume=100, amount=100,
        )
        k1 = Kline.create(**kwargs)
        k2 = Kline.create(**kwargs)
        assert k1 == k2


# ════════════════════════════════════════════════════════════════
# StockInfo 聚合根
# ════════════════════════════════════════════════════════════════

class TestStockInfo:
    def test_create_basic(self):
        stock = StockInfo.create(symbol="000001", name="平安银行")
        assert stock.symbol == "000001"
        assert stock.name == "平安银行"
        assert stock.industry is None

    def test_create_with_industry_and_market(self):
        stock = StockInfo.create(
            symbol="000001",
            name="平安银行",
            industry="银行",
            market="SZ",
        )
        assert stock.industry.name == "银行"
        assert stock.market.code == "SZ"

    def test_update_name(self):
        stock = StockInfo.create(symbol="000001", name="旧名")
        stock.update_name("新名")
        assert stock.name == "新名"


# ════════════════════════════════════════════════════════════════
# KlineBO / KlineVO Schema
# ════════════════════════════════════════════════════════════════

class TestKlineSchemas:
    def test_klinebo_to_entity(self):
        from domain.kline.schemas import KlineBO
        bo = KlineBO(
            symbol="000001", name="平安银行", trade_date=date(2024, 1, 1),
            open=10, high=11, low=9, close=10.5,
            volume=1000, amount=10000, change_pct=5.0,
        )
        entity = bo.to_entity()
        assert entity.symbol.code == "000001"
        assert entity.name == "平安银行"

    def test_klinevo_from_entity(self):
        from domain.kline.schemas import KlineVO
        entity = Kline.create(
            symbol="000001", name="test", trade_date=date(2024, 1, 1),
            open=10, high=11, low=9, close=10.5,
            volume=1000, amount=10000,
        )
        vo = KlineVO.from_entity(entity)
        assert vo.symbol == "000001"
        assert vo.date == date(2024, 1, 1)


# ════════════════════════════════════════════════════════════════
# Market 值对象
# ════════════════════════════════════════════════════════════════

class TestMarket:
    def test_from_code_shanghai(self):
        m = Market.from_code("SH")
        assert m.code == "SH"
        assert m.is_shanghai is True

    def test_from_code_shenzhen(self):
        m = Market.from_code("SZ")
        assert m.code == "SZ"
        assert m.is_shenzhen is True

    def test_from_code_default(self):
        m = Market.from_code("UNKNOWN")
        assert m.code == "SZ"

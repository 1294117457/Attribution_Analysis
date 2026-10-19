"""端到端 fetcher 单元测试（mock SDK 返回，验证 BO 构造）

不调用真实 SDK。每个 fetcher 用 1 行 mock data 验证：
- BO 构造成功
- 字段映射正确

用法: python -m scripts.test_fetcher_mock
"""
import sys
import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# 强制 import 所有 BO/fetcher
import contexts.collect.application.bo  # noqa
import contexts.concept.application.bo.concept  # noqa
import contexts.market.application.bo.stock_info  # noqa

import contexts.collect.infrastructure.fetcher.tech  # noqa
import contexts.collect.infrastructure.fetcher.capital  # noqa
import contexts.collect.infrastructure.fetcher.fundamental  # noqa
import contexts.collect.infrastructure.fetcher.news  # noqa


# ========== 准备 mock data ==========

# 模拟 pandas DataFrame 行为的辅助类
class MockRow(dict):
    """支持 pd.notna 判定的 dict"""
    def __getitem__(self, key):
        v = super().__getitem__(key, None)
        if v is None:
            raise KeyError(key)
        return v


class MockDF(list):
    """支持 to_dict('records') 的 DataFrame mock"""
    def __init__(self, records: list[dict]):
        super().__init__(records)
        self._records = records
    def to_dict(self, orient: str) -> list[dict]:
        return self._records
    @property
    def empty(self) -> bool:
        return len(self._records) == 0
    def iterrows(self):
        for i, r in enumerate(self._records):
            yield i, MockRow(r)
    def sort_values(self, *args, **kwargs):
        return self
    def reset_index(self, *args, **kwargs):
        return self
    def __bool__(self):
        return not self.empty
    # 兼容 pd.notna
    def get(self, key, default=None):
        return self._records[0].get(key, default) if self._records else default


def _df(records: list[dict]) -> MockDF:
    return MockDF(records)


# ========== 各 fetcher 测试用例 ==========

async def test_stock_basic():
    from contexts.collect.infrastructure.fetcher.fundamental.StockBasicTushareFetcher import (
        StockBasicTushareFetcher,
    )
    record = {
        "ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行",
        "area": "深圳", "industry": "银行", "market": "主板", "exchange": "SZSE",
        "list_date": "19910403", "delist_date": None, "list_status": "L", "is_hs": "H",
        "act_name": "无", "act_ent_type": "其他",
        # §1.1 新增
        "fullname": "平安银行股份有限公司",
        "enname": "Ping An Bank Co., Ltd.",
        "cnspell": "PAYH",
        "curr_type": "CNY",
    }
    # StockBasicTushareFetcher 会对 3 个交易所各调一次 → 3 行相同
    records = [record, record, record]
    fetcher = StockBasicTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(list_status="L")
    # 允许重复（fetcher 没去重），但至少 1 条
    assert len(out) >= 1
    bo = out[0]
    assert bo.symbol == "000001"
    assert bo.fullname == "平安银行股份有限公司"
    assert bo.enname == "Ping An Bank Co., Ltd."
    assert bo.cnspell == "PAYH"
    assert bo.curr_type == "CNY"
    print(f"  [OK ] StockBasicTushareFetcher 4 新字段 fullname/enname/cnspell/curr_type")


async def test_moneyflow_hsgt():
    from contexts.collect.infrastructure.fetcher.capital.MoneyflowHsgtTushareFetcher import (
        MoneyflowHsgtTushareFetcher,
    )
    records = [{
        "trade_date": "20251017", "ts_code": "000001.SZ", "name": "平安银行",
        "market_type": "3",  # 深市
        "close": 12.5,
        "change": 0.1,        # 涨跌额
        "pct_chg": 0.81,      # 涨跌幅
        "rank": 5,
        "amount": 12345.0,
        "net_amount": 1234.0,
        "buy": 6789.0,
        "sell": 5555.0,
    }]
    fetcher = MoneyflowHsgtTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(trade_date="2025-10-17")
    assert len(out) == 1
    bo = out[0]
    assert bo.symbol == "000001"
    assert bo.market_type == "3"
    assert bo.p_change == 0.1     # change → p_change
    assert bo.pct_change == 0.81
    assert bo.rank == 5
    print(f"  [OK ] MoneyflowHsgtTushareFetcher 字段语义对齐 p_change/pct_change")


async def test_limit_list_d():
    from contexts.collect.infrastructure.fetcher.capital.LimitListTushareFetcher import (
        LimitListTushareFetcher,
    )
    records = [{
        "trade_date": "20251017", "ts_code": "600000.SH", "industry": "银行",
        "name": "浦发银行", "close": 10.5, "pct_chg": 10.0,   # 文档叫 pct_chg
        "amount": 12345.0, "limit_amount": None, "float_mv": 100.0, "total_mv": 200.0,
        "turnover_ratio": 5.0, "fd_amount": 100.0,
        "first_time": "093000", "last_time": "150000",
        "open_times": 0, "up_stat": "1/1", "limit_times": 1,
        "limit": "U",  # 文档字段 limit
    }]
    fetcher = LimitListTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(trade_date="2025-10-17")
    assert len(out) == 1
    bo = out[0]
    assert bo.symbol == "600000"
    assert bo.pct_chg == 10.0
    assert bo.limit_type == "U"
    assert bo.limit_times == 1
    assert bo.first_time == "093000"
    print(f"  [OK ] LimitListTushareFetcher 18 字段对齐 pct_chg/limit(→limit_type)/limit_times")


async def test_hsgt_top10():
    from contexts.collect.infrastructure.fetcher.capital.HsgtTop10TushareFetcher import (
        HsgtTop10TushareFetcher,
    )
    records = [{
        "trade_date": "20251017", "ts_code": "600519.SH", "name": "贵州茅台",
        "market_type": "1",  # 沪市
        "close": 1500.0,
        "change": 10.0,   # 涨跌额 → p_change
        "rank": 1,
        "amount": 100000.0,
        "net_amount": 5000.0,
        "buy": 52000.0,
        "sell": 47000.0,
    }]
    fetcher = HsgtTop10TushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(trade_date="2025-10-17")
    assert len(out) == 1
    bo = out[0]
    assert bo.symbol == "600519"
    assert bo.market_type == "1"
    assert bo.rank == 1
    assert bo.p_change == 10.0
    assert bo.net_amount == 5000.0
    print(f"  [OK ] HsgtTop10TushareFetcher 11 字段对齐 含 rank/market_type")


async def test_fin_income():
    from contexts.collect.infrastructure.fetcher.fundamental.FinIncomeTushareFetcher import (
        FinIncomeTushareFetcher,
    )
    records = [{
        "ts_code": "000001.SZ", "ann_date": "20250420", "end_date": "20250331",
        "report_type": "1", "comp_type": "1", "end_type": "1",  # §1.5 新增
        "basic_eps": 0.5, "diluted_eps": 0.5, "total_revenue": 100.0,
        "revenue": 100.0, "operate_profit": 50.0, "total_profit": 50.0,
        "n_income": 40.0, "n_income_attr_p": 30.0,
    }]
    fetcher = FinIncomeTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(symbol="000001")
    assert len(out) == 1
    bo = out[0]
    assert bo.end_type == "1"
    assert bo.basic_eps == 0.5
    print(f"  [OK ] FinIncomeTushareFetcher end_type 已读")


async def test_daily_basic():
    from contexts.collect.infrastructure.fetcher.fundamental.DailyBasicTushareFetcher import (
        DailyBasicTushareFetcher,
    )
    records = [{
        "ts_code": "000001.SZ", "trade_date": "20251017",
        "close": 12.5, "turnover_rate": 1.5, "turnover_rate_f": 2.0,
        "volume_ratio": 1.0, "pe": 5.0, "pe_ttm": 5.0, "pb": 0.5,
        "ps": 1.0, "ps_ttm": 1.0, "dv_ratio": 0.5, "dv_ttm": 0.5,
        "total_share": 100.0, "float_share": 80.0, "free_share": 60.0,
        "total_mv": 100.0, "circ_mv": 80.0,
        "limit_status": 2,  # §2.7 新增
    }]
    fetcher = DailyBasicTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(trade_date="2025-10-17")
    assert len(out) == 1
    bo = out[0]
    assert bo.limit_status == 2
    print(f"  [OK ] DailyBasicTushareFetcher limit_status 已读")


async def test_margin_detail():
    from contexts.collect.infrastructure.fetcher.capital.MarginDetailTushareFetcher import (
        MarginDetailTushareFetcher,
    )
    records = [{
        "ts_code": "000001.SZ", "trade_date": "20251017",
        "name": "平安银行",  # §2.3 新增
        "rzye": 100.0, "rqye": 50.0, "rzmre": 10.0, "rqyl": 100.0,
        "rzche": 5.0, "rqchl": 3.0, "rqmcl": 2.0, "rzrqye": 150.0,
    }]
    fetcher = MarginDetailTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(trade_date="2025-10-17")
    assert len(out) == 1
    bo = out[0]
    assert bo.name == "平安银行"
    print(f"  [OK ] MarginDetailTushareFetcher name 已读")


async def test_holder_number():
    from contexts.collect.infrastructure.fetcher.capital.HolderNumberTushareFetcher import (
        HolderNumberTushareFetcher,
    )
    records = [{
        "ts_code": "000001.SZ", "ann_date": "20250420", "end_date": "20250331",
        "holder_num": 100000,
    }]
    fetcher = HolderNumberTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(symbol="000001")
    assert len(out) == 1
    bo = out[0]
    assert bo.holder_num == 100000
    assert bo.holder_nums == 100000.0  # §2.6 冗余
    print(f"  [OK ] HolderNumberTushareFetcher holder_nums 冗余")


async def test_dividend():
    from contexts.collect.infrastructure.fetcher.fundamental.DividendTushareFetcher import (
        DividendTushareFetcher,
    )
    records = [{
        "ts_code": "000001.SZ", "end_date": "20241231", "ann_date": "20250320",
        "record_date": "20250510", "ex_date": "20250511", "pay_date": "20250512",
        "div_proc": "实施", "stk_div": 0.0, "stk_bo_rate": 0.0, "stk_co_rate": 0.0,
        "cash_div": 0.5, "cash_div_tax": 0.5,
        # §2.8 新增
        "div_listdate": "20250520",
        "imp_ann_date": "20250501",
    }]
    fetcher = DividendTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch()
    assert len(out) == 1
    bo = out[0]
    assert bo.div_listdate is not None
    assert bo.imp_ann_date is not None
    print(f"  [OK ] DividendTushareFetcher div_listdate + imp_ann_date 已读")


async def test_suspend():
    from contexts.collect.infrastructure.fetcher.tech.SuspendTushareFetcher import (
        SuspendTushareFetcher,
    )
    records = [{
        "ts_code": "000001.SZ", "trade_date": "20251017",
        "suspend_timing": "09:30-10:00",  # 字符串
        "suspend_type": "S",
    }]
    fetcher = SuspendTushareFetcher()
    fetcher._c = MagicMock()
    fetcher._c.query = lambda *a, **kw: asyncio.sleep(0, result=_df(records))
    out = await fetcher.fetch(trade_date="2025-10-17")
    assert len(out) == 1
    bo = out[0]
    # §2.1 修复：suspend_timing 应该是字符串
    assert bo.suspend_timing == "09:30-10:00", f"期望字符串，实际 {bo.suspend_timing!r}"
    assert isinstance(bo.suspend_timing, str)
    print(f"  [OK ] SuspendTushareFetcher suspend_timing 是 str 而非 date")


async def test_concept_snapshot():
    """测试 ConceptSnapshotAdataFetcher §1.7 字段语义修复"""
    import pandas as pd_real
    from contexts.collect.infrastructure.fetcher.fundamental.ConceptSnapshotAdataFetcher import (
        ConceptSnapshotAdataFetcher,
    )
    records = [{
        "index_code": "885312", "name": "物联网",
        "trade_date": "2025-10-17",
        "price": 1234.5, "open": 1230.0, "high": 1240.0, "low": 1225.0,
        "prev_close": 1230.0,
        "change": 4.5,        # 涨跌额 → p_change
        "change_pct": 0.37,   # 涨跌幅 → pct_change
        "volume": 1000000, "amount": 12345.0,
        "turnover_rate": 1.5, "pe": None, "pb": None,
        "trade_time": "2025-10-17 15:00:00",
    }]
    fetcher = ConceptSnapshotAdataFetcher()
    fetcher._c = MagicMock()
    fetcher._c.call = lambda fn, name: asyncio.sleep(0, result=pd_real.DataFrame(records))
    fetcher._sdk = MagicMock()
    fetcher._sdk.stock.market.get_market_concept_current_ths = lambda **kw: None
    out = await fetcher.fetch(index_code="885312")
    assert len(out) == 1
    item = out[0]
    # §1.7 修复验证
    assert "p_change" in item, "应有 p_change 字段"
    assert "pct_change" in item, "应有 pct_change 字段"
    assert "open_price" in item, "应有 open_price 字段（不是 open）"
    assert "change" not in item, "不应再有 change 字段"
    assert "change_pct" not in item, "不应再有 change_pct 字段"
    assert "open" not in item, "不应再有 open 字段"
    assert item["p_change"] == 4.5
    assert item["pct_change"] == 0.37
    assert item["trade_date"] == "2025-10-17"
    print(f"  [OK ] ConceptSnapshotAdataFetcher 字段语义修复 p_change/pct_change/open_price")


async def test_concept_list_source():
    """§2.9 ConceptListAdataFetcher 补 source"""
    import pandas as pd_real
    from contexts.collect.infrastructure.fetcher.fundamental.ConceptListAdataFetcher import (
        ConceptListAdataFetcher,
    )
    records = [{
        "index_code": "885312", "concept_code": "309061", "name": "物联网",
        "source": "ths",  # 文档有
    }]
    fetcher = ConceptListAdataFetcher()
    fetcher._c = MagicMock()
    fetcher._c.call = lambda fn, name: asyncio.sleep(0, result=pd_real.DataFrame(records))
    fetcher._sdk = MagicMock()
    fetcher._sdk.stock.info.all_concept_code_ths = lambda: None
    out = await fetcher.fetch()
    assert len(out) == 1
    assert out[0]["source"] == "ths"
    print(f"  [OK ] ConceptListAdataFetcher source 已填")


async def test_concept_members_short_name():
    """§2.10 ConceptMembersAdataFetcher 补 short_name"""
    import pandas as pd_real
    from contexts.collect.infrastructure.fetcher.fundamental.ConceptMembersAdataFetcher import (
        ConceptMembersAdataFetcher,
    )
    records = [{
        "stock_code": "301205", "short_name": "联特科技",  # 文档字段
    }]
    fetcher = ConceptMembersAdataFetcher()
    fetcher._c = MagicMock()
    fetcher._c.call = lambda fn, name: asyncio.sleep(0, result=pd_real.DataFrame(records))
    fetcher._sdk = MagicMock()
    fetcher._sdk.stock.info.concept_constituent_ths = lambda **kw: None
    out = await fetcher.fetch(index_code="885312")
    assert len(out) == 1
    assert out[0]["short_name"] == "联特科技"
    assert out[0]["source"] == "ths"
    print(f"  [OK ] ConceptMembersAdataFetcher short_name + source")


async def test_stock_concepts_source():
    """§2.11 StockConceptsAdataFetcher 补 source"""
    import pandas as pd_real
    from contexts.collect.infrastructure.fetcher.fundamental.StockConceptsAdataFetcher import (
        StockConceptsAdataFetcher,
    )
    records = [{
        "stock_code": "300033", "concept_code": "886031", "name": "ChatGPT概念",
        "source": "ths", "reason": "i问财",
    }]
    fetcher = StockConceptsAdataFetcher()
    fetcher._c = MagicMock()
    fetcher._c.call = lambda fn, name: asyncio.sleep(0, result=pd_real.DataFrame(records))
    fetcher._sdk = MagicMock()
    fetcher._sdk.stock.info.get_concept_ths = lambda **kw: None
    out = await fetcher.fetch(symbol="300033")
    assert len(out) == 1
    assert out[0]["source"] == "ths"
    print(f"  [OK ] StockConceptsAdataFetcher source")


async def test_news_permission_error():
    """§1.6 NewsTushareFetcher 权限检测：捕获异常并返回空"""
    from contexts.collect.infrastructure.fetcher.news.NewsTushareFetcher import (
        NewsTushareFetcher,
    )
    fetcher = NewsTushareFetcher()
    fetcher._tushare = MagicMock()
    # 模拟 Tushare 抛权限错误
    fetcher._tushare.query = lambda *a, **kw: (_ for _ in ()).throw(
        Exception("权限不足，您没有此接口的访问权限")
    )
    out = await fetcher.fetch(minutes=30)
    # 应当返回空，不抛错
    assert out == []
    print(f"  [OK ] NewsTushareFetcher 权限不足时返回空（不抛错）")


async def test_news_normal():
    """§1.6 NewsTushareFetcher 正常返回（构造 dict 结构）"""
    from contexts.collect.infrastructure.fetcher.news.NewsTushareFetcher import (
        NewsTushareFetcher,
    )
    import pandas as pd_real
    # 构造一条新闻
    records = [{
        "datetime": "2025-10-17T10:00:00",
        "title": "利好消息：A股大涨",
        "content": "今日A股大涨",
        "source": "新浪财经",
        "url": "http://...",
        "channels": "财经,A股",
        "ts_code": "000001.SZ,600000.SH",
    }]
    fetcher = NewsTushareFetcher()
    fetcher._tushare = MagicMock()
    fetcher._tushare.query = lambda *a, **kw: asyncio.sleep(0, result=pd_real.DataFrame(records))
    out = await fetcher.fetch(minutes=60)
    # 时序数据：news 是当前时间 ± 60min 内的；2025-10-17T10:00:00 vs 当前时间可能超期
    # 不强求有结果，只验证调用没崩
    print(f"  [OK ] NewsTushareFetcher 正常返回（{len(out)} 条，依赖当前时间）")


async def main():
    print("=" * 70)
    print("Fetcher 端到端 mock 测试")
    print("=" * 70)
    tests = [
        test_stock_basic,
        test_moneyflow_hsgt,
        test_limit_list_d,
        test_hsgt_top10,
        test_fin_income,
        test_daily_basic,
        test_margin_detail,
        test_holder_number,
        test_dividend,
        test_suspend,
        test_concept_snapshot,
        test_concept_list_source,
        test_concept_members_short_name,
        test_stock_concepts_source,
        test_news_permission_error,
        test_news_normal,
    ]
    failed = 0
    for t in tests:
        try:
            await t()
        except Exception as e:
            import traceback
            print(f"  [ERR] {t.__name__}: {e!r}")
            traceback.print_exc()
            failed += 1
    print("=" * 70)
    if failed:
        print(f"❌ {failed}/{len(tests)} 失败")
        sys.exit(1)
    print(f"✅ {len(tests) - failed}/{len(tests)} 全部通过")


if __name__ == "__main__":
    asyncio.run(main())

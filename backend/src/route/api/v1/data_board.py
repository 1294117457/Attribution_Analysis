"""四数据面数据看板 API（业务模块：data-board/）

提供四个面（tech / capital / fundamental / news）的统一查询接口，
供前端 DataBoard.vue 单页面使用。

注意：
- 每个面返回的都是"按 symbol 维度"的查询
- 不做服务层封装，直接走 repo（简化路径，参考 stock.py 风格）
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response

from infrastructure.config.di import get_db
from infrastructure.persistence.repositories.kline_repository import KlineRepoImpl
from infrastructure.persistence.repositories.fin_daily_basic_repository import (
    FinDailyBasicRepoImpl,
)
from infrastructure.persistence.repositories.fin_report_repository import FinReportRepoImpl
from infrastructure.persistence.repositories.stock_repository import StockRepoImpl
from infrastructure.persistence.repositories.cap_moneyflow_repository import (
    CapMoneyflowRepoImpl,
)
from infrastructure.persistence.repositories.cap_margin_detail_repository import (
    CapMarginDetailRepoImpl,
)
from infrastructure.persistence.repositories.cap_top_list_repository import (
    CapTopListRepoImpl,
)
from infrastructure.persistence.repositories.cap_top_inst_repository import (
    CapTopInstRepoImpl,
)
from infrastructure.persistence.repositories.cap_block_trade_repository import (
    CapBlockTradeRepoImpl,
)
from infrastructure.persistence.repositories.cap_holder_num_repository import (
    CapHolderNumRepoImpl,
)
from infrastructure.persistence.repositories.fin_top10_holders_repository import (
    FinTop10HoldersRepoImpl,
)
from infrastructure.persistence.repositories.fin_top10_float_repository import (
    FinTop10FloatRepoImpl,
)
from infrastructure.persistence.repositories.base_dividend_repository import (
    BaseDividendRepoImpl,
)
from infrastructure.persistence.repositories.base_adj_factor_repository import (
    BaseAdjFactorRepoImpl,
)
from infrastructure.persistence.repositories.base_suspend_repository import (
    BaseSuspendRepoImpl,
)
from infrastructure.persistence.repositories.base_name_change_repository import (
    BaseNameChangeRepoImpl,
)
from route.api import _response as R
from domain.entitys.kline.vo import StockCode

router = APIRouter(prefix="/data-board", tags=["四数据面"])


# ═══════════════════════════════════════════════════════════════════════════════
#  ETag / 304 缓存（K线、adj_factor、suspend、name_change 准静态，免去重复传输）
# ═══════════════════════════════════════════════════════════════════════════════


def _iso(value) -> str | None:
    """把各种日期表示统一成 "YYYY-MM-DD" 字符串

    背景：本模块的 repo 返回值里日期字段有三种形态，直接调 .isoformat() 会炸：
      1. datetime.date / datetime.datetime  → 有 .isoformat()
      2. TradeDate 值对象（K线系列）        → 没有 .isoformat()，内层是 .date
      3. str                                → 原样返回（已是字符串）
    另外 None 也要安全返回 None。

    注意：datetime 是 date 的子类，所以必须先判 hasattr(x, "isoformat")，
    再回退到"取内层 .date"，否则 datetime 会被误当成值对象。
    """
    if value is None:
        return None
    # 1) 优先用原生 isoformat（date / datetime 都满足）
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    # 2) 值对象（TradeDate 等）：取内层 date 再来一轮
    inner = getattr(value, "date", None)
    if inner is not None and inner is not value:
        return _iso(inner)
    # 3) 值对象自带 to_string
    to_str = getattr(value, "to_string", None)
    if callable(to_str):
        return to_str()
    # 4) 兜底：字符串化
    return str(value) if value else None


def _etag_for(payload: dict) -> str:
    """对响应体做 SHA1 摘要，生成弱 ETag（仅看结构，不看微秒）"""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return 'W/"' + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16] + '"'


def _cached_response(if_none_match: Optional[str], body: dict) -> dict | Response:
    """ETag 协商：相同指纹 → 返回 304 Response（空体）；否则返回原 R.ok 包装

    用法：response = _cached_response(if_none_match, body); return response
    FastAPI 会自动处理 dict → JSON 序列化；Response 对象 → 直通。
    """
    payload = R.ok(body)  # 套上 {code, message, data} 包装
    etag = _etag_for(payload)
    if if_none_match and if_none_match.strip() == etag:
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": "private, max-age=60",
            },
        )
    return Response(
        content=json.dumps(payload, ensure_ascii=False, default=str),
        media_type="application/json",
        headers={
            "ETag": etag,
            "Cache-Control": "private, max-age=60",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  技术面 (tech)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/tech/kline/{symbol}", summary="技术面：日 K 线")
async def get_tech_kline(
    symbol: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(250, ge=10, le=3650),
    if_none_match: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    repo = KlineRepoImpl(db)
    try:
        sc = StockCode(code=symbol)
    except ValueError as e:
        raise HTTPException(400, str(e))
    rows = await repo.find_by_symbol(sc, start_date, end_date, limit=limit)
    payload = {
        "symbol": symbol,
        "klines": [
            {
                "trade_date": _iso(r.trade_date),
                "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                "volume": r.volume, "amount": r.amount,
                "change_pct": r.change_pct,
                "ma5": r.ma5, "ma10": r.ma10, "ma20": r.ma20, "ma60": r.ma60,
                "ema12": r.ema12, "ema26": r.ema26,
                "macd_dif": r.macd_dif, "macd_dea": r.macd_dea, "macd_bar": r.macd_bar,
                "rsi6": r.rsi6, "rsi12": r.rsi12, "rsi24": r.rsi24,
                "kdj_k": r.kdj_k, "kdj_d": r.kdj_d, "kdj_j": r.kdj_j,
                "boll_up": r.boll_up, "boll_mid": r.boll_mid, "boll_dn": r.boll_dn,
            }
            for r in rows
        ],
    }
    return _cached_response(if_none_match, payload)


@router.get("/tech/adj-factor/{symbol}", summary="技术面：复权因子")
async def get_adj_factor(
    symbol: str,
    limit: int = Query(500, ge=10, le=3650),
    if_none_match: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseAdjFactorRepoImpl(db)
    rows = await repo.find_by_symbol(symbol)
    payload = {
        "symbol": symbol,
        "factors": [
            {"trade_date": _iso(r.trade_date), "adj_factor": r.adj_factor}
            for r in rows[:limit]
        ],
    }
    return _cached_response(if_none_match, payload)


@router.get("/tech/suspend/{symbol}", summary="技术面：停复牌")
async def get_suspend(
    symbol: str,
    if_none_match: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseSuspendRepoImpl(db)
    rows = await repo.find_by_symbol(symbol)
    payload = {
        "symbol": symbol,
        "events": [
            {
                "trade_date": _iso(r.trade_date),
                "suspend_timing": _iso(r.suspend_timing),
                "suspend_type": r.suspend_type,
            }
            for r in rows
        ],
    }
    return _cached_response(if_none_match, payload)


@router.get("/tech/name-change/{symbol}", summary="技术面：股票曾用名")
async def get_name_change(
    symbol: str,
    if_none_match: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    repo = BaseNameChangeRepoImpl(db)
    rows = await repo.find_by_symbol(symbol)
    payload = {
        "symbol": symbol,
        "history": [
            {
                "name": r.name,
                "start_date": _iso(r.start_date),
                "end_date": _iso(r.end_date),
                "ann_date": _iso(r.ann_date),
                "change_reason": r.change_reason,
            }
            for r in rows
        ],
    }
    return _cached_response(if_none_match, payload)


# ═══════════════════════════════════════════════════════════════════════════════
#  资金面 (capital)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/capital/moneyflow/{symbol}", summary="资金面：资金流向")
async def get_moneyflow(
    symbol: str,
    days: int = Query(60, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    repo = CapMoneyflowRepoImpl(db)
    today = date.today()
    rows = await repo.find_by_symbol(
        symbol, start_date=today - timedelta(days=days), end_date=today,
    )
    return R.ok({
        "symbol": symbol,
        "days": days,
        "flows": [
            {
                "trade_date": _iso(r.trade_date),
                "buy_sm_amount": r.buy_sm_amount, "sell_sm_amount": r.sell_sm_amount,
                "buy_md_amount": r.buy_md_amount, "sell_md_amount": r.sell_md_amount,
                "buy_lg_amount": r.buy_lg_amount, "sell_lg_amount": r.sell_lg_amount,
                "buy_elg_amount": r.buy_elg_amount, "sell_elg_amount": r.sell_elg_amount,
                "net_mf_amount": r.net_mf_amount, "net_mf_vol": r.net_mf_vol,
            }
            for r in rows
        ],
    })


@router.get("/capital/margin/{symbol}", summary="资金面：融资融券")
async def get_margin(
    symbol: str,
    days: int = Query(60, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    repo = CapMarginDetailRepoImpl(db)
    today = date.today()
    rows = await repo.find_by_symbol(
        symbol, start_date=today - timedelta(days=days), end_date=today,
    )
    return R.ok({
        "symbol": symbol,
        "days": days,
        "details": [
            {
                "trade_date": _iso(r.trade_date),
                "rzye": r.rzye, "rqye": r.rqye, "rzrqye": r.rzrqye,
                "rzmre": r.rzmre, "rzche": r.rzche,
                "rqyl": r.rqyl, "rqmcl": r.rqmcl, "rqchl": r.rqchl,
            }
            for r in rows
        ],
    })


@router.get("/capital/top-list/{symbol}", summary="资金面：龙虎榜每日")
async def get_top_list(
    symbol: str,
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    repo = CapTopListRepoImpl(db)
    today = date.today()
    rows = await repo.find_by_symbol(
        symbol, start_date=today - timedelta(days=days), end_date=today,
    )
    return R.ok({
        "symbol": symbol,
        "days": days,
        "lists": [
            {
                "trade_date": _iso(r.trade_date),
                "name": r.name,
                "close": r.close, "pct_change": r.pct_change,
                "turnover_rate": r.turnover_rate, "amount": r.amount,
                "l_buy": r.l_buy, "l_sell": r.l_sell, "l_amount": r.l_amount,
                "net_amount": r.net_amount, "net_rate": r.net_rate,
                "amount_rate": r.amount_rate,
                "float_values": r.float_values,
                "reason": r.reason,
            }
            for r in rows
        ],
    })


@router.get("/capital/top-inst/{symbol}", summary="资金面：龙虎榜机构")
async def get_top_inst(
    symbol: str,
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    repo = CapTopInstRepoImpl(db)
    today = date.today()
    rows = await repo.find_by_symbol(
        symbol, start_date=today - timedelta(days=days), end_date=today,
    )
    return R.ok({
        "symbol": symbol,
        "days": days,
        "details": [
            {
                "trade_date": _iso(r.trade_date),
                "exalter": r.exalter, "side": r.side,
                "buy": r.buy, "buy_rate": r.buy_rate,
                "sell": r.sell, "sell_rate": r.sell_rate,
                "net_buy": r.net_buy, "reason": r.reason,
            }
            for r in rows
        ],
    })


@router.get("/capital/block-trade/{symbol}", summary="资金面：大宗交易")
async def get_block_trade(
    symbol: str,
    days: int = Query(180, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    repo = CapBlockTradeRepoImpl(db)
    today = date.today()
    rows = await repo.find_by_symbol(
        symbol, start_date=today - timedelta(days=days), end_date=today,
    )
    return R.ok({
        "symbol": symbol,
        "days": days,
        "trades": [
            {
                "trade_date": _iso(r.trade_date),
                "name": r.name,
                "price": r.price, "vol": r.vol, "amount": r.amount,
                "buyer": r.buyer, "seller": r.seller,
            }
            for r in rows
        ],
    })


@router.get("/capital/holder-num/{symbol}", summary="资金面：股东户数")
async def get_holder_num(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    repo = CapHolderNumRepoImpl(db)
    rows = await repo.find_by_symbol(symbol)
    return R.ok({
        "symbol": symbol,
        "history": [
            {
                "end_date": _iso(r.end_date),
                "ann_date": _iso(r.ann_date),
                "holder_num": r.holder_num,
                "holder_nums": r.holder_nums,
            }
            for r in rows
        ],
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  基本面 (fundamental)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/fundamental/stock/{symbol}", summary="基本面：股票基本信息")
async def get_stock_info(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    repo = StockRepoImpl(db)
    stock = await repo.find_by_symbol(symbol)
    if not stock:
        raise HTTPException(404, f"股票 {symbol} 不存在")
    return R.ok({
        "symbol": stock.symbol,
        "name": stock.name,
        "industry": stock.industry.name if stock.industry else None,
        "market": stock.market.name if stock.market else None,
        "exchange": stock.exchange,
        "area": stock.area,
        "list_date": _iso(stock.list_date),
        "delist_date": _iso(stock.delist_date),
        "list_status": stock.list_status,
        "is_hs": stock.is_hs,
        "act_name": stock.act_name,
    })


@router.get("/fundamental/daily-basic/{symbol}", summary="基本面：日频估值")
async def get_daily_basic(
    symbol: str,
    days: int = Query(60, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    repo = FinDailyBasicRepoImpl(db)
    today = date.today()
    rows = await repo.find_by_symbol(
        symbol, start_date=today - timedelta(days=days), end_date=today,
    )
    return R.ok({
        "symbol": symbol,
        "days": days,
        "valuation": [
            {
                "trade_date": _iso(r.trade_date),
                "close": r.close,
                "turnover_rate": r.turnover_rate,
                "turnover_rate_f": r.turnover_rate_f,
                "volume_ratio": r.volume_ratio,
                "pe": r.pe, "pe_ttm": r.pe_ttm,
                "pb": r.pb, "ps": r.ps, "ps_ttm": r.ps_ttm,
                "dv_ratio": r.dv_ratio, "dv_ttm": r.dv_ttm,
                "total_share": r.total_share,
                "float_share": r.float_share,
                "total_mv": r.total_mv, "circ_mv": r.circ_mv,
            }
            for r in rows
        ],
    })


@router.get("/fundamental/fin-report/{symbol}", summary="基本面：季报财务")
async def get_fin_report(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    repo = FinReportRepoImpl(db)
    rows = await repo.find_by_symbol(symbol)
    return R.ok({
        "symbol": symbol,
        "reports": [
            {
                "end_date": _iso(r.end_date),
                "ann_date": _iso(r.ann_date),
                "report_type": r.report_type,
                "basic_eps": r.basic_eps,
                "diluted_eps": r.diluted_eps,
                "total_revenue": r.total_revenue,
                "revenue": r.revenue,
                "operate_profit": r.operate_profit,
                "total_profit": r.total_profit,
                "n_income": r.n_income,
                "n_income_attr_p": r.n_income_attr_p,
                # 净利润率派生
                "net_margin": (
                    round(r.n_income / r.revenue * 100, 2)
                    if r.n_income is not None and r.revenue not in (None, 0)
                    else None
                ),
            }
            for r in rows
        ],
    })


@router.get("/fundamental/top10-holders/{symbol}", summary="基本面：前十大股东")
async def get_top10_holders(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    repo = FinTop10HoldersRepoImpl(db)
    rows = await repo.find_by_symbol(symbol)
    return R.ok({
        "symbol": symbol,
        "holders": [
            {
                "end_date": _iso(r.end_date),
                "ann_date": _iso(r.ann_date),
                "holder_name": r.holder_name,
                "hold_amount": r.hold_amount,
                "hold_ratio": r.hold_ratio,
                "hold_float_ratio": r.hold_float_ratio,
                "hold_change": r.hold_change,
                "holder_type": r.holder_type,
            }
            for r in rows
        ],
    })


@router.get("/fundamental/top10-float/{symbol}", summary="基本面：前十大流通股东")
async def get_top10_float(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    repo = FinTop10FloatRepoImpl(db)
    rows = await repo.find_by_symbol(symbol)
    return R.ok({
        "symbol": symbol,
        "holders": [
            {
                "end_date": _iso(r.end_date),
                "ann_date": _iso(r.ann_date),
                "holder_name": r.holder_name,
                "hold_amount": r.hold_amount,
                "hold_ratio": r.hold_ratio,
                "hold_change": r.hold_change,
                "holder_type": r.holder_type,
            }
            for r in rows
        ],
    })


@router.get("/fundamental/dividend/{symbol}", summary="基本面：分红送股")
async def get_dividend(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    repo = BaseDividendRepoImpl(db)
    rows = await repo.find_by_symbol(symbol)
    return R.ok({
        "symbol": symbol,
        "dividends": [
            {
                "end_date": _iso(r.end_date),
                "ann_date": _iso(r.ann_date),
                "record_date": _iso(r.record_date),
                "ex_date": _iso(r.ex_date),
                "pay_date": _iso(r.pay_date),
                "div_proc": r.div_proc,
                "stk_div": r.stk_div,
                "stk_bo_rate": r.stk_bo_rate,
                "stk_co_rate": r.stk_co_rate,
                "cash_div": r.cash_div,
                "cash_div_tax": r.cash_div_tax,
            }
            for r in rows
        ],
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  数据面板"综合看板"（按 symbol 一次拉四面的统计）
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/overview/{symbol}", summary="四数据面综合看板")
async def overview_panel(
    symbol: str,
    db: AsyncSession = Depends(get_db),
):
    """按 symbol 一次拉四面的关键统计（前端 DataBoard.vue 概览用）"""
    from sqlalchemy import func, select
    from infrastructure.persistence.models.tech_kline import TechKlineDailyDB
    from infrastructure.persistence.models.fin_daily_basic import FinDailyBasicDB
    from infrastructure.persistence.models.cap_moneyflow import CapMoneyflowDB
    from infrastructure.persistence.models.cap_margin_detail import CapMarginDetailDB
    from infrastructure.persistence.models.cap_top_list import CapTopListDB
    from infrastructure.persistence.models.cap_holder_num import CapHolderNumDB

    # 各表最新一条 + 条数
    async def _latest(model, col):
        r = await db.execute(
            select(func.max(getattr(model, col)))
            .where(getattr(model, "symbol") == symbol)
        )
        return r.scalar_one_or_none()

    async def _count(model):
        r = await db.execute(
            select(func.count()).select_from(model).where(model.symbol == symbol)
        )
        return r.scalar_one() or 0

    async def _latest_basic(model):
        # 拿 symbol + 当日数据
        today = date.today()
        rows = await FinDailyBasicRepoImpl(db).find_by_symbol(
            symbol, start_date=today - timedelta(days=5), end_date=today,
        )
        return rows[0] if rows else None

    # 注意：K线表（TechKlineDailyDB）的日期列是 `date`，其余表都是 `trade_date`。
    # 旧代码给 K 线传 "trade_date" 会抛 AttributeError 导致整个 /overview 500。
    kline_latest = await _latest(TechKlineDailyDB, "date")
    kline_count = await _count(TechKlineDailyDB)
    basic_latest = await _latest_basic(FinDailyBasicDB)
    mf_latest = await _latest(CapMoneyflowDB, "trade_date")
    mf_count = await _count(CapMoneyflowDB)
    margin_latest = await _latest(CapMarginDetailDB, "trade_date")
    margin_count = await _count(CapMarginDetailDB)
    top_count = await _count(CapTopListDB)
    holder_count = await _count(CapHolderNumDB)

    # 股票基本信息
    stock = await StockRepoImpl(db).find_by_symbol(symbol)

    return R.ok({
        "symbol": symbol,
        "stock": {
            "name": stock.name if stock else None,
            "industry": stock.industry.name if stock and stock.industry else None,
            "list_date": _iso(stock.list_date) if stock and stock.list_date else None,
        } if stock else None,
        "tech": {
            "kline_count": kline_count,
            "kline_latest_date": _iso(kline_latest),
        },
        "fundamental": {
            "latest_close": basic_latest.close if basic_latest else None,
            "latest_pe": basic_latest.pe if basic_latest else None,
            "latest_pb": basic_latest.pb if basic_latest else None,
            "latest_total_mv": basic_latest.total_mv if basic_latest else None,
            "latest_date": _iso(basic_latest.trade_date) if basic_latest else None,
        },
        "capital": {
            "moneyflow_latest_date": _iso(mf_latest),
            "moneyflow_count": mf_count,
            "margin_latest_date": _iso(margin_latest),
            "margin_count": margin_count,
            "top_list_count": top_count,
            "holder_count": holder_count,
        },
        "news": {
            "available": False,
            "message": "news_article 任务等待 tushare news 权限开通",
        },
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  数据面板"左侧股票列"（按 q 搜索 / 全量拉取 5000+ 只）
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/stock-list", summary="左侧股票列：模糊搜索（symbol/name/ts_code）")
async def stock_list(
    q: Optional[str] = Query(None, description="模糊匹配 symbol/name/ts_code"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页条数"),
    list_status: Optional[str] = Query("L", description="上市状态 L/D/P，空=全部"),
    db: AsyncSession = Depends(get_db),
):
    """DataBoard 左侧股票列专用端点（轻量字段）

    返回字段：symbol / name / industry / market / exchange / list_status
    默认只列出上市状态=L 的股票，模糊匹配 symbol / name / ts_code。
    """
    repo = StockRepoImpl(db)
    items, total = await repo.list_paginated(
        q=q, list_status=(list_status or None),
        page=page, page_size=page_size,
    )
    return R.ok({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "symbol": s.symbol,
                "name": s.name,
                "industry": s.industry.name if s.industry else None,
                "market": s.market.name if s.market else None,
                "exchange": s.exchange,
                "list_status": s.list_status,
            }
            for s in items
        ],
    })


@router.get("/stock-list-all", summary="左侧股票列：全量轻量列表（一次性 5000+ 只）")
async def stock_list_all(
    db: AsyncSession = Depends(get_db),
):
    """DataBoard 左侧股票列一次性全量拉取（轻量字段，无关联查询）

    设计目标：
    - 5000+ 只股票一次性返回，前端做本地过滤 / 缓存
    - 不带分页，不带关联（K 线/概念条目都在前几 Tab 内按 symbol 单查）
    - 内部按 symbol 排序，前端做虚拟滚动 / 分组都很方便
    """
    repo = StockRepoImpl(db)
    items, total = await repo.list_paginated(
        list_status="L", page=1, page_size=10000,
    )
    return R.ok({
        "total": total,
        "items": [
            {
                "symbol": s.symbol,
                "name": s.name,
                "industry": s.industry.name if s.industry else None,
                "market": s.market.name if s.market else None,
                "exchange": s.exchange,
            }
            for s in items
        ],
    })
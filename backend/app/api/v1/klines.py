"""
K 线数据 API 路由。
提供查询、添加 K 线数据的接口。
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from app.config import settings

router = APIRouter(prefix="/api/v1/klines", tags=["K线数据"])


# ============ 请求/响应模型 ============

class KLineResponse(BaseModel):
    id: int
    code: str
    name: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    change_pct: Optional[float]
    turnover_rate: Optional[float]


class KLineCreateRequest(BaseModel):
    code: str
    name: str
    date: str  # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    change_pct: Optional[float] = None
    turnover_rate: Optional[float] = None


# ============ 数据库操作函数 ============

def get_db():
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return engine


# ============ API 路由 ============

@router.get("", response_model=list[KLineResponse])
async def get_klines(
    code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询 K 线数据"""
    engine = get_db()

    # 拼装 WHERE 条件
    conditions = []
    params = {}

    if code:
        conditions.append("code = :code")
        params["code"] = code
    if start_date:
        conditions.append("date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("date <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT id, code, name, date, open, high, low, close, volume, amount, change_pct, turnover_rate
        FROM klines
        WHERE {where_clause}
        ORDER BY date DESC
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.fetchall()

    return [
        KLineResponse(
            id=row[0],
            code=row[1],
            name=row[2],
            date=str(row[3]),
            open=row[4],
            high=row[5],
            low=row[6],
            close=row[7],
            volume=row[8],
            amount=row[9],
            change_pct=row[10],
            turnover_rate=row[11],
        )
        for row in rows
    ]


@router.get("/{code}", response_model=list[KLineResponse])
async def get_kline_by_code(
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=1000),
):
    """根据股票代码查询 K 线"""
    engine = get_db()

    conditions = ["code = :code"]
    params = {"code": code, "limit": limit}

    if start_date:
        conditions.append("date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("date <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT id, code, name, date, open, high, low, close, volume, amount, change_pct, turnover_rate
        FROM klines
        WHERE {where_clause}
        ORDER BY date DESC
        LIMIT :limit
    """

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.fetchall()

    return [
        KLineResponse(
            id=row[0],
            code=row[1],
            name=row[2],
            date=str(row[3]),
            open=row[4],
            high=row[5],
            low=row[6],
            close=row[7],
            volume=row[8],
            amount=row[9],
            change_pct=row[10],
            turnover_rate=row[11],
        )
        for row in rows
    ]


@router.post("", response_model=dict)
async def create_kline(data: KLineCreateRequest):
    """添加单条 K 线数据"""
    engine = get_db()

    sql = """
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
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(sql), {
                "code": data.code,
                "name": data.name,
                "date": data.date,
                "open": data.open,
                "high": data.high,
                "low": data.low,
                "close": data.close,
                "volume": data.volume,
                "amount": data.amount,
                "change_pct": data.change_pct,
                "turnover_rate": data.turnover_rate,
            })
            conn.commit()

        return {"message": "OK", "code": data.code, "date": data.date}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{code}")
async def delete_klines(
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
):
    """删除 K 线数据"""
    engine = get_db()

    conditions = ["code = :code"]
    params = {"code": code}

    if start_date:
        conditions.append("date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("date <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(conditions)

    sql = f"DELETE FROM klines WHERE {where_clause}"

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        conn.commit()
        deleted = result.rowcount

    return {"message": "OK", "deleted": deleted}

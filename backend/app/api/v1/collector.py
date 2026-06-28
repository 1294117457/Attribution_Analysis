"""
采集模块 API 路由。
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.modules.collector.service import CollectorService
from app.modules.collector.schemas import BatchCollectionResult

router = APIRouter(prefix="/api/v1/collector", tags=["数据采集"])

# 服务实例
_collector_service: Optional[CollectorService] = None


def get_collector_service() -> CollectorService:
    global _collector_service
    if _collector_service is None:
        _collector_service = CollectorService()
    return _collector_service


# ============ 默认股票列表 ============

DEFAULT_STOCKS = [
    ("600519", "贵州茅台"),
    ("000858", "五粮液"),
    ("000001", "平安银行"),
    ("601318", "中国平安"),
    ("600036", "招商银行"),
    ("000333", "美的集团"),
    ("601318", "中国平安"),
    ("002594", "比亚迪"),
    ("300750", "宁德时代"),
    ("600887", "伊利股份"),
]


# ============ API 路由 ============

@router.post("/collect", response_model=dict)
async def collect_stock(
    code: str = Query(..., description="股票代码"),
    name: str = Query(..., description="股票名称"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
):
    """
    采集单只股票数据。
    """
    service = get_collector_service()
    result = service.collect_single(code, name, start_date, end_date)

    return {
        "code": result.code,
        "name": result.name,
        "collected": result.collected,
        "saved": result.saved,
        "success": result.success,
        "error": result.error,
    }


@router.post("/collect-batch", response_model=BatchCollectionResult)
async def collect_batch(
    codes: list[str] = Query(..., description="股票代码列表"),
    names: list[str] = Query(..., description="股票名称列表"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
):
    """
    批量采集多只股票数据。
    """
    if len(codes) != len(names):
        raise HTTPException(status_code=400, detail="codes 和 names 长度必须一致")

    stocks = list(zip(codes, names))
    service = get_collector_service()

    return service.collect_batch(stocks, start_date, end_date)


@router.post("/collect-default", response_model=BatchCollectionResult)
async def collect_default(
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
):
    """
    采集默认股票列表数据。
    """
    service = get_collector_service()
    return service.collect_batch(DEFAULT_STOCKS, start_date, end_date)


@router.post("/collect-index/{index_code}", response_model=BatchCollectionResult)
async def collect_index(
    index_code: str,  # 路径参数
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
):
    """
    采集某指数所有成分股数据。
    """
    service = get_collector_service()
    return service.collect_index(index_code, start_date, end_date)


@router.get("/index-components/{index_code}")
async def get_index_components(index_code: str):
    """
    获取指数成分股列表。
    """
    service = get_collector_service()
    components = service.get_index_components(index_code)

    return {
        "index_code": index_code,
        "count": len(components),
        "components": [{"code": c, "name": n} for c, n in components],
    }

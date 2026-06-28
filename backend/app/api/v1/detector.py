"""
异常检测 API 路由。
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.modules.detector.service import DetectorService

router = APIRouter(prefix="/api/v1/detectors", tags=["异常检测"])

# 服务实例
_detector_service: Optional[DetectorService] = None


def get_detector_service() -> DetectorService:
    global _detector_service
    if _detector_service is None:
        _detector_service = DetectorService()
    return _detector_service


# ============ API 路由 ============

@router.get("/detect")
async def detect_anomaly(
    code: str = Query(..., description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期 YYYY-MM-DD，默认最新日期"),
    lookback_days: int = Query(30, ge=10, le=120, description="回看天数"),
):
    """
    检测单只股票是否异常。
    """
    service = get_detector_service()
    result = service.detect(code, trade_date, lookback_days)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/batch-detect")
async def batch_detect_anomaly(
    codes: list[str] = Query(..., description="股票代码列表"),
    trade_date: Optional[str] = Query(None, description="交易日期 YYYY-MM-DD"),
):
    """
    批量检测多只股票异常。
    """
    service = get_detector_service()
    return service.detect_batch(codes, trade_date)


@router.get("/detectors")
async def list_detectors():
    """
    列出所有检测器。
    """
    service = get_detector_service()
    return {
        "detectors": service.get_detectors(),
        "count": len(service.get_detectors()),
    }

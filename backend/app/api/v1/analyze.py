"""分析服务 API"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.analyze_service import AnalyzeService

router = APIRouter()


@router.post("", response_model=AnalyzeResponse, summary="归因分析")
async def analyze(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
):
    """
    对指定股票进行归因分析

    - **symbol**: 股票代码，6位数字
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    - **analysis_type**: 分析类型（anomaly=仅异常检测, attribution=仅归因, full=完整）

    返回分析结果，包含异常检测和报告内容
    """
    service = AnalyzeService(db)
    result = await service.analyze(request.symbol, request.start_date, request.end_date)
    return result

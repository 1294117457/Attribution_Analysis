"""健康检查端点"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness_check():
    """就绪检查"""
    return {"status": "ready"}

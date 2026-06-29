"""健康检查 API"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "version": "1.0.0"}


@router.get("/ping")
def ping():
    """Ping"""
    return "pong"

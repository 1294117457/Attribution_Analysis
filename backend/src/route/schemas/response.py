"""统一 API 响应格式

所有 API 统一用此格式包装：
{ "code": 200, "message": "success", "data": ... }
"""

from typing import Any
from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "success") -> dict:
    """成功响应（200）"""
    return {"code": 200, "message": message, "data": data}


def created(data: Any = None, message: str = "创建成功") -> dict:
    """创建成功响应（201）"""
    return {"code": 201, "message": message, "data": data}


def no_content(message: str = "操作成功") -> dict:
    """无内容响应（200，data 为 null）"""
    return {"code": 200, "message": message, "data": None}


def err(message: str, code: int = 400) -> JSONResponse:
    """错误响应"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None},
    )


def bad_request(message: str) -> JSONResponse:
    return err(message, 400)


def not_found(message: str) -> JSONResponse:
    return err(message, 404)


def server_error(message: str = "服务器内部错误") -> JSONResponse:
    return err(message, 500)


def gateway_error(message: str) -> JSONResponse:
    return err(message, 502)

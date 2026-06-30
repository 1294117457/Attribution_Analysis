"""全局异常处理器"""

from app.handlers.http_errors import register_exception_handlers

__all__ = ["register_exception_handlers"]

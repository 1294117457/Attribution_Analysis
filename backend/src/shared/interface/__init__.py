"""shared.interface — 共享接口层（统一响应 + 分页 + router 聚合）

文件结构：
- _response.py: 统一 API 响应函数（原 route/api/_response.py）
- page.py: 通用分页 VO（前端分页请求/响应的载体）
- router_compat.py: 兼容层 API 聚合（原 route/api/router.py）

提供 `from shared.interface import _response as R` 兼容写法。
"""
from shared.interface import _response

# 为了让 route 层可以 `from shared.interface import _response as R`
# 需要把 _response 作为子模块从本包中导出
from shared.interface._response import (
    bad_request,
    created,
    err,
    gateway_error,
    no_content,
    not_found,
    ok,
    server_error,
)

__all__ = [
    "_response",
    "ok",
    "created",
    "no_content",
    "err",
    "bad_request",
    "not_found",
    "server_error",
    "gateway_error",
]

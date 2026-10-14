"""兼容层：聚合所有 context 的 router（从 route/api/router.py 迁移）

新结构：每个 context 暴露自己的 router，本模块按 03-依赖矩阵与启动序列.md §3.1
的顺序聚合：
  data → market → concept → user → auth → collect
"""
from fastapi import APIRouter

# 聚合各 context 的 router
api_router = APIRouter(prefix="/api/v1")

# 注意：每个 context 的 bootstrap.setup_xxx 也会再次 include_router，
# 但因为本文件只在 main.py 兼容期被导入，二选一即可

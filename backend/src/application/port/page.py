"""通用分页结果容器（应用层契约）

字段命名与前端 PaginatedResponse<T> 对齐：
items / total / page / page_size / pages

按 DDD.md §2.3：「application 层只暴露与领域/用例相关的协议和数据容器，
不依赖任何具体框架/传输层」。Page[T] 是应用层对"分页结果"的统一抽象，
可被 route 层直接复用序列化（因 Pydantic 本身只描述 schema，与 HTTP 无关）。
"""

from __future__ import annotations

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """泛型分页容器

    字段顺序与前端 PaginatedResponse<T> 1:1 对齐，
    便于后端返回后直接喂给前端的分页组件。
    """
    items: List[T] = Field(default_factory=list)
    total: int = Field(0, ge=0, description="总记录数")
    page: int = Field(1, ge=1, description="当前页码")
    page_size: int = Field(20, ge=1, description="每页条数")
    pages: int = Field(0, ge=0, description="总页数")

    @classmethod
    def from_list(
        cls,
        items: List[T],
        total: int,
        page_num: int,
        page_size: int,
    ) -> "Page[T]":
        """从 items + total 构造 Page，自动计算 pages

        pages 公式：ceil(total / page_size)，total=0 时为 0。
        """
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page_num,
            page_size=page_size,
            pages=pages,
        )

__all__ = ["Page"]
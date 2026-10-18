"""service/ — collect + query + 抽象（base/helpers）

service 是 application 层的核心：
  - service/collect/  写库的 service（按数据面分目录）
  - service/query/    实时查询的 service
  - base.py           CollectService Protocol / CollectResult / 错误类型

Service 同时实现 collect() + get()，两类方法同属一个 service。
本目录按 service 的"主要职责"分类，承载 collect() 较多的放 collect/，
主要提供 get() 实时查询的放 query/。
"""

from contexts.collect.application.service.base import (
    CollectResult,
    CollectService,
)

__all__ = [
    "CollectResult",
    "CollectService",
]

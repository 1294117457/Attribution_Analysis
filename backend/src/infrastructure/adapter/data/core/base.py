"""AdapterBase：实现方属性（谁来取、怎么限流）

Adapter 写成 `class XxxAdapter(XxxPort, AdapterBase)`；application 层看不到这些字段。
"""
from __future__ import annotations

from typing import ClassVar


class AdapterBase:
    tool: ClassVar[str] = ""                # 采集工具：tushare / adata / pytdx / akshare
    origin: ClassVar[str] = ""              # 数据源：tushare / ths / tdx / eastmoney
    priority: ClassVar[int] = 100           # 越小越优先
    throttle_group: ClassVar[str] = ""      # 限流分组，同组共享配额


ORIGIN_LABELS: dict[str, str] = {
    "tushare": "Tushare",
    "ths": "同花顺",
    "tdx": "通达信",
    "eastmoney": "东方财富",
}


__all__ = ["AdapterBase", "ORIGIN_LABELS"]

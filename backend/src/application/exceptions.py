"""应用层异常

应用层异常是业务层面的错误。
"""

from __future__ import annotations


class ApplicationError(Exception):
    """应用层异常基类"""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class KlineNotFoundError(ApplicationError):
    """K线不存在"""

    def __init__(self, symbol: str, date: str = None):
        if date:
            msg = f"股票 {symbol} 在 {date} 的K线不存在"
        else:
            msg = f"股票 {symbol} 的K线不存在"
        super().__init__(msg, "KLINE_NOT_FOUND")
        self.symbol = symbol


class StockNotFoundError(ApplicationError):
    """股票不存在"""

    def __init__(self, symbol: str):
        super().__init__(f"股票 {symbol} 不存在", "STOCK_NOT_FOUND")
        self.symbol = symbol


class KlineDataError(ApplicationError):
    """K线数据错误"""

    def __init__(self, symbol: str, reason: str):
        super().__init__(f"股票 {symbol} 数据错误: {reason}", "KLINE_DATA_ERROR")
        self.symbol = symbol


class CollectionError(ApplicationError):
    """数据采集错误"""

    def __init__(self, symbol: str, reason: str):
        super().__init__(f"采集股票 {symbol} 失败: {reason}", "COLLECTION_ERROR")
        self.symbol = symbol


# ── 操作池相关异常 ──────────────────────────────────────────────


class PoolNotFoundError(ApplicationError):
    def __init__(self, pool_id: int):
        self.pool_id = pool_id
        super().__init__(f"操作池不存在: {pool_id}", "POOL_NOT_FOUND")


class PoolOperationNotFoundError(ApplicationError):
    def __init__(self, op_id: int):
        self.op_id = op_id
        super().__init__(f"操作记录不存在: {op_id}", "POOL_OP_NOT_FOUND")


class CannotDeleteDefaultPoolError(ApplicationError):
    def __init__(self):
        super().__init__("无法删除默认池", "CANNOT_DELETE_DEFAULT_POOL")


class DuplicatePoolMemberError(ApplicationError):
    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"股票 {symbol} 已在该池中", "DUPLICATE_MEMBER")


class PoolMemberNotFoundError(ApplicationError):
    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"股票 {symbol} 不在该池中", "MEMBER_NOT_FOUND")


class PoolOperationConflictError(ApplicationError):
    def __init__(self, pool_id: int):
        self.pool_id = pool_id
        super().__init__(
            f"池 {pool_id} 已有进行中的操作，请等待完成后重试",
            "OPERATION_CONFLICT",
        )

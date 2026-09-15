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

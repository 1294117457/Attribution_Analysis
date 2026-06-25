"""数据查询工具（LangChain Tool）"""

from typing import List, Optional
from langchain_core.tools import tool

from app.db.session import SessionLocal
from app.models.kline import KLine


@tool(description="查询股票K线历史数据")
def query_klines(
    symbol: str,
    start_date: str,
    end_date: str,
    limit: int = 100,
) -> str:
    """
    查询指定股票指定日期范围的K线数据。

    Args:
        symbol: 股票代码，6位数字，如 "600519"
        start_date: 开始日期，格式 "YYYY-MM-DD"
        end_date: 结束日期，格式 "YYYY-MM-DD"
        limit: 最大返回条数，默认100条

    Returns:
        K线数据列表，包含日期、开盘价、收盘价、最高价、最低价、成交量等
    """
    db = SessionLocal()
    try:
        from datetime import date as date_type

        start = date_type.fromisoformat(start_date)
        end = date_type.fromisoformat(end_date)

        klines = (
            db.query(KLine)
            .filter(
                KLine.code == symbol,
                KLine.date >= start,
                KLine.date <= end,
            )
            .order_by(KLine.date.desc())
            .limit(limit)
            .all()
        )

        if not klines:
            return f"股票 {symbol} 在 {start_date} 至 {end_date} 期间无数据"

        lines = [f"股票 {symbol} K线数据（共 {len(klines)} 条）："]
        lines.append("-" * 80)
        lines.append(
            f"{'日期':<12} {'开盘':>10} {'收盘':>10} {'最高':>10} {'最低':>10} {'涨跌幅':>8} {'成交量':>12}"
        )
        lines.append("-" * 80)

        for k in klines:
            change_str = f"{k.change_pct:+.2f}%" if k.change_pct is not None else "-"
            lines.append(
                f"{str(k.date):<12} {k.open:>10.2f} {k.close:>10.2f} "
                f"{k.high:>10.2f} {k.low:>10.2f} {change_str:>8} {k.volume:>12,.0f}"
            )

        return "\n".join(lines)

    finally:
        db.close()


@tool(description="查询股票相关新闻")
def query_news(
    symbol: str,
    days: int = 7,
) -> str:
    """
    查询指定股票最近的新闻。

    Args:
        symbol: 股票代码，6位数字，如 "600519"
        days: 查询最近几天，默认7天

    Returns:
        新闻列表
    """
    # TODO: 实现新闻查询
    return f"查询到 {symbol} 最近 {days} 天新闻（功能开发中）"


@tool(description="计算股票技术指标")
def calculate_indicators(prices: List[float]) -> dict:
    """
    计算股票技术指标。

    Args:
        prices: 收盘价列表

    Returns:
        技术指标：MA5, MA10, MA20, 涨跌幅, 波动率等
    """
    if len(prices) < 5:
        return {"error": "数据不足，需要至少5条数据"}

    import statistics

    # 计算移动平均
    ma5 = sum(prices[-5:]) / 5
    ma10 = sum(prices[-10:]) / 10 if len(prices) >= 10 else None
    ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else None

    # 计算涨跌幅
    change_pct = (prices[-1] - prices[-2]) / prices[-2] * 100 if len(prices) >= 2 else 0

    # 计算波动率
    volatility = statistics.stdev(prices[-20:]) if len(prices) >= 20 else statistics.stdev(prices) if len(prices) > 1 else 0

    return {
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2) if ma10 else None,
        "ma20": round(ma20, 2) if ma20 else None,
        "change_pct": round(change_pct, 2),
        "volatility": round(volatility, 2),
        "latest_price": prices[-1],
        "data_count": len(prices),
    }

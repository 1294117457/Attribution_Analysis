"""异常检测节点"""

from typing import Literal, List
from datetime import date

from app.agents.state import AnomalyState
from app.agents.tools.query_tools import query_klines, query_news, calculate_indicators


def detect_anomaly(state: AnomalyState) -> AnomalyState:
    """
    异常检测节点

    1. 查询K线数据
    2. 计算技术指标
    3. 应用异常检测算法
    """
    symbol = state["symbol"]
    start_date = str(state["start_date"])
    end_date = str(state["end_date"])

    # 1. 查询K线数据
    kline_data = query_klines.invoke({
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "limit": 100
    })

    # 2. 提取价格列表（简化版，实际应解析 kline_data）
    # TODO: 解析 kline_data 获取价格列表
    prices = []  # 从 kline_data 解析

    # 3. 计算指标
    indicators = {}
    if prices:
        indicators = calculate_indicators.invoke({"prices": prices})

    # 4. 异常检测
    anomalies: List[dict] = []

    # 检测涨跌幅异常
    if indicators.get("change_pct"):
        change = indicators["change_pct"]
        if abs(change) > 10:
            severity = "high"
        elif abs(change) > 5:
            severity = "medium"
        elif abs(change) > 3:
            severity = "low"
        else:
            severity = None

        if severity:
            anomalies.append({
                "type": "price_change",
                "severity": severity,
                "value": change,
                "description": f"涨跌幅异常：{change:+.2f}%"
            })

    # 检测波动率异常
    if indicators.get("volatility") and indicators.get("ma20"):
        vol = indicators["volatility"]
        ma20 = indicators["ma20"]
        if vol > ma20 * 0.1:  # 波动率超过均价的 10%
            anomalies.append({
                "type": "high_volatility",
                "severity": "medium",
                "value": vol,
                "description": f"波动率异常偏高：{vol:.2f}"
            })

    return {
        **state,
        "klines": kline_data,
        "indicators": indicators,
        "anomalies": anomalies,
        "is_anomaly": len(anomalies) > 0
    }


def should_escalate(state: AnomalyState) -> Literal["generate_report", "__end__"]:
    """判断是否需要生成报告"""
    if state.get("is_anomaly", False):
        return "generate_report"
    return "__end__"


def generate_report(state: AnomalyState) -> AnomalyState:
    """
    生成异常报告节点

    TODO: 后续接入 LLM 生成自然语言报告
    """
    symbol = state["symbol"]
    anomalies = state.get("anomalies", [])
    indicators = state.get("indicators", {})

    # 构建报告
    report_lines = [f"# 异常检测报告\n"]
    report_lines.append(f"\n**股票代码**: {symbol}\n")
    report_lines.append(f"**分析日期**: {state['start_date']} 至 {state['end_date']}\n")

    if anomalies:
        report_lines.append(f"\n## 检测到 {len(anomalies)} 项异常\n")

        high_severity = [a for a in anomalies if a.get("severity") == "high"]
        medium_severity = [a for a in anomalies if a.get("severity") == "medium"]
        low_severity = [a for a in anomalies if a.get("severity") == "low"]

        if high_severity:
            report_lines.append("\n### 高风险异常\n")
            for a in high_severity:
                report_lines.append(f"- ⚠️ {a.get('description', '')}\n")

        if medium_severity:
            report_lines.append("\n### 中风险异常\n")
            for a in medium_severity:
                report_lines.append(f"- ⚡ {a.get('description', '')}\n")

        if low_severity:
            report_lines.append("\n### 低风险异常\n")
            for a in low_severity:
                report_lines.append(f"- ℹ️ {a.get('description', '')}\n")
    else:
        report_lines.append("\n## 未检测到明显异常\n")

    # 添加指标摘要
    if indicators:
        report_lines.append("\n## 技术指标摘要\n")
        report_lines.append(f"- 最新价格: {indicators.get('latest_price', 'N/A')}\n")
        report_lines.append(f"- MA5: {indicators.get('ma5', 'N/A')}\n")
        report_lines.append(f"- MA10: {indicators.get('ma10', 'N/A')}\n")
        report_lines.append(f"- MA20: {indicators.get('ma20', 'N/A')}\n")
        report_lines.append(f"- 涨跌幅: {indicators.get('change_pct', 'N/A'):+.2f}%\n")
        report_lines.append(f"- 波动率: {indicators.get('volatility', 'N/A')}\n")

    report_lines.append("\n## 建议\n")
    if anomalies:
        report_lines.append("建议结合市场环境和公司基本面进一步分析异常原因。\n")
    else:
        report_lines.append("当前行情走势平稳，无明显异常信号。\n")

    report = "".join(report_lines)

    return {**state, "report": report}

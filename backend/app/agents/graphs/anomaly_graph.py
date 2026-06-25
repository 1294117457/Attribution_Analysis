"""异常检测工作流图"""

from langgraph.graph import StateGraph, END

from app.agents.state import AnomalyState
from app.agents.nodes.anomaly_node import detect_anomaly, should_escalate, generate_report


def build_anomaly_graph() -> StateGraph:
    """
    构建异常检测工作流图

    工作流：
    start -> detect_anomaly -> should_escalate?
                                            |
                                            +-> [yes] -> generate_report -> end
                                            |
                                            +-> [no] -> end
    """
    workflow = StateGraph(AnomalyState)

    # 添加节点
    workflow.add_node("detect", detect_anomaly, name="异常检测")
    workflow.add_node("report", generate_report, name="生成报告")

    # 设置入口
    workflow.set_entry_point("detect")

    # 添加条件边
    workflow.add_conditional_edges(
        "detect",
        should_escalate,
        {
            "generate_report": "report",
            END: END,
        },
    )

    # 添加结束边
    workflow.add_edge("report", END)

    return workflow


# 编译工作流
anomaly_graph = build_anomaly_graph().compile()


async def run_anomaly_detection(
    symbol: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    运行异常检测

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        包含检测结果的字典
    """
    from datetime import date as date_type

    result = await anomaly_graph.ainvoke({
        "symbol": symbol,
        "start_date": date_type.fromisoformat(start_date),
        "end_date": date_type.fromisoformat(end_date),
        "klines": None,
        "indicators": None,
        "anomalies": [],
        "is_anomaly": False,
        "report": None,
        "error": None,
    })

    return {
        "symbol": result["symbol"],
        "start_date": str(result["start_date"]),
        "end_date": str(result["end_date"]),
        "is_anomaly": result.get("is_anomaly", False),
        "anomalies": result.get("anomalies", []),
        "indicators": result.get("indicators", {}),
        "report": result.get("report"),
        "error": result.get("error"),
    }

# Step 03: 条件分支和复杂流程

## 学习目标
掌握 LangGraph 的条件分支、循环、复杂流程控制

## 概念速览

```python
from typing import Literal

# 条件边
def decide(state):
    if condition:
        return "path_a"
    else:
        return "path_b"

workflow.add_conditional_edges(
    "decision_node",
    decide,
    {
        "path_a": "node_a",
        "path_b": "node_b"
    }
)
```

## 任务

### 任务 1: 基本条件分支

创建 `demo_03_conditional.py`：

```python
"""
条件分支示例
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class DecisionState(TypedDict):
    """决策状态"""
    value: int
    path: str
    messages: list[str]

def initial_node(state: DecisionState) -> dict:
    """初始化"""
    print(f">>> 初始节点，value = {state['value']}")
    return {"messages": state["messages"] + ["初始化完成"]}

def decide_path(state: DecisionState) -> Literal["positive", "negative", "zero"]:
    """决策函数 - 决定走哪个分支"""
    value = state["value"]
    
    print(f">>> 决策点，value = {value}")
    
    if value > 0:
        return "positive"
    elif value < 0:
        return "negative"
    else:
        return "zero"

def positive_path(state: DecisionState) -> dict:
    """正值路径"""
    print(">>> 正值路径")
    return {
        "path": "positive",
        "messages": state["messages"] + ["执行正值路径"]
    }

def negative_path(state: DecisionState) -> dict:
    """负值路径"""
    print(">>> 负值路径")
    return {
        "path": "negative",
        "messages": state["messages"] + ["执行负值路径"]
    }

def zero_path(state: DecisionState) -> dict:
    """零值路径"""
    print(">>> 零值路径")
    return {
        "path": "zero",
        "messages": state["messages"] + ["执行零值路径"]
    }

def create_decision_workflow():
    """创建决策工作流"""
    workflow = StateGraph(DecisionState)
    
    workflow.add_node("init", initial_node)
    workflow.add_node("positive", positive_path)
    workflow.add_node("negative", negative_path)
    workflow.add_node("zero", zero_path)
    
    workflow.add_edge(START, "init")
    workflow.add_edge("init", "decision")
    
    # 条件边
    workflow.add_conditional_edges(
        "init",  # 起始节点
        decide_path,  # 决策函数
        {
            "positive": "positive",
            "negative": "negative",
            "zero": "zero"
        }
    )
    
    workflow.add_edge("positive", END)
    workflow.add_edge("negative", END)
    workflow.add_edge("zero", END)
    
    return workflow.compile()

if __name__ == "__main__":
    print("=" * 50)
    print("条件分支示例")
    print("=" * 50)
    
    app = create_decision_workflow()
    
    # 测试三种情况
    for value in [10, -5, 0]:
        print(f"\n测试 value = {value}")
        result = app.invoke({"value": value, "path": "", "messages": []})
        print(f"最终路径: {result['path']}")
```

### 任务 2: 股票分析的条件分支

```python
"""
股票分析的条件分支
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class StockState(TypedDict):
    """股票分析状态"""
    stock_code: str
    price: float
    change_pct: float
    
    # 分析结果
    anomaly_detected: bool
    anomaly_reason: str
    
    # 报告
    report: str
    
    # 流程控制
    action_taken: str
    messages: list[str]

def fetch_data(state: StockState) -> dict:
    """获取数据"""
    print(f">>> 获取 {state['stock_code']} 的数据")
    return {
        "messages": state["messages"] + ["数据获取完成"]
    }

def analyze_anomaly(state: StockState) -> dict:
    """分析异常"""
    change = state["change_pct"]
    
    print(f">>> 分析异常，涨跌幅 = {change}%")
    
    if change > 10:
        detected = True
        reason = "涨幅超过10%，可能存在异常"
    elif change < -10:
        detected = True
        reason = "跌幅超过10%，可能存在异常"
    elif abs(change) > 5:
        detected = True
        reason = "涨跌幅超过5%，值得关注"
    else:
        detected = False
        reason = "涨跌幅正常"
    
    return {
        "anomaly_detected": detected,
        "anomaly_reason": reason,
        "messages": state["messages"] + [f"异常检测: {reason}"]
    }

def decide_action(state: StockState) -> Literal["alert", "log", "report"]:
    """决定后续动作"""
    if state["anomaly_detected"]:
        if abs(state["change_pct"]) > 10:
            return "alert"  # 需要紧急警报
        else:
            return "report"  # 生成报告
    else:
        return "log"  # 简单记录

def alert_action(state: StockState) -> dict:
    """发送警报"""
    print(">>> 🚨 发送紧急警报")
    return {
        "action_taken": "alert",
        "report": f"🚨 紧急警报：{state['stock_code']} 异常波动 {state['change_pct']}%",
        "messages": state["messages"] + ["已发送紧急警报"]
    }

def log_action(state: StockState) -> dict:
    """记录日志"""
    print(">>> 📝 记录日志")
    return {
        "action_taken": "log",
        "report": f"📝 {state['stock_code']} 正常，涨跌幅 {state['change_pct']}%",
        "messages": state["messages"] + ["已记录日志"]
    }

def generate_report(state: StockState) -> dict:
    """生成报告"""
    print(">>> 📊 生成分析报告")
    report = f"""
    {'='*40}
    股票分析报告
    {'='*40}
    股票代码: {state['stock_code']}
    当前价格: {state['price']}
    涨跌幅: {state['change_pct']}%
    
    异常检测: {'是' if state['anomaly_detected'] else '否'}
    异常原因: {state['anomaly_reason']}
    {'='*40}
    """
    return {
        "report": report,
        "messages": state["messages"] + ["报告已生成"]
    }

def create_stock_workflow():
    """创建股票分析工作流"""
    workflow = StateGraph(StockState)
    
    workflow.add_node("fetch", fetch_data)
    workflow.add_node("analyze", analyze_anomaly)
    workflow.add_node("alert", alert_action)
    workflow.add_node("log", log_action)
    workflow.add_node("report", generate_report)
    
    workflow.add_edge(START, "fetch")
    workflow.add_edge("fetch", "analyze")
    
    # 条件分支
    workflow.add_conditional_edges(
        "analyze",
        decide_action,
        {
            "alert": "alert",
            "log": "log",
            "report": "report"
        }
    )
    
    # alert 和 report 后都生成最终报告
    workflow.add_edge("alert", "report")
    workflow.add_edge("log", END)
    workflow.add_edge("report", END)
    
    return workflow.compile()

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("股票分析条件分支")
    print("=" * 50)
    
    app = create_stock_workflow()
    
    # 测试用例
    test_cases = [
        {"code": "600519", "price": 1500, "change": 12.5, "desc": "涨幅超10%"},
        {"code": "000858", "price": 150, "change": -8.0, "desc": "跌幅超5%但不到10%"},
        {"code": "600036", "price": 35, "change": 2.0, "desc": "正常涨跌"},
    ]
    
    for case in test_cases:
        print(f"\n{'='*40}")
        print(f"测试: {case['code']} - {case['desc']}")
        print("="*40)
        
        result = app.invoke({
            "stock_code": case["code"],
            "price": case["price"],
            "change_pct": case["change"],
            "anomaly_detected": False,
            "anomaly_reason": "",
            "report": "",
            "action_taken": "",
            "messages": []
        })
        
        print(f"\n执行的动作: {result['action_taken'] or 'N/A'}")
        print(f"报告:\n{result['report']}")
```

### 任务 3: 带循环的工作流

```python
"""
带循环的工作流
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class LoopState(TypedDict):
    """循环状态"""
    count: int
    max_count: int
    result: str
    messages: list[str]

def start(state: LoopState) -> dict:
    """开始"""
    print(f">>> 开始循环，最大次数: {state['max_count']}")
    return {"messages": state["messages"] + ["开始处理"]}

def process_item(state: LoopState) -> dict:
    """处理单个项目"""
    new_count = state["count"] + 1
    print(f">>> 处理第 {new_count} 项")
    return {
        "count": new_count,
        "result": state["result"] + f" → 第{new_count}项",
        "messages": state["messages"] + [f"处理第{new_count}项"]
    }

def should_continue(state: LoopState) -> Literal["process", "finish"]:
    """决定是否继续"""
    print(f">>> 检查是否继续: count={state['count']}, max={state['max_count']}")
    
    if state["count"] < state["max_count"]:
        return "process"
    return "finish"

def finish(state: LoopState) -> dict:
    """完成"""
    print(f">>> 完成处理，共处理 {state['count']} 项")
    return {
        "result": state["result"] + " → 完成",
        "messages": state["messages"] + ["处理完成"]
    }

def create_loop_workflow():
    """创建循环工作流"""
    workflow = StateGraph(LoopState)
    
    workflow.add_node("start", start)
    workflow.add_node("process", process_item)
    workflow.add_node("finish", finish)
    
    workflow.add_edge(START, "start")
    workflow.add_edge("start", "process")
    
    # 条件边：决定继续还是结束
    workflow.add_conditional_edges(
        "process",
        should_continue,
        {
            "process": "process",  # 继续循环
            "finish": "finish"    # 结束
        }
    )
    
    workflow.add_edge("finish", END)
    
    return workflow.compile()

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("带循环的工作流")
    print("=" * 50)
    
    app = create_loop_workflow()
    
    initial_state = {
        "count": 0,
        "max_count": 3,
        "result": "",
        "messages": []
    }
    
    result = app.invoke(initial_state)
    
    print(f"\n最终结果: {result['result']}")
    print(f"处理项数: {result['count']}")
```

## 运行

```bash
python demo_03_conditional.py
```

## 流程图

```
条件分支流程

START → fetch → analyze → decide_action
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
                   alert    report     log
                    ↓         ↓         ↓
                    └────┬────┘         ↓
                         ↓              END
                       report
                         ↓
                        END
```

## 下一步
阅读 `../docs/analysis/03_conditional_flows.md` 深入理解

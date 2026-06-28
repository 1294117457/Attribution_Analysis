# Step 02: StateGraph 基础 - 节点和边

## 学习目标
掌握 StateGraph 的基本用法：定义状态、添加节点、连接边

## 概念速览

```python
from langgraph.graph import StateGraph, START, END

# 1. 定义状态
class State(TypedDict):
    messages: list

# 2. 定义节点
def node_func(state):
    return {"messages": ["新消息"]}

# 3. 创建图
graph = StateGraph(State)

# 4. 添加节点
graph.add_node("node_name", node_func)

# 5. 添加边
graph.add_edge(START, "node_name")
graph.add_edge("node_name", END)

# 6. 编译运行
app = graph.compile()
result = app.invoke({"messages": []})
```

## 任务

### 任务 1: 最简单的工作流

创建 `demo_02_stategraph.py`：

```python
"""
LangGraph StateGraph 基础示例
"""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# ============ 1. 定义状态 ============
class SimpleState(TypedDict):
    """简单状态"""
    step: str
    data: str

# ============ 2. 定义节点函数 ============
def step_1(state: SimpleState) -> dict:
    """步骤1：获取数据"""
    print(">>> 步骤1: 获取数据")
    return {
        "step": "step_1_done",
        "data": "从数据库获取的股票数据"
    }

def step_2(state: SimpleState) -> dict:
    """步骤2：处理数据"""
    print(">>> 步骤2: 处理数据")
    original = state.get("data", "")
    return {
        "step": "step_2_done",
        "data": f"处理后的数据: {original}"
    }

def step_3(state: SimpleState) -> dict:
    """步骤3：生成报告"""
    print(">>> 步骤3: 生成报告")
    return {
        "step": "step_3_done",
        "data": state.get("data", "") + " | 报告已生成"
    }

# ============ 3. 创建工作流 ============
def create_workflow():
    """创建工作流"""
    # 创建状态图
    workflow = StateGraph(SimpleState)
    
    # 添加节点
    workflow.add_node("step_1", step_1)
    workflow.add_node("step_2", step_2)
    workflow.add_node("step_3", step_3)
    
    # 添加边（控制流程）
    workflow.add_edge(START, "step_1")  # 开始 → step_1
    workflow.add_edge("step_1", "step_2")  # step_1 → step_2
    workflow.add_edge("step_2", "step_3")  # step_2 → step_3
    workflow.add_edge("step_3", END)  # step_3 → 结束
    
    # 编译
    return workflow.compile()

# ============ 4. 运行 ============
if __name__ == "__main__":
    print("=" * 50)
    print("创建工作流...")
    app = create_workflow()
    
    print("\n运行工作流:")
    initial_state = {"step": "start", "data": ""}
    result = app.invoke(initial_state)
    
    print("\n最终状态:")
    for key, value in result.items():
        print(f"  {key}: {value}")
```

### 任务 2: 带消息历史的状态

```python
"""
带消息历史的工作流
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END, add_messages

# 带消息历史的状态
class ChatState(TypedDict):
    """聊天状态"""
    messages: Annotated[list, add_messages]  # 自动追加消息
    user_name: str

def process_message(state: ChatState) -> dict:
    """处理用户消息"""
    last_message = state["messages"][-1] if state["messages"] else ""
    print(f">>> 处理消息: {last_message}")
    
    # 模拟回复
    response = f"收到消息: {last_message}"
    return {"messages": [response]}

def analyze_sentiment(state: ChatState) -> dict:
    """分析情感"""
    messages = state["messages"]
    print(f">>> 分析 {len(messages)} 条消息的情感")
    
    sentiment = "正面" if len(messages) % 2 == 0 else "中性"
    return {"messages": [f"情感分析结果: {sentiment}"]}

def create_chat_workflow():
    """创建聊天工作流"""
    workflow = StateGraph(ChatState)
    
    workflow.add_node("process", process_message)
    workflow.add_node("analyze", analyze_sentiment)
    
    workflow.add_edge(START, "process")
    workflow.add_edge("process", "analyze")
    workflow.add_edge("analyze", END)
    
    return workflow.compile()

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("聊天工作流示例")
    print("=" * 50)
    
    app = create_chat_workflow()
    
    # 运行
    initial_state = {
        "messages": ["你好"],
        "user_name": "张三"
    }
    
    result = app.invoke(initial_state)
    
    print("\n消息历史:")
    for msg in result["messages"]:
        print(f"  - {msg}")
```

### 任务 3: 股票分析工作流

```python
"""
股票分析工作流
"""
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

class StockAnalysisState(TypedDict):
    """股票分析状态"""
    stock_code: str
    stock_name: str
    
    # 价格数据
    price_data: Optional[dict]
    price_source: str
    
    # 分析结果
    anomaly_detected: bool
    anomaly_reason: str
    anomaly_severity: str
    
    # 报告
    report: str
    
    # 消息
    messages: list[str]

def fetch_price_data(state: StockAnalysisState) -> dict:
    """获取股票价格数据"""
    code = state["stock_code"]
    print(f">>> 获取 {code} 的价格数据...")
    
    # 模拟数据
    mock_data = {
        "current": 150.0,
        "change": 2.5,
        "volume": 1000000,
        "history": [148, 149, 150, 152, 150]
    }
    
    return {
        "price_data": mock_data,
        "price_source": "akshare",
        "messages": state["messages"] + [f"已获取 {code} 的价格数据"]
    }

def detect_anomaly(state: StockAnalysisState) -> dict:
    """检测异常"""
    price_data = state.get("price_data", {})
    change = price_data.get("change", 0)
    
    print(f">>> 检测异常，涨跌: {change}%")
    
    # 简单异常检测
    if abs(change) > 5:
        anomaly_detected = True
        reason = f"涨跌幅度异常: {change}%"
        severity = "high" if abs(change) > 10 else "medium"
    else:
        anomaly_detected = False
        reason = "无异常"
        severity = "none"
    
    return {
        "anomaly_detected": anomaly_detected,
        "anomaly_reason": reason,
        "anomaly_severity": severity,
        "messages": state["messages"] + [f"异常检测完成: {reason}"]
    }

def generate_report(state: StockAnalysisState) -> dict:
    """生成报告"""
    code = state["stock_code"]
    price = state.get("price_data", {}).get("current", 0)
    change = state.get("price_data", {}).get("change", 0)
    anomaly = state["anomaly_detected"]
    
    report = f"""
    ====================
    股票分析报告
    代码: {code}
    名称: {state['stock_name']}
    当前价格: {price}元
    涨跌幅: {change}%
    ====================
    异常检测: {'有异常' if anomaly else '无异常'}
    异常原因: {state['anomaly_reason']}
    ====================
    """
    
    return {
        "report": report,
        "messages": state["messages"] + ["报告已生成"]
    }

def create_stock_workflow():
    """创建股票分析工作流"""
    workflow = StateGraph(StockAnalysisState)
    
    workflow.add_node("fetch_data", fetch_price_data)
    workflow.add_node("detect_anomaly", detect_anomaly)
    workflow.add_node("generate_report", generate_report)
    
    workflow.add_edge(START, "fetch_data")
    workflow.add_edge("fetch_data", "detect_anomaly")
    workflow.add_edge("detect_anomaly", "generate_report")
    workflow.add_edge("generate_report", END)
    
    return workflow.compile()

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("股票分析工作流")
    print("=" * 50)
    
    app = create_stock_workflow()
    
    initial_state: StockAnalysisState = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "price_data": None,
        "price_source": "",
        "anomaly_detected": False,
        "anomaly_reason": "",
        "anomaly_severity": "",
        "report": "",
        "messages": []
    }
    
    result = app.invoke(initial_state)
    
    print("\n最终报告:")
    print(result["report"])
```

## 运行

```bash
python demo_02_stategraph.py
```

## 关键点

| 组件 | 说明 |
|------|------|
| `StateGraph(SimpleState)` | 创建状态图 |
| `workflow.add_node("name", func)` | 添加节点 |
| `workflow.add_edge(A, B)` | 连接边（A → B） |
| `START` | 工作流入口 |
| `END` | 工作流出口 |
| `app.invoke(initial_state)` | 运行工作流 |

## 下一步
阅读 `../docs/analysis/02_stategraph_basics.md` 深入理解

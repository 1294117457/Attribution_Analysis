# 条件分支和复杂流程详解

## 一、条件边的基本语法

### add_conditional_edges

```python
workflow.add_conditional_edges(
    source_node,      # 起始节点
    routing_function,  # 路由函数
    path_map          # 路径映射
)
```

### 路由函数

```python
from typing import Literal

def route_function(state: State) -> Literal["path_a", "path_b", "path_c"]:
    """
    路由函数
    
    Args:
        state: 当前状态
    
    Returns:
        Literal: 要跳转的节点名称
    """
    if condition:
        return "path_a"
    elif other_condition:
        return "path_b"
    else:
        return "path_c"
```

### 路径映射

```python
path_map = {
    "path_a": "node_a",   # path_a → node_a
    "path_b": "node_b",   # path_b → node_b
    "path_c": "node_c"    # path_c → node_c
}
```

## 二、条件分支模式

### 模式1：二分支

```python
def should_proceed(state: State) -> Literal["continue", "stop"]:
    return "continue" if state["value"] > 0 else "stop"

workflow.add_conditional_edges(
    "check",
    should_proceed,
    {
        "continue": "process",
        "stop": END
    }
)
```

### 模式2：多分支

```python
def classify(state: State) -> Literal["a", "b", "c", "d"]:
    score = state["score"]
    if score >= 90:
        return "a"
    elif score >= 80:
        return "b"
    elif score >= 60:
        return "c"
    else:
        return "d"

workflow.add_conditional_edges(
    "grade",
    classify,
    {
        "a": "excellent",
        "b": "good",
        "c": "pass",
        "d": "fail"
    }
)
```

### 模式3：分类器

```python
def classify_anomaly(state: StockState) -> Literal["critical", "warning", "info"]:
    severity = state.get("severity", "info")
    confidence = state.get("confidence", 0.5)
    
    if severity == "critical" and confidence > 0.8:
        return "critical"
    elif severity in ["critical", "warning"]:
        return "warning"
    else:
        return "info"

workflow.add_conditional_edges(
    "analyze",
    classify_anomaly,
    {
        "critical": "emergency_alert",
        "warning": "notify",
        "info": "log"
    }
)
```

## 三、循环工作流

### 基本循环

```
START → process → should_continue → END
              ↑                     ↓
              └─────── continue ────┘
```

```python
def should_continue(state: LoopState) -> Literal["process", "end"]:
    if state["count"] < state["max_count"]:
        return "process"  # 继续循环
    return "end"          # 退出循环

workflow.add_conditional_edges(
    "process",
    should_continue,
    {
        "process": "process",  # 回到 process
        "end": END             # 结束
    }
)
```

### 带退出条件的循环

```python
def should_retry(state: RetryState) -> Literal["retry", "success", "fail"]:
    if state["attempts"] >= state["max_attempts"]:
        return "fail"
    
    if state["success"]:
        return "success"
    
    return "retry"

workflow.add_conditional_edges(
    "attempt",
    should_retry,
    {
        "retry": "attempt",
        "success": "report",
        "fail": "error_handler"
    }
)
```

## 四、复杂流程示例

### 股票分析工作流

```python
from typing import TypedDict, Literal

class StockAnalysisState(TypedDict):
    stock_code: str
    price_data: dict | None
    sentiment_data: dict | None
    news_data: list | None
    
    anomaly_detected: bool
    anomaly_score: float
    sentiment: str
    
    report: str
    needs_alert: bool
    messages: list[str]

def fetch_all_data(state: StockAnalysisState) -> dict:
    """并行获取所有数据"""
    # 模拟并行获取
    return {
        "price_data": {"change": 5.2},
        "sentiment_data": {"score": 0.7},
        "news_data": [{"title": "利好消息"}],
        "messages": ["数据获取完成"]
    }

def analyze_price(state: StockAnalysisState) -> dict:
    """分析价格异常"""
    change = state["price_data"]["change"]
    anomaly = abs(change) > 5
    return {
        "anomaly_detected": anomaly,
        "anomaly_score": abs(change),
        "messages": ["价格分析完成"]
    }

def analyze_sentiment(state: StockAnalysisState) -> dict:
    """分析情感"""
    score = state["sentiment_data"]["score"]
    sentiment = "positive" if score > 0.5 else "negative"
    return {
        "sentiment": sentiment,
        "messages": ["情感分析完成"]
    }

def decide_alert(state: StockAnalysisState) -> Literal["alert", "report"]:
    """决定是否需要警报"""
    # 多条件组合判断
    anomaly = state["anomaly_detected"]
    sentiment = state["sentiment"]
    
    if anomaly and sentiment == "negative":
        return "alert"  # 异常 + 负面情感 = 紧急
    elif anomaly:
        return "alert"  # 异常就要警报
    return "report"

def create_report(state: StockAnalysisState) -> dict:
    """生成报告"""
    return {
        "report": f"股票 {state['stock_code']} 分析完成",
        "messages": ["报告生成完成"]
    }

def send_alert(state: StockAnalysisState) -> dict:
    """发送警报"""
    return {
        "needs_alert": True,
        "messages": ["警报已发送"]
    }

# 创建工作流
workflow = StateGraph(StockAnalysisState)

workflow.add_node("fetch", fetch_all_data)
workflow.add_node("analyze_price", analyze_price)
workflow.add_node("analyze_sentiment", analyze_sentiment)
workflow.add_node("decide", decide_alert)
workflow.add_node("report", create_report)
workflow.add_node("alert", send_alert)

# 顺序：fetch → 分析
workflow.add_edge(START, "fetch")
workflow.add_edge("fetch", "analyze_price")
workflow.add_edge("fetch", "analyze_sentiment")  # 并行

# 条件分支
workflow.add_conditional_edges(
    "decide",
    decide_alert,
    {
        "alert": "alert",
        "report": "report"
    }
)

workflow.add_edge("alert", END)
workflow.add_edge("report", END)
```

## 五、并行与收敛

### 并行分支

```python
# START 同时触发多个节点
workflow.add_edge(START, "task_a")
workflow.add_edge(START, "task_b")
workflow.add_edge(START, "task_c")

# 收敛：所有分支完成后汇聚
workflow.add_edge("task_a", "aggregate")
workflow.add_edge("task_b", "aggregate")
workflow.add_edge("task_c", "aggregate")
workflow.add_edge("aggregate", END)
```

### 带条件的并行

```python
def should_parallel(state: State) -> Literal["parallel", "sequential"]:
    return "parallel" if state["mode"] == "fast" else "sequential"

workflow.add_conditional_edges(
    "init",
    should_parallel,
    {
        "parallel": "parallel_node",
        "sequential": "sequential_node"
    }
)
```

## 六、中断点

```python
# 编译时设置中断点
app = workflow.compile(
    interrupt_before=["alert"],   # alert 之前中断
    interrupt_after=["analyze"]   # analyze 之后中断
)

# 运行
result = app.invoke(initial_state)
# 在 interrupt_before 处暂停

# 检查状态
snapshot = app.get_state(config)
print(snapshot.values)

# 继续执行
result = app.invoke({"action": "proceed"}, config)
```

### 使用场景

```python
# 1. 人工审批
app = workflow.compile(
    interrupt_before=["send_alert"]  # 发送警报前等待人工确认
)

# 2. 调试
app = workflow.compile(
    interrupt_after=["process"]  # 处理后中断查看结果
)

# 3. 外部确认
app = workflow.compile(
    interrupt_before=["execute_trade"]  # 执行交易前等待确认
)
```

## 七、状态持久化

```python
from langgraph.checkpoint.memory import MemorySaver

# 创建检查点
checkpointer = MemorySaver()

# 编译时添加检查点
app = workflow.compile(checkpointer=checkpointer)

# 线程配置
config = {"configurable": {"thread_id": "user_123"}}

# 运行
result = app.invoke(initial_state, config)

# 获取当前状态
snapshot = app.get_state(config)
print(snapshot.values)

# 更新状态后继续
app.update_state(config, {"new_field": "value"})
result = app.invoke(None, config)
```

## 八、错误处理

```python
from langgraph.errors import NodeInterrupt

def process(state: State) -> dict:
    try:
        return do_something(state)
    except ValueError as e:
        raise NodeInterrupt(f"处理失败: {e}")

def handle_error(state: State) -> dict:
    return {"error": str(e), "recovered": True}

workflow.add_node("process", process)
workflow.add_node("error_handler", handle_error)

workflow.add_edge(START, "process")
workflow.add_edge("process", END)
```

## 九、可视化

```python
# 导出为图片
app = workflow.compile()
graph = app.get_graph()

# 导出为 Mermaid 格式
mermaid_code = graph.draw_mermaid()

# 导出为 PNG
try:
    png_data = graph.draw_mermaid_png()
    with open("workflow.png", "wb") as f:
        f.write(png_data)
except Exception as e:
    print(f"无法生成图片: {e}")
    print("Mermaid 代码:")
    print(mermaid_code)
```

## 十、最佳实践

### 1. 清晰的节点命名

```python
# ❌ 不好
workflow.add_node("node1", func_a)
workflow.add_node("node2", func_b)

# ✅ 好
workflow.add_node("fetch_stock_data", fetch_data)
workflow.add_node("analyze_anomaly", analyze)
```

### 2. 状态字段组织

```python
class State(TypedDict):
    # 输入
    user_input: str
    
    # 处理结果
    data: dict
    analysis: dict
    
    # 输出
    result: str
    
    # 元数据
    messages: list[str]
    errors: list[str]
```

### 3. 条件分支不要太深

```python
# ❌ 不好：嵌套太深
def route(state):
    if a:
        if b:
            if c:
                return "x"
            return "y"
        return "z"
    return "default"

# ✅ 好：扁平化
def route(state):
    if not a:
        return "default"
    if not b:
        return "z"
    if c:
        return "x"
    return "y"
```

## 练习题

1. 创建股票评分工作流：获取数据 → 评分 → 分类（A/B/C/D）→ 对应处理
2. 创建重试工作流：尝试 → 失败？→ 重试（最多3次）→ 成功/失败
3. 创建并行工作流：同时获取价格、新闻、成交量 → 汇总分析
4. 创建带中断的工作流：在发送警报前等待人工确认
5. 创建完整股票分析工作流，包含多条件分支和循环

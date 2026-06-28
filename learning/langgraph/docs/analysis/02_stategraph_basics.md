# StateGraph 基础详解

## 一、StateGraph 工作流程

```
创建 StateGraph 的步骤

1. 定义 State
   └── 定义工作流中的数据结构

2. 定义 Node（节点）
   └── 编写处理函数

3. 添加 Node
   └── graph.add_node("name", function)

4. 添加 Edge（边）
   └── graph.add_edge(A, B)  # A → B

5. 编译
   └── app = graph.compile()

6. 运行
   └── result = app.invoke(initial_state)
```

## 二、状态定义

### 基本状态

```python
from typing import TypedDict

class State(TypedDict):
    """基本状态"""
    name: str
    value: int
    items: list[str]
    result: str | None  # 可选字段
```

### 带默认值的状态

```python
class State(TypedDict, total=False):
    """可选字段"""
    name: str  # 必需字段
    value: int | None  # 可选字段
```

### Annotated 状态

```python
from typing import Annotated, TypedDict
from langgraph.graph import add_messages

class ChatState(TypedDict):
    """带特殊行为的状态"""
    
    # add_messages 会自动追加，而不是替换
    messages: Annotated[list, add_messages]
    
    # 其他普通字段
    user_id: str
```

## 三、节点函数

### 基本结构

```python
def node_function(state: State) -> dict:
    """
    节点函数
    
    Args:
        state: 当前状态（只读）
    
    Returns:
        dict: 要更新的状态字段
    """
    # 读取状态
    current_value = state["name"]
    
    # 处理逻辑
    result = do_something(current_value)
    
    # 返回要更新的字段
    return {
        "result": result,
        "messages": ["处理完成"]
    }
```

### 节点函数的返回值

```python
# 返回值会合并到状态中
def node_a(state: State):
    return {"value": 10}

# 初始状态: {"value": 0, "name": ""}
# 节点执行后: {"value": 10, "name": ""}
```

### Annotated 字段的处理

```python
from langgraph.graph import add_messages

# 使用 Annotated[list, add_messages] 时
def node_a(state: ChatState):
    return {"messages": ["消息 A"]}

def node_b(state: ChatState):
    return {"messages": ["消息 B"]}

# 结果：
# state["messages"] = ["消息 A", "消息 B"]
# 而不是覆盖！
```

## 四、边（Edge）

### 基本边

```python
from langgraph.graph import START, END

workflow = StateGraph(State)

# START：工作流入口
workflow.add_edge(START, "node_a")

# END：工作流出口
workflow.add_edge("node_c", END)

# 普通边：顺序连接
workflow.add_edge("node_a", "node_b")
workflow.add_edge("node_b", "node_c")
```

### 边的工作方式

```
START → node_a → node_b → node_c → END

执行顺序：
1. 从 START 开始
2. 进入 node_a
3. 从 node_a 的边进入 node_b
4. 从 node_b 的边进入 node_c
5. 从 node_c 的边进入 END
```

## 五、条件边

### 条件边基础

```python
from typing import Literal
from langgraph.graph import StateGraph, START, END

def decide_branch(state: State) -> Literal["node_a", "node_b"]:
    """决定走哪个分支"""
    if state["value"] > 10:
        return "node_a"
    else:
        return "node_b"

workflow = StateGraph(State)

workflow.add_node("node_a", node_a_func)
workflow.add_node("node_b", node_b_func)
workflow.add_node("decision", decide_func)

# 条件边
workflow.add_conditional_edges(
    "decision",  # 起始节点
    decide_branch,  # 决策函数
    {
        "node_a": "node_a",  # 返回 "node_a" 时 → node_a
        "node_b": "node_b"   # 返回 "node_b" 时 → node_b
    }
)

workflow.add_edge(START, "decision")
workflow.add_edge("node_a", END)
workflow.add_edge("node_b", END)
```

### 决策函数签名

```python
from typing import Literal

def decision_function(state: State) -> Literal["path_a", "path_b", "path_c"]:
    """
    决策函数
    
    Args:
        state: 当前状态
    
    Returns:
        Literal: 要跳转的节点名称
    """
    # 决策逻辑
    if condition_a:
        return "path_a"
    elif condition_b:
        return "path_b"
    else:
        return "path_c"
```

## 六、实战：股票分析工作流

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class StockState(TypedDict):
    """股票分析状态"""
    stock_code: str
    price_data: dict | None
    anomaly_detected: bool
    report: str
    messages: list[str]

def fetch_data(state: StockState) -> dict:
    """获取数据"""
    return {
        "price_data": {"current": 150.0, "change": 3.5},
        "messages": ["数据获取完成"]
    }

def detect_anomaly(state: StockState) -> dict:
    """检测异常"""
    change = state["price_data"]["change"]
    detected = abs(change) > 5
    return {
        "anomaly_detected": detected,
        "messages": ["异常检测完成"]
    }

def alert(state: StockState) -> dict:
    """发送警报"""
    return {
        "messages": ["已发送异常警报"]
    }

def generate_report(state: StockState) -> dict:
    """生成报告"""
    return {
        "report": f"股票 {state['stock_code']} 分析完成",
        "messages": ["报告生成完成"]
    }

def should_alert(state: StockState) -> Literal["alert", "report"]:
    """决定是否需要警报"""
    if state["anomaly_detected"]:
        return "alert"
    return "report"

# 创建工作流
workflow = StateGraph(StockState)

workflow.add_node("fetch", fetch_data)
workflow.add_node("detect", detect_anomaly)
workflow.add_node("alert", alert)
workflow.add_node("report", generate_report)

workflow.add_edge(START, "fetch")
workflow.add_edge("fetch", "detect")

# 条件分支
workflow.add_conditional_edges(
    "detect",
    should_alert,
    {
        "alert": "alert",
        "report": "report"
    }
)

workflow.add_edge("alert", "report")
workflow.add_edge("report", END)

app = workflow.compile()

# 运行
result = app.invoke({
    "stock_code": "600519",
    "price_data": None,
    "anomaly_detected": False,
    "report": "",
    "messages": []
})
```

## 七、并行节点

```python
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(State)

# 添加并行节点
workflow.add_node("fetch_price", fetch_price)
workflow.add_node("fetch_news", fetch_news)
workflow.add_node("fetch_volume", fetch_volume)

workflow.add_node("aggregate", aggregate)

# START → 三个并行节点
workflow.add_edge(START, "fetch_price")
workflow.add_edge(START, "fetch_news")
workflow.add_edge(START, "fetch_volume")

# 三个节点 → aggregate
workflow.add_edge("fetch_price", "aggregate")
workflow.add_edge("fetch_news", "aggregate")
workflow.add_edge("fetch_volume", "aggregate")

workflow.add_edge("aggregate", END)
```

## 八、编译和运行

### 编译

```python
# 简单编译
app = workflow.compile()

# 带检查点
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# 带配置
app = workflow.compile(
    interrupt_before=["alert"],  # 在 alert 之前中断
    interrupt_after=["detect"]   # 在 detect 之后中断
)
```

### 运行

```python
# 单次运行
result = app.invoke(initial_state)

# 流式运行
for chunk in app.stream(initial_state):
    print(chunk)

# 带配置运行
config = {"configurable": {"thread_id": "user_123"}}
result = app.invoke(initial_state, config)
```

## 九、调试技巧

### 打印状态

```python
def debug_node(state: State) -> dict:
    print(f"进入节点，当前状态: {state}")
    result = do_something(state)
    print(f"节点执行后: {result}")
    return result
```

### 可视化

```python
# 生成图片
app = workflow.compile()
image = app.get_graph().draw_mermaid_png()
with open("workflow.png", "wb") as f:
    f.write(image)
```

## 十、常见问题

### 1. 节点返回值

```python
# ❌ 错误：返回整个状态
def node_a(state: State):
    return state  # 不要这样做！

# ✅ 正确：返回要更新的字段
def node_a(state: State):
    return {"new_field": "value"}
```

### 2. 状态不可变

```python
# ❌ 错误：直接修改状态
def node_a(state: State):
    state["value"] = 10  # 不要这样做！
    return {}

# ✅ 正确：返回更新
def node_a(state: State):
    return {"value": 10}
```

### 3. 循环处理

```python
# LangGraph 支持循环，但要设置最大迭代次数
from langgraph.constants import Interrupt

def should_continue(state: State) -> bool:
    return state["iterations"] < 10

workflow.add_conditional_edges(
    "process",
    should_continue,
    {
        True: "process",
        False: END
    }
)
```

## 练习题

1. 创建一个三步的顺序工作流
2. 创建一个带条件分支的工作流
3. 创建一个带消息历史的工作流
4. 创建一个并行执行的工作流
5. 创建股票分析工作流：获取数据 → 分析 → 异常检测 → 报告

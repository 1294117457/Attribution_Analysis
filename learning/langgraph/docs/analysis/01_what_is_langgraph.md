# 什么是 LangGraph 详解

## 一、为什么需要 LangGraph？

### LLM 应用的困境

```python
# 场景：分析股票并生成报告

# ❌ 普通方式：所有逻辑塞到一个 Prompt
prompt = """
你是一个股票分析师。请：
1. 获取股票数据
2. 分析价格趋势
3. 检测异常
4. 生成报告
[大量数据]
"""

response = llm.invoke(prompt)
# 问题：
# - 上下文长度限制
# - 无法获取实时数据
# - 无法处理复杂逻辑
# - 无法中途干预
```

### LangGraph 的解决方案

```
传统 LLM                      LangGraph
┌─────────────┐              ┌─────────────────────┐
│ User Input  │              │ User Input           │
└──────┬──────┘              └──────────┬──────────┘
       │                              │
       ▼                              ▼
┌─────────────┐              ┌─────────────────────┐
│   Single    │              │ ┌─────┐   ┌──────┐ │
│   Prompt    │              │ │Fetch│──▶│Parse │ │
│             │              │ └──┬──┘   └──┬───┘ │
└──────┬──────┘              │    │         │     │
       │                     │    ▼         ▼     │
       ▼                     │ ┌─────────┐  │    │
┌─────────────┐              │ │Analyze │◀──┘    │
│   Output    │              │ └──┬────┘         │
└─────────────┘              │    │              │
                            │ ┌──┴────────────┐ │
                            │ │Conditional   │ │
                            │ │Branch       │ │
                            │ └──┬─────┬─────┘ │
                            │    │     │       │
                            │    ▼     ▼       │
                            │ ┌─────┐ ┌─────┐  │
                            │ │Alert│ │Report│  │
                            │ └─────┘ └─────┘  │
                            └─────────────────────┘
```

## 二、LangGraph 核心概念

### 1. State（状态）

状态是工作流中流动的数据：

```python
from typing import TypedDict

class StockState(TypedDict):
    """股票分析状态"""
    
    # 输入字段
    stock_code: str
    stock_name: str
    
    # 中间结果
    price_history: list[dict]
    anomaly_scores: list[float]
    
    # 输出结果
    anomaly_detected: bool
    report: str
    
    # 元数据
    messages: list[str]
    error: str | None
```

### 2. Node（节点）

节点是执行特定任务的函数：

```python
from langgraph.graph import StateGraph

# 节点函数签名：输入 State，返回 State 更新
def fetch_price_data(state: StockState) -> dict:
    """
    获取股票价格数据
    
    Args:
        state: 当前状态（只读）
    
    Returns:
        dict: 要更新的状态字段
    """
    code = state["stock_code"]
    
    # 获取数据（伪代码）
    price_data = fetch_from_api(code)
    
    # 返回要更新的字段
    return {
        "price_history": price_data,
        "messages": state["messages"] + ["已获取价格数据"]
    }
```

### 3. Edge（边）

边连接节点，控制执行流程：

```python
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(StockState)

# 添加节点
workflow.add_node("fetch", fetch_price_data)
workflow.add_node("analyze", analyze_data)
workflow.add_node("report", generate_report)

# 顺序边
workflow.add_edge(START, "fetch")
workflow.add_edge("fetch", "analyze")
workflow.add_edge("analyze", "report")
workflow.add_edge("report", END)
```

### 4. Annotated State

用 Annotated 可以定义特殊的字段行为：

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class ChatState(TypedDict):
    """聊天状态"""
    
    # 自动追加消息，不覆盖
    messages: Annotated[list, add_messages]
    
    # 普通字段
    user_name: str

# add_messages 会合并列表，而不是替换
def node_a(state: ChatState):
    return {"messages": ["消息 A"]}

def node_b(state: ChatState):
    return {"messages": ["消息 B"]}

# 结果：messages = ["消息 A", "消息 B"]
```

## 三、状态机模式

### 为什么叫 Graph？

```
      ┌────────────────────────────────────────┐
      │                                        │
      │     ┌────────────────────────┐        │
      │     │                        │        │
      │     │    ┌──────┐            │        │
START ─────▶│    │ Node │──────────────┤        │
      │     │    └──┬───┘              │        │
      │     │       │                  │        │
      │     │       ▼                  │        │
      │     │    ┌──────┐              │        │
      │     │    │ Node │              │        │
      │     │    └──┬───┘              │        │
      │     │       │                  │        │
      │     │       ▼                  │        │
      │     │    ┌──────┐              │        │
      │     │    │ Node │──────────────┘        │
      │     │    └──┬───┘                      │
      │     │       │                          │
      │     │       ▼                          │
      │     │    ┌──────┐                      │
      │     │    │ END  │                      │
      │     │    └──────┘                      │
      │     │                                    │
      └────────────────────────────────────────┘
```

### 状态持久化

```python
from langgraph.checkpoint.memory import MemorySaver

# 内存持久化
checkpointer = MemorySaver()

workflow = StateGraph(StockState)
# ... 添加节点和边
app = workflow.compile(checkpointer=checkpointer)

# 创建线程
config = {"configurable": {"thread_id": "user_123"}}

# 第一次调用（完整流程）
result = app.invoke({"stock_code": "600519"}, config)

# 第二次调用（从上次状态继续）
result = app.invoke({"stock_code": "000858"}, config)

# 获取当前状态
snapshot = app.get_state(config)
print(snapshot.values)  # 包含之前的所有数据
```

## 四、与 LangChain 的关系

```
LangChain          LangGraph
┌─────────┐       ┌────────────┐
│  LLM    │       │ StateGraph │
│ Chain   │       │            │
│  Tool   │       │  Node      │
│ Retriever│      │  Edge      │
└─────────┘       │  Checkpoint│
     │            └────────────┘
     │                   │
     ▼                   ▼
┌─────────────────────────────┐
│        LangGraph            │
│                             │
│  LangGraph = LangChain + 图结构  │
│                             │
│  - 使用 LangChain 的组件      │
│  - 添加图结构的控制能力        │
└─────────────────────────────┘
```

## 五、使用场景

### 1. 股票分析工作流

```python
# 工作流
fetch_data → parse_data → analyze_anomaly → generate_report
                        ↓
                   anomaly? → alert → notify_user
```

### 2. RAG 应用

```python
# 工作流
query → retrieve → grade_docs → generate → grade_answer
                        ↓
                  relevant? → rewrite_query
                        ↓
                   answer? → done
```

### 3. 多轮对话 Agent

```python
# 工作流
user_input → decide_action → tool_call → response
                              ↓
                         needs_more? → continue
                              ↓
                            done
```

### 4. 数据处理管道

```python
# 工作流
fetch → clean → validate → transform → load → report
              ↓
          invalid? → retry → manual_fix
```

## 六、对比其他框架

| 特性 | LangGraph | AutoGen | CrewAI |
|------|-----------|---------|--------|
| 架构 | 有向图 | 对话 | Agent 团队 |
| 循环支持 | ✅ | ⚠️ 有限 | ❌ |
| 状态持久化 | ✅ | ❌ | ❌ |
| 条件分支 | ✅ | ❌ | ⚠️ |
| LangChain 集成 | ✅ 原生 | ❌ | ❌ |
| 学习曲线 | 中等 | 陡峭 | 简单 |

## 七、核心优势

```python
# 1. 可控性：每一步都能控制
def analyze(state):
    # 可以在这里做任何事
    if condition:
        return "path_a"
    else:
        return "path_b"

# 2. 可观测性：每个节点都能监控
@app.middleware("http")
async def log_graph(request: Request, call_next):
    # 记录每个节点的输入输出
    result = await call_next(request)
    return result

# 3. 可恢复性：状态持久化
config = {"thread_id": "123"}
result = app.invoke(state, config)

# 中断后恢复
result = app.invoke(state, config)  # 从上次状态继续

# 4. 可测试性：每个节点可单独测试
def test_analyze():
    state = {"data": [...]}
    result = analyze(state)
    assert "anomaly_detected" in result
```

## 八、常见问题

### Q: LangGraph 和 LangChain Chain 的区别？

```python
# LangChain Chain：线性流程
chain = LLMChain(prompt=prompt, llm=llm)
result = chain.invoke({"topic": "AI"})  # 一步完成

# LangGraph：可以循环、分支
graph = StateGraph(State)
graph.add_node("analyze", analyze)
graph.add_edge("analyze", "analyze")  # 可以回到自己！
graph.add_edge("analyze", END)  # 或结束
```

### Q: 什么时候用 LangGraph？

```
不用 LangGraph：
├── 简单的问答
├── 单次 LLM 调用
└── 固定流程的单次任务

用 LangGraph：
├── 多步骤工作流
├── 需要循环迭代
├── 需要条件分支
├── 需要状态持久化
└── 需要人工干预
```

## 九、练习建议

1. 先运行官方的 "Introduction to LangGraph" 笔记本
2. 尝试修改简单工作流，添加新节点
3. 实现带条件分支的工作流
4. 添加状态持久化并测试中断恢复
5. 结合你的项目，实现股票分析工作流

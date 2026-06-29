# 工具调用详解

## 一、为什么需要工具？

```
没有工具的 LLM：
┌─────────────────┐
│   User Input    │
│ "贵州茅台价格？" │
└────────┬────────┘
         ↓
┌─────────────────┐
│     LLM         │
│  (只知道训练数据) │
└────────┬────────┘
         ↓
┌─────────────────┐
│   瞎猜的回答     │
│  "可能1500左右"  │
└─────────────────┘
❌ 不准确，没有实时数据

有工具的 LLM：
┌─────────────────┐
│   User Input    │
│ "贵州茅台价格？" │
└────────┬────────┘
         ↓
┌─────────────────┐
│     LLM         │
│ "需要查询价格"   │
└────────┬────────┘
         ↓
┌─────────────────┐
│   Tool (API)    │
│ 获取实时价格     │
└────────┬────────┘
         ↓
┌─────────────────┐
│     LLM         │
│ "贵州茅台价格    │
│  1500.5元"      │
└─────────────────┘
✅ 准确，有实时数据
```

## 二、定义工具

### 方式1：@tool 装饰器

```python
from langchain_core.tools import tool

@tool
def get_stock_price(code: str) -> dict:
    """
    获取股票当前价格
    
    Args:
        code: 股票代码，如 600519
    
    Returns:
        dict: 包含价格和涨跌信息
    """
    return {"price": 1500.0, "change": 2.5}

# 自动提取：
# - 函数名作为工具名：get_stock_price
# - docstring 第一行作为描述
# - Args 部分作为参数说明
```

### 方式2：Tool 对象

```python
from langchain_core.tools import Tool

get_price = Tool(
    name="get_stock_price",
    description="获取股票当前价格",
    func=get_price_function,  # 同步函数
    # args_schema=...  # 可选：Pydantic 模型
)

# 异步版本
async_get_price = Tool(
    name="get_stock_price",
    description="获取股票当前价格",
    coroutine=async_get_price_function,  # 异步函数
)
```

### 方式3：Structured Tool

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

class StockPriceInput(BaseModel):
    code: str = Field(description="股票代码")

def get_price(code: str) -> dict:
    return {"price": 1500.0}

stock_price_tool = StructuredTool(
    name="get_stock_price",
    description="获取股票当前价格",
    args_schema=StockPriceInput,
    func=get_price,
)
```

## 三、在工作流中使用工具

### 方式1：手动调用

```python
@tool
def get_price(code: str) -> dict:
    return {"price": 1500.0}

def query_node(state: State) -> dict:
    # 手动调用工具
    result = get_price.invoke({"code": "600519"})
    return {"price_info": result}
```

### 方式2：ToolNode（自动工具调用）

```python
from langgraph.prebuilt import ToolNode

# 创建工具列表
tools = [get_price, calculate_risk, search_news]

# 创建 ToolNode
tool_node = ToolNode(tools)

# 在工作流中使用
workflow.add_node("tools", tool_node)
```

## 四、LLM 绑定工具

### 基本绑定

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

# 绑定工具
llm_with_tools = llm.bind_tools(tools)

# 调用
response = llm_with_tools.invoke("查询 600519 的价格")
print(response.tool_calls)  # 工具调用请求
```

### 结构化输出

```python
# 使用 JSON schema
llm_with_schema = llm.bind_tools(
    tools,
    tool_choice="auto"  # 自动选择工具
)

# 指定必须使用某个工具
llm_with_required = llm.bind_tools(
    tools,
    tool_choice="get_price"  # 强制使用 get_price
)
```

## 五、ReAct 模式

```
ReAct = Reasoning + Acting

用户：分析 600519
      ↓
思考：我需要查询价格，然后计算风险
      ↓
行动：调用 get_price(600519)
      ↓
观察：价格 1500，涨幅 2.5%
      ↓
思考：价格信息已获取，需要计算风险
      ↓
行动：调用 calculate_risk(1500, 2.5)
      ↓
观察：风险等级低，建议持有
      ↓
回答：600519 当前价格 1500 元，风险等级低...
```

### 实现 ReAct

```python
from typing import TypedDict, Literal

class ReActState(TypedDict):
    messages: list
    intermediate_steps: list

def agent(state: ReActState):
    """LLM 决策节点"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def should_act(state: ReActState):
    """决定下一步"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "act"
    return END

def tool_action(state: ReActState):
    """执行工具"""
    tool_calls = state["messages"][-1].tool_calls
    results = []
    
    for call in tool_calls:
        result = tool_node.invoke({"messages": [call]})
        results.append(result)
    
    return {"messages": results}

# ReAct 循环
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_act,
    {
        "act": "tool_action",
        END: END
    }
)
workflow.add_edge("tool_action", "agent")
```

## 六、工具定义最佳实践

### 1. 清晰的描述

```python
@tool
def get_stock_price(code: str) -> dict:
    """
    获取股票当前价格和涨跌信息
    
    Args:
        code: 上海或深圳交易所的股票代码，6位数字
              例如：600519（贵州茅台）、000858（五粮液）
    
    Returns:
        dict: 包含以下字段：
            - price: 当前价格（元）
            - change: 涨跌幅（%）
            - volume: 成交量
            - name: 股票名称
    """
    ...
```

### 2. 错误处理

```python
@tool
def get_stock_price(code: str) -> dict:
    """获取股票价格"""
    if not code or len(code) != 6:
        return {"error": "无效的股票代码"}
    
    if not code.isdigit():
        return {"error": "股票代码必须是数字"}
    
    # 获取数据...
    if not found:
        return {"error": f"未找到股票 {code}"}
    
    return {"price": 1500.0, "change": 2.5}
```

### 3. 类型注解

```python
from typing import TypedDict

class StockPrice(TypedDict):
    price: float
    change: float
    volume: int
    name: str

@tool
def get_stock_price(code: str) -> StockPrice:
    """获取股票价格"""
    ...
```

## 七、实战：股票分析 Agent

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

# 定义工具
@tool
def get_stock_price(code: str) -> dict:
    """获取股票价格"""
    return {"price": 1500.0, "change": 2.5, "name": "贵州茅台"}

@tool
def get_stock_news(code: str) -> list[dict]:
    """获取股票相关新闻"""
    return [
        {"title": "公司发布财报", "sentiment": "positive"},
        {"title": "行业前景看好", "sentiment": "neutral"}
    ]

@tool
def analyze_anomaly(price: float, change: float, volume: float) -> dict:
    """分析股票异常"""
    anomaly_score = abs(change) + (volume / 1000000)
    return {
        "detected": anomaly_score > 5,
        "score": anomaly_score,
        "level": "high" if anomaly_score > 5 else "normal"
    }

# 状态
class AgentState(TypedDict):
    messages: list
    stock_code: str
    analysis_result: dict | None

# LLM
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools([get_stock_price, get_stock_news, analyze_anomaly])

# 节点
def llm_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "final"

def final_node(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "content"):
        return {"analysis_result": {"summary": last.content}}

# 工作流
workflow = StateGraph(AgentState)

tools = [get_stock_price, get_stock_news, analyze_anomaly]
workflow.add_node("llm", llm_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("final", final_node)

workflow.add_edge(START, "llm")
workflow.add_conditional_edges(
    "llm",
    should_continue,
    {"tools": "tools", "final": "final"}
)
workflow.add_edge("tools", "llm")
workflow.add_edge("final", END)

app = workflow.compile()

# 运行
result = app.invoke({
    "messages": [{"role": "user", "content": "分析 600519"}],
    "stock_code": "600519",
    "analysis_result": None
})

print(result["analysis_result"])
```

## 八、常见问题

### 1. 工具调用失败

```python
@tool
def risky_tool() -> str:
    """可能失败的工具"""
    try:
        return fetch_data()
    except Exception as e:
        return f"工具执行失败: {str(e)}"
```

### 2. 并行工具调用

```python
# ToolNode 会自动处理并行工具调用
# 如果 LLM 一次请求多个工具，会并行执行

# 例如：LLM 请求了 get_price 和 get_news
# ToolNode 会并行执行，然后合并结果
```

### 3. 工具超时

```python
import asyncio
from langchain_core.tools import tool

@tool
async def slow_tool() -> str:
    """模拟慢速工具"""
    await asyncio.sleep(10)  # 10秒超时
    return "完成"

# 在 ToolNode 中设置超时
tool_node = ToolNode(tools, timeout=30)  # 30秒超时
```

## 练习题

1. 定义一个获取股票历史数据的工具
2. 定义一个计算技术指标的工具（如均线、MACD）
3. 创建一个完整的股票分析 Agent，包含多个工具
4. 实现工具调用失败时的重试机制
5. 创建一个多轮对话的股票分析 Agent

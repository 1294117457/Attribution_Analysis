# Step 04: 工具调用 - Tool 集成

## 学习目标
掌握 LangGraph 中 Tool 的定义和集成，实现可调用工具的 Agent

## 概念速览

```python
from langchain_core.tools import tool

# 定义工具
@tool
def get_stock_price(code: str) -> float:
    """获取股票价格"""
    return 150.0

# 在节点中使用工具
def query_node(state):
    price = get_stock_price.invoke({"code": "600519"})
    return {"price": price}
```

## 任务

### 任务 1: 定义工具

创建 `demo_04_tools.py`：

```python
"""
LangGraph 工具调用示例
"""
from typing import TypedDict
from langchain_core.tools import tool, Tool
from langgraph.graph import StateGraph, START, END

# ============ 1. 定义工具 ============

@tool
def get_stock_price(code: str) -> dict:
    """
    获取股票当前价格
    
    Args:
        code: 股票代码，如 600519
    
    Returns:
        dict: 包含价格和涨跌信息
    """
    # 模拟数据
    mock_data = {
        "600519": {"name": "贵州茅台", "price": 1500.0, "change": 2.5},
        "000858": {"name": "五粮液", "price": 150.0, "change": -1.2},
        "600036": {"name": "招商银行", "price": 35.0, "change": 0.8},
    }
    
    if code in mock_data:
        return mock_data[code]
    return {"name": "未知", "price": 0, "change": 0}

@tool
def calculate_risk(price: float, change: float) -> dict:
    """
    计算股票风险等级
    
    Args:
        price: 当前价格
        change: 涨跌幅
    
    Returns:
        dict: 风险等级和建议
    """
    risk_score = abs(change) / 10  # 简单风险计算
    
    if risk_score > 1:
        level = "高风险"
        advice = "建议观望或减仓"
    elif risk_score > 0.5:
        level = "中等风险"
        advice = "建议谨慎操作"
    else:
        level = "低风险"
        advice = "可以适当关注"
    
    return {
        "risk_score": round(risk_score, 2),
        "level": level,
        "advice": advice
    }

@tool
def search_news(keyword: str) -> list[dict]:
    """
    搜索相关新闻
    
    Args:
        keyword: 搜索关键词
    
    Returns:
        list: 新闻列表
    """
    # 模拟新闻数据
    mock_news = {
        "茅台": [
            {"title": "贵州茅台发布财报，营收增长15%", "sentiment": "positive"},
            {"title": "茅台提价预期升温", "sentiment": "positive"},
        ],
        "银行": [
            {"title": "银行业整体估值处于低位", "sentiment": "neutral"},
        ]
    }
    
    return mock_news.get(keyword, [])

# 打印工具信息
print("=" * 50)
print("定义的工具:")
print("=" * 50)
for t in [get_stock_price, calculate_risk, search_news]:
    print(f"\n工具: {t.name}")
    print(f"描述: {t.description}")
```

### 任务 2: 创建带工具的工作流

```python
# ============ 2. 定义状态 ============

class StockAnalysisState(TypedDict):
    """股票分析状态"""
    stock_code: str
    stock_name: str
    
    # 工具结果
    price_info: dict | None
    risk_info: dict | None
    news: list | None
    
    # 最终结果
    analysis: str
    messages: list[str]

# ============ 3. 定义节点 ============

def query_price(state: StockAnalysisState) -> dict:
    """查询价格"""
    print(f">>> 查询 {state['stock_code']} 的价格")
    
    result = get_stock_price.invoke({"code": state["stock_code"]})
    print(f"价格信息: {result}")
    
    return {
        "price_info": result,
        "messages": state["messages"] + [f"已查询价格: {result['price']}元"]
    }

def calculate_risk_level(state: StockAnalysisState) -> dict:
    """计算风险"""
    price_info = state.get("price_info", {})
    price = price_info.get("price", 0)
    change = price_info.get("change", 0)
    
    print(f">>> 计算风险: 价格={price}, 涨跌={change}%")
    
    result = calculate_risk.invoke({"price": price, "change": change})
    print(f"风险信息: {result}")
    
    return {
        "risk_info": result,
        "messages": state["messages"] + [f"风险等级: {result['level']}"]
    }

def search_related_news(state: StockAnalysisState) -> dict:
    """搜索新闻"""
    name = state.get("stock_name", "")
    if not name:
        name = state.get("price_info", {}).get("name", "")
    
    print(f">>> 搜索关于 {name} 的新闻")
    
    news = search_news.invoke({"keyword": name})
    print(f"找到 {len(news)} 条新闻")
    
    return {
        "news": news,
        "messages": state["messages"] + [f"找到 {len(news)} 条新闻"]
    }

def generate_analysis(state: StockAnalysisState) -> dict:
    """生成分析报告"""
    price_info = state.get("price_info", {})
    risk_info = state.get("risk_info", {})
    news = state.get("news", [])
    
    print(">>> 生成分析报告")
    
    sentiment = "正面" if news and news[0].get("sentiment") == "positive" else "中性"
    
    analysis = f"""
    {'='*50}
    股票分析报告
    {'='*50}
    股票代码: {state['stock_code']}
    股票名称: {price_info.get('name', '未知')}
    
    价格信息:
    - 当前价格: {price_info.get('price', 0)}元
    - 涨跌幅: {price_info.get('change', 0)}%
    
    风险评估:
    - 风险等级: {risk_info.get('level', '未知')}
    - 风险评分: {risk_info.get('risk_score', 0)}
    - 操作建议: {risk_info.get('advice', '暂无')}
    
    新闻情感: {sentiment}
    相关新闻: {len(news)}条
    
    {'='*50}
    """
    
    return {
        "analysis": analysis,
        "messages": state["messages"] + ["分析报告已生成"]
    }

# ============ 4. 创建工作流 ============

def create_stock_agent():
    """创建股票分析 Agent"""
    workflow = StateGraph(StockAnalysisState)
    
    workflow.add_node("query_price", query_price)
    workflow.add_node("calculate_risk", calculate_risk_level)
    workflow.add_node("search_news", search_related_news)
    workflow.add_node("analyze", generate_analysis)
    
    workflow.add_edge(START, "query_price")
    workflow.add_edge("query_price", "calculate_risk")
    workflow.add_edge("query_price", "search_news")  # 并行
    workflow.add_edge("calculate_risk", "analyze")
    workflow.add_edge("search_news", "analyze")      # 并行
    workflow.add_edge("analyze", END)
    
    return workflow.compile()

# ============ 5. 运行 ============

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("运行股票分析 Agent")
    print("=" * 50)
    
    app = create_stock_agent()
    
    initial_state: StockAnalysisState = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "price_info": None,
        "risk_info": None,
        "news": None,
        "analysis": "",
        "messages": []
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + result["analysis"])
```

## 任务 3: 带 LLM 的 Agent

```python
"""
带 LLM 的股票分析 Agent
"""
from typing import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# 假设已定义 get_stock_price, calculate_risk, search_news 工具

# 创建 LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 绑定工具
llm_with_tools = llm.bind_tools([get_stock_price, calculate_risk, search_news])

class LLMAgentState(TypedDict):
    """LLM Agent 状态"""
    messages: list  # 对话消息

def call_llm(state: LLMAgentState) -> dict:
    """调用 LLM"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: LLMAgentState) -> str:
    """检查是否需要继续（是否有工具调用）"""
    last_message = state["messages"][-1]
    
    # 如果 LLM 返回了 tool_calls，需要执行工具
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    return END

# 创建带工具的节点
tool_node = ToolNode([get_stock_price, calculate_risk, search_news])

# 创建工作流
workflow = StateGraph(LLMAgentState)

workflow.add_node("llm", call_llm)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "llm")

# 条件边
workflow.add_conditional_edges(
    "llm",
    should_continue,
    {
        "tools": "tools",  # 执行工具
        END: END            # 结束
    }
)

workflow.add_edge("tools", "llm")  # 工具执行完后继续 LLM

app = workflow.compile()

# 运行
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("LLM Agent 示例")
    print("=" * 50)
    
    initial_state = {
        "messages": [
            {"role": "user", "content": "帮我分析一下 600519 这只股票"}
        ]
    }
    
    # 流式运行
    for chunk in app.stream(initial_state):
        if "llm" in chunk:
            msg = chunk["llm"]["messages"][-1]
            if hasattr(msg, "content") and msg.content:
                print(f"LLM: {msg.content[:100]}...")
            if hasattr(msg, "tool_calls"):
                print(f"工具调用: {[tc['name'] for tc in msg.tool_calls]}")
        if "tools" in chunk:
            print(f"工具结果: {chunk['tools']}")
```

## 运行

```bash
python demo_04_tools.py
```

## 下一步
阅读 `../docs/analysis/04_tools_integration.md` 深入理解

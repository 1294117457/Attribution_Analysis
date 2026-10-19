# Step 05: 完整示例 - 股票异常检测 Agent

## 学习目标
构建一个完整的股票异常检测 Agent，整合所有学过的知识

## 概念回顾

```
股票异常检测 Agent
├── StateGraph
│   ├── State: 状态管理
│   ├── Nodes: 节点（数据获取、分析、报告）
│   ├── Edges: 边（流程控制）
│   └── Conditional: 条件分支
├── Tools
│   ├── get_stock_data: 获取数据
│   ├── detect_anomaly: 异常检测
│   └── send_alert: 发送警报
└── Workflow
    fetch → analyze → decide → alert/report
```

## 任务

### 任务 1: 项目结构

创建 `demo_05_complete.py`：

```python
"""
股票异常检测 Agent - 完整示例
整合所有 LangGraph 知识点
"""
from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.tools import tool
from datetime import datetime

print("=" * 60)
print("股票异常检测 Agent")
print("=" * 60)

# ============ 1. 定义工具 ============

@tool
def get_stock_realtime(code: str) -> dict:
    """
    获取股票实时行情
    
    Args:
        code: 股票代码 (6位数字)
    
    Returns:
        dict: 包含实时行情数据
    """
    # 模拟数据
    mock_data = {
        "600519": {
            "name": "贵州茅台",
            "price": 1500.0,
            "change": 2.5,
            "volume": 5000000,
            "high": 1520.0,
            "low": 1480.0,
            "open": 1490.0,
        },
        "000858": {
            "name": "五粮液",
            "price": 150.0,
            "change": -1.2,
            "volume": 2000000,
            "high": 155.0,
            "low": 148.0,
            "open": 152.0,
        },
        "600036": {
            "name": "招商银行",
            "price": 35.0,
            "change": 0.8,
            "volume": 3000000,
            "high": 36.0,
            "low": 34.5,
            "open": 34.8,
        }
    }
    
    if code in mock_data:
        return mock_data[code]
    return {"error": f"未找到股票 {code}"}

@tool
def get_stock_history(code: str, days: int = 5) -> list[dict]:
    """
    获取股票历史数据
    
    Args:
        code: 股票代码
        days: 获取天数，默认5天
    
    Returns:
        list: 历史行情列表
    """
    # 模拟历史数据
    base_price = 1500 if code == "600519" else 150 if code == "000858" else 35
    history = []
    
    for i in range(days):
        import random
        change_pct = random.uniform(-3, 3)
        price = base_price * (1 + change_pct / 100)
        history.append({
            "date": f"2024-01-{15-i:02d}",
            "close": round(price, 2),
            "change": round(change_pct, 2),
            "volume": random.randint(1000000, 5000000)
        })
    
    return history

@tool
def detect_price_anomaly(current: float, change_pct: float, history: list) -> dict:
    """
    检测价格异常
    
    Args:
        current: 当前价格
        change_pct: 涨跌幅
        history: 历史数据
    
    Returns:
        dict: 异常检测结果
    """
    anomalies = []
    
    # 1. 涨跌异常
    if abs(change_pct) > 5:
        anomalies.append({
            "type": "price_change",
            "severity": "high" if abs(change_pct) > 10 else "medium",
            "description": f"涨跌幅异常: {change_pct}%"
        })
    
    # 2. 波动异常
    if history:
        avg_price = sum(h["close"] for h in history) / len(history)
        price_diff = abs(current - avg_price) / avg_price
        
        if price_diff > 0.05:
            anomalies.append({
                "type": "price_volatility",
                "severity": "medium",
                "description": f"价格偏离均值: {price_diff*100:.1f}%"
            })
    
    return {
        "has_anomaly": len(anomalies) > 0,
        "count": len(anomalies),
        "anomalies": anomalies
    }

@tool
def detect_volume_anomaly(volume: int, history: list) -> dict:
    """
    检测成交量异常
    
    Args:
        volume: 当前成交量
        history: 历史数据
    
    Returns:
        dict: 成交量异常检测结果
    """
    if not history:
        return {"has_anomaly": False, "anomalies": []}
    
    avg_volume = sum(h["volume"] for h in history) / len(history)
    ratio = volume / avg_volume if avg_volume > 0 else 0
    
    if ratio > 2:
        return {
            "has_anomaly": True,
            "ratio": round(ratio, 2),
            "anomalies": [{
                "type": "volume_surge",
                "severity": "high" if ratio > 3 else "medium",
                "description": f"成交量放大 {ratio:.1f} 倍"
            }]
        }
    
    return {"has_anomaly": False, "anomalies": []}

@tool
def generate_report(code: str, name: str, current: float, 
                    change_pct: float, anomalies: list) -> str:
    """
    生成异常检测报告
    
    Args:
        code: 股票代码
        name: 股票名称
        current: 当前价格
        change_pct: 涨跌幅
        anomalies: 异常列表
    
    Returns:
        str: 报告内容
    """
    anomaly_count = len(anomalies)
    severity = "高" if any(a.get("severity") == "high" for a in anomalies) else "中"
    
    report = f"""
{'='*60}
股票异常检测报告
{'='*60}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
股票代码: {code}
股票名称: {name}
{'='*60}
行情数据
{'='*60}
当前价格: {current:.2f}元
涨跌幅: {change_pct:+.2f}%
{'='*60}
异常检测
{'='*60}
检测结果: {'发现异常' if anomaly_count > 0 else '未发现异常'}
异常数量: {anomaly_count} 项
风险等级: {severity}风险
"""
    
    if anomalies:
        report += "\n异常详情:\n"
        for i, a in enumerate(anomalies, 1):
            report += f"  {i}. [{a['severity'].upper()}] {a['description']}\n"
    
    report += f"""
{'='*60}
建议: {'请密切关注，及时采取风险控制措施' if anomaly_count > 0 else '暂无异常，保持常规关注'}
{'='*60}
"""
    
    return report

@tool
def send_alert(code: str, name: str, anomalies: list) -> dict:
    """
    发送警报通知
    
    Args:
        code: 股票代码
        name: 股票名称
        anomalies: 异常列表
    
    Returns:
        dict: 发送结果
    """
    print(f"\n{'='*60}")
    print(f"🚨 发送警报")
    print(f"{'='*60}")
    print(f"股票: {name}({code})")
    print(f"异常数量: {len(anomalies)}")
    
    for i, a in enumerate(anomalies, 1):
        print(f"  {i}. {a['description']}")
    
    print(f"{'='*60}")
    
    return {
        "sent": True,
        "timestamp": datetime.now().isoformat(),
        "recipients": ["monitor@example.com"],
        "message": f"{name}({code}) 发现 {len(anomalies)} 项异常"
    }
```

### 任务 2: 定义状态

```python
# ============ 2. 定义状态 ============

class AnomalyDetectionState(TypedDict):
    """异常检测状态"""
    stock_code: str
    
    # 行情数据
    realtime_data: dict | None
    history_data: list | None
    
    # 检测结果
    price_anomaly: dict | None
    volume_anomaly: dict | None
    all_anomalies: list
    
    # 最终结果
    report: str
    alert_sent: bool
    
    # 消息
    messages: Annotated[list, add_messages]
    steps_taken: list[str]
```

### 任务 3: 定义节点

```python
# ============ 3. 定义节点函数 ============

def fetch_realtime(state: AnomalyDetectionState) -> dict:
    """获取实时行情"""
    code = state["stock_code"]
    print(f"\n>>> 步骤1: 获取 {code} 实时行情")
    
    data = get_stock_realtime.invoke({"code": code})
    
    if "error" in data:
        return {
            "messages": add_messages(state["messages"], f"错误: {data['error']}"),
            "steps_taken": state["steps_taken"] + ["fetch_realtime_failed"]
        }
    
    return {
        "realtime_data": data,
        "messages": add_messages(state["messages"], 
            f"已获取 {data.get('name', code)} 实时数据: 价格 {data['price']}"),
        "steps_taken": state["steps_taken"] + ["fetch_realtime"]
    }

def fetch_history(state: AnomalyDetectionState) -> dict:
    """获取历史数据"""
    code = state["stock_code"]
    print(f">>> 步骤2: 获取 {code} 历史数据")
    
    history = get_stock_history.invoke({"code": code, "days": 5})
    
    return {
        "history_data": history,
        "messages": add_messages(state["messages"], f"已获取 {len(history)} 天历史数据"),
        "steps_taken": state["steps_taken"] + ["fetch_history"]
    }

def analyze_price(state: AnomalyDetectionState) -> dict:
    """分析价格异常"""
    realtime = state.get("realtime_data", {})
    history = state.get("history_data", [])
    
    if not realtime or "error" in realtime:
        return {"price_anomaly": None, "messages": state["messages"]}
    
    print(f">>> 步骤3: 分析价格异常")
    
    result = detect_price_anomaly.invoke({
        "current": realtime.get("price", 0),
        "change_pct": realtime.get("change", 0),
        "history": history
    })
    
    print(f"价格异常检测: {'发现异常' if result['has_anomaly'] else '无异常'}")
    
    return {
        "price_anomaly": result,
        "messages": add_messages(state["messages"], 
            f"价格异常检测: {'发现' + str(result['count']) + '项' if result['has_anomaly'] else '无异常'}"),
        "steps_taken": state["steps_taken"] + ["analyze_price"]
    }

def analyze_volume(state: AnomalyDetectionState) -> dict:
    """分析成交量异常"""
    realtime = state.get("realtime_data", {})
    history = state.get("history_data", [])
    
    if not realtime or "error" in realtime:
        return {"volume_anomaly": None}
    
    print(f">>> 步骤4: 分析成交量异常")
    
    result = detect_volume_anomaly.invoke({
        "volume": realtime.get("volume", 0),
        "history": history
    })
    
    print(f"成交量异常检测: {'发现异常' if result['has_anomaly'] else '无异常'}")
    
    return {
        "volume_anomaly": result,
        "messages": add_messages(state["messages"],
            f"成交量异常检测: {'发现异常' if result['has_anomaly'] else '无异常'}"),
        "steps_taken": state["steps_taken"] + ["analyze_volume"]
    }

def aggregate_anomalies(state: AnomalyDetectionState) -> dict:
    """汇总异常"""
    print(f">>> 步骤5: 汇总异常")
    
    all_anomalies = []
    
    price_anomaly = state.get("price_anomaly", {})
    if price_anomaly and price_anomaly.get("has_anomaly"):
        all_anomalies.extend(price_anomaly.get("anomalies", []))
    
    volume_anomaly = state.get("volume_anomaly", {})
    if volume_anomaly and volume_anomaly.get("has_anomaly"):
        all_anomalies.extend(volume_anomaly.get("anomalies", []))
    
    print(f"共发现 {len(all_anomalies)} 项异常")
    
    return {
        "all_anomalies": all_anomalies,
        "messages": add_messages(state["messages"], 
            f"汇总完成: 共 {len(all_anomalies)} 项异常"),
        "steps_taken": state["steps_taken"] + ["aggregate_anomalies"]
    }

def generate_final_report(state: AnomalyDetectionState) -> dict:
    """生成最终报告"""
    print(f">>> 步骤6: 生成报告")
    
    realtime = state.get("realtime_data", {})
    anomalies = state.get("all_anomalies", [])
    
    report = generate_report.invoke({
        "code": state["stock_code"],
        "name": realtime.get("name", "未知"),
        "current": realtime.get("price", 0),
        "change_pct": realtime.get("change", 0),
        "anomalies": anomalies
    })
    
    print(report)
    
    return {
        "report": report,
        "messages": add_messages(state["messages"], "报告已生成"),
        "steps_taken": state["steps_taken"] + ["generate_report"]
    }

def send_notification(state: AnomalyDetectionState) -> dict:
    """发送警报"""
    print(f">>> 步骤7: 发送警报")
    
    realtime = state.get("realtime_data", {})
    anomalies = state.get("all_anomalies", [])
    
    result = send_alert.invoke({
        "code": state["stock_code"],
        "name": realtime.get("name", "未知"),
        "anomalies": anomalies
    })
    
    return {
        "alert_sent": result.get("sent", False),
        "messages": add_messages(state["messages"], "警报已发送"),
        "steps_taken": state["steps_taken"] + ["send_alert"]
    }

def skip_notification(state: AnomalyDetectionState) -> dict:
    """跳过警报"""
    print(f">>> 跳过警报（无异常或异常轻微）")
    
    return {
        "alert_sent": False,
        "messages": add_messages(state["messages"], "跳过警报"),
        "steps_taken": state["steps_taken"] + ["skip_alert"]
    }
```

### 任务 4: 条件判断

```python
# ============ 4. 定义条件函数 ============

def should_alert(state: AnomalyDetectionState) -> Literal["alert", "skip"]:
    """决定是否发送警报"""
    anomalies = state.get("all_anomalies", [])
    
    if not anomalies:
        return "skip"
    
    # 如果有高严重度异常，发送警报
    for anomaly in anomalies:
        if anomaly.get("severity") == "high":
            return "alert"
    
    # 中等严重度也发送
    if anomalies:
        return "alert"
    
    return "skip"
```

### 任务 5: 创建工作流

```python
# ============ 5. 创建工作流 ============

def create_anomaly_detection_workflow():
    """创建异常检测工作流"""
    
    workflow = StateGraph(AnomalyDetectionState)
    
    # 添加节点
    workflow.add_node("fetch_realtime", fetch_realtime)
    workflow.add_node("fetch_history", fetch_history)
    workflow.add_node("analyze_price", analyze_price)
    workflow.add_node("analyze_volume", analyze_volume)
    workflow.add_node("aggregate_anomalies", aggregate_anomalies)
    workflow.add_node("generate_report", generate_final_report)
    workflow.add_node("send_alert", send_notification)
    workflow.add_node("skip_alert", skip_notification)
    
    # 设置入口
    workflow.add_edge(START, "fetch_realtime")
    workflow.add_edge(START, "fetch_history")
    
    # 数据获取后进行分析
    workflow.add_edge("fetch_realtime", "analyze_price")
    workflow.add_edge("fetch_history", "analyze_price")
    workflow.add_edge("fetch_history", "analyze_volume")
    workflow.add_edge("analyze_price", "aggregate_anomalies")
    workflow.add_edge("analyze_volume", "aggregate_anomalies")
    
    # 生成报告
    workflow.add_edge("aggregate_anomalies", "generate_report")
    
    # 条件分支：是否发送警报
    workflow.add_conditional_edges(
        "generate_report",
        should_alert,
        {
            "alert": "send_alert",
            "skip": "skip_alert"
        }
    )
    
    # 都结束
    workflow.add_edge("send_alert", END)
    workflow.add_edge("skip_alert", END)
    
    return workflow.compile()
```

### 任务 6: 运行测试

```python
# ============ 6. 运行测试 ============

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("运行测试")
    print("=" * 60)
    
    app = create_anomaly_detection_workflow()
    
    # 测试用例
    test_cases = [
        {"code": "600519", "desc": "正常波动"},
        {"code": "000858", "desc": "成交量放大"},
        {"code": "600036", "desc": "其他股票"},
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"测试: {test['code']} - {test['desc']}")
        print("=" * 60)
        
        initial_state: AnomalyDetectionState = {
            "stock_code": test["code"],
            "realtime_data": None,
            "history_data": None,
            "price_anomaly": None,
            "volume_anomaly": None,
            "all_anomalies": [],
            "report": "",
            "alert_sent": False,
            "messages": [],
            "steps_taken": []
        }
        
        result = app.invoke(initial_state)
        
        print(f"\n执行步骤: {result['steps_taken']}")
        print(f"发现的异常: {len(result['all_anomalies'])} 项")
        print(f"警报发送: {'是' if result['alert_sent'] else '否'}")
```

## 运行

```bash
python demo_05_complete.py
```

## 工作流程图

```
                    ┌──────────────┐
                    │    START     │
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            ↓                             ↓
    ┌───────────────┐            ┌───────────────┐
    │fetch_realtime│            │ fetch_history │
    └───────┬───────┘            └───────┬───────┘
            │                             │
            └──────────┬──────────────────┘
                       ↓
              ┌────────────────┐
              │ analyze_price  │
              └───────┬────────┘
                      │
            ┌─────────┴─────────┐
            ↓                   ↓
    ┌───────────────┐  ┌───────────────┐
    │analyze_volume │  │              │
    └───────┬───────┘  │              │
            │           │              │
            └───────────┼───────────────┘
                        ↓
               ┌────────────────┐
               │aggregate_anomaly│
               └───────┬────────┘
                       ↓
              ┌────────────────┐
              │generate_report │
               └───────┬────────┘
                       │
                       ↓
            ┌──────────┴──────────┐
            ↓                     ↓
      ┌──────────┐          ┌──────────┐
      │send_alert│          │skip_alert│
      └────┬─────┘          └────┬─────┘
           └──────────┬─────────┘
                      ↓
                   ┌─────┐
                   │ END │
                   └─────┘
```

## 下一步
- 在你的项目中应用这个工作流
- 添加更多检测规则
- 集成真实的 akshare 数据源
- 添加 Web API 接口

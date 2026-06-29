# LangGraph 基础学习路径

## 学习目标
掌握 LangGraph 框架，构建复杂的多步骤 AI 工作流

## 前置知识
- Python 基础（类、函数、异步）
- FastAPI 基础（路由、请求响应）
- LLM 基础概念（ChatGPT、API 调用）

## 学习顺序

### 第一阶段：核心概念（Day 1）

| Step | 标题 | 内容 | 预计时间 |
|------|------|------|----------|
| 01 | 什么是 LangGraph | 基本概念和架构 | 30分钟 |
| 02 | 状态机基础 | StateGraph、节点、边 | 50分钟 |
| 03 | 条件分支 | 条件边、分支逻辑 | 40分钟 |

### 第二阶段：实际应用（Day 2-3）

| Step | 标题 | 内容 | 预计时间 |
|------|------|------|----------|
| 04 | 股票分析工作流 | 多步骤分析流程 | 60分钟 |
| 05 | 工具调用 | Tool、工具集成 | 50分钟 |
| 06 | 异常检测 Agent | 完整示例 | 60分钟 |

## 学习方法
1. 先阅读 `docs/step/` 中的指导
2. 运行示例代码观察效果
3. 对照 `docs/analysis/` 深入理解
4. 修改代码实验各种功能

## 运行环境

```bash
cd learning/langgraph
source ../venv/bin/activate

# 安装依赖
pip install langgraph langchain-core langchain-openai

# 运行 demo
python demo_01_intro.py
```

## 前提条件

需要设置 OpenAI API Key：

```bash
export OPENAI_API_KEY="your-api-key"
```

## 与你的项目结合

```
LangGraph 工作流
    ↓
┌─────────────────────────────────────┐
│  Stock Analysis Agent               │
│                                     │
│  ┌─────────┐    ┌──────────────┐   │
│  │ Fetch  │───▶│ Analyze      │   │
│  │ Data   │    │ Price        │   │
│  └─────────┘    └──────┬───────┘   │
│                        │           │
│                   条件分支          │
│                   /     \          │
│             异常         正常      │
│            /               \       │
│    ┌────────────┐    ┌──────────┐ │
│    │ Alert     │    │ Generate │ │
│    │ Report   │    │ Report   │ │
│    └───────────┘    └──────────┘ │
└─────────────────────────────────────┘
```

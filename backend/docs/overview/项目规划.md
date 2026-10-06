# 智能金融数据归因分析平台（Intelligent Financial Attribution Analysis Platform）

## 项目规划文档

**版本**：v4.0  
**日期**：2026年6月  
**技术栈**：Vue-ts + Python LangGraph FastAPI + PostgreSQL pgvector + Redis + Docker

---

## 项目概述

### 核心痛点

- 数据波动时，分析师需要手动排查多个维度才能找到原因
- 经验依赖严重，新人难以快速上手
- 缺乏系统化的归因分析工具

### 项目目标

构建一个**智能金融数据归因分析平台**，让用户能够：

1. **一句话提问**：输入"为什么茅台今天跌了？"或"利率为什么上涨？"
2. **自动检测**：系统自动检测数据异常，提取变化特征
3. **智能归因**：自动拆解各维度贡献度，定位核心驱动因素
4. **经验累积**：系统越用越聪明，自动匹配历史相似案例

---

## 技术架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         前端层（Vue 3 + TypeScript）                    │
│  数据上传 → 指标配置 → 看板展示 → 交互式下钻 → 用户反馈                  │
│                              │                                          │
│                              ▼                                          │
│                    ┌─────────────────┐                                  │
│                    │   Nginx 网关    │                                  │
│                    │   (反向代理)     │                                  │
│                    └────────┬────────┘                                  │
└─────────────────────────────┼───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      API 网关层（FastAPI + Python）                      │
│  POST /api/v1/analyze  POST /api/v1/collect  GET /api/v1/klines        │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     LangGraph 多 Agent 编排层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  异常检测    │→ │  情感分析    │→ │  归因分析    │→ │  报告生成  │ │
│  │   Agent      │  │   Agent      │  │   Agent      │  │   Agent    │ │
│  │  (算法+AI)   │  │    (AI)      │  │  (算法+AI)   │  │    (AI)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│         │                │                │                             │
│         └────────────────┴────────────────┴──────────────────────────┐ │
│                                │                                       │
│                         经验检索/存储                                   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         算法引擎层                                       │
│  StatisticalDetector  SignalExtractor  ContributionCalculator          │
│  技术指标计算（MA/EMA/RSI/MACD/BOLL）  异常检测（3σ/IQR）              │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         数据接入层                                       │
│       AkShare (A股)  │  PostgreSQL (持久化)  │  Redis (缓存)           │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         经验层 (pgvector)                               │
│     向量化  │  相似检索  │  置信度更新  │  反馈处理                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Docker 微服务架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Nginx 网关                                    │
│                    (反向代理 + 静态资源服务)                              │
└─────────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     Frontend     │  │     Backend      │  │     Backend      │
│   (Vue-ts SPA)  │  │   (Python API)   │  │   (Python API)   │
│     端口:80     │  │    端口:8000     │  │    端口:8001     │
└─────────────────┘  └────────┬────────┘  └────────┬────────┘
                              │                    │
                              └──────────┬───────────┘
                                         │
          ┌──────────────────────────────┼──────────────────────────────┐
          │                              │                              │
          ▼                              ▼                              ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────┐
│   PostgreSQL     │  │   pgvector       │  │      Redis       │  │  AkShare │
│   (主数据库)     │  │  (向量存储)       │  │    (缓存)        │  │ (数据源) │
│    端口:5432    │  │   内嵌在 PG       │  │    端口:6379    │  │         │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────┘
```

### 技术选型

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **前端框架** | Vue 3 + TypeScript | 响应式前端，类型安全 |
| **构建工具** | Vite | 快速开发体验 |
| **UI 组件** | Element Plus | Vue 3 组件库 |
| **图表** | ECharts | 瀑布图、折线图、贡献度图 |
| **状态管理** | Pinia | Vue 3 状态管理 |
| **后端框架** | FastAPI 0.115 | 现代高性能 Python Web 框架，原生异步支持 |
| **AI 编排** | LangGraph 0.3 | 多 Agent 协作编排，状态管理 |
| **AI 基础** | LangChain 0.3 | LLM 调用、Tool 定义、Prompt 管理 |
| **嵌入模型** | QianfanEmbeddings | 百度千帆 Embedding（中文优化） |
| **大模型** | 通义千问 / GPT-4 | AI 判断和报告生成 |
| **数据采集** | AkShare 1.14 | 免费 A 股数据接口 |
| **数据库** | PostgreSQL 16 | 关系数据持久化 + pgvector 向量 |
| **ORM** | SQLAlchemy 2.0 | Python ORM，类型安全 |
| **迁移工具** | Alembic | 数据库版本管理 |
| **向量存储** | pgvector | PostgreSQL 扩展，经验向量存储与相似检索 |
| **缓存** | Redis | 会话缓存、热点数据、限流 |
| **容器化** | Docker + Docker Compose | 开发/生产部署 |

---

## 核心功能

### 异常检测（8 种算法）

| 检测方法 | 适用场景 | 说明 |
|----------|----------|------|
| Z-score（3σ）| 偏离均值 | 股价单日暴涨超3倍标准差 |
| IQR（箱线图）| 离群值 | 交易量异常放大 |
| 同比偏差 | 年度对比 | 今年 vs 去年同期 |
| 环比偏差 | 月度对比 | 本月 vs 上月 |
| 方向检测 | 涨跌判断 | 股价由涨转跌 |
| 速度检测 | 变化速率 | 跌幅加速扩大 |
| 拐点检测 | 趋势反转 | V型/倒V型反转 |
| 季节性检测 | 周期规律 | 年底资金面紧张 |

### 归因分析

- **基期拆解法**：拆解"价格 vs 数量"的贡献
- **多维贡献度计算**：按区域/品类/时间/产品类型动态聚合
- **核心驱动因素排序**：识别最大贡献者和最大拖累者

### 经验系统（pgvector）

- **768 维向量**：综合异常类型 + 指标特征 + 新闻情绪 + 归因结论
- **余弦相似度匹配**：匹配度 > 0.85 时复用历史结论
- **置信度进化**：用户反馈驱动置信度更新
- **历史案例参考**：检索相似案例作为 LLM 上下文

---

## 项目结构

```
attribution-analysis/
├── frontend/                    # Vue 3 + TypeScript 前端
│   ├── src/
│   │   ├── views/              # 页面
│   │   ├── components/         # 组件
│   │   ├── stores/              # Pinia 状态
│   │   ├── api/                # API 调用
│   │   ├── types/              # TypeScript 类型
│   │   └── utils/              # 工具函数
│   ├── Dockerfile
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                     # Python 后端
│   ├── app/                    # 主应用
│   │   ├── api/v1/             # API 路由
│   │   │   ├── endpoints/      # 路由实现
│   │   │   └── router.py       # 路由汇总
│   │   ├── models/             # SQLAlchemy 模型
│   │   │   ├── domain/         # 领域模型
│   │   │   └── tables/         # 数据库表
│   │   ├── schemas/             # Pydantic DTO
│   │   ├── services/           # 业务逻辑
│   │   │   ├── detectors/      # 异常检测算法
│   │   │   ├── indicators/     # 技术指标
│   │   │   └── attribution/    # 归因分析
│   │   ├── agents/             # LangGraph Agent
│   │   │   ├── nodes/          # Agent 节点
│   │   │   ├── tools/          # Agent 工具
│   │   │   └── graphs/         # 工作流图
│   │   ├── db/                 # 数据库连接
│   │   │   ├── session.py      # 会话管理
│   │   │   └── repositories/   # 数据仓储
│   │   ├── cache/              # Redis 缓存
│   │   └── tasks/              # 定时任务
│   ├── scripts/                # 脚本
│   ├── alembic/                # 数据库迁移
│   ├── tests/                  # 测试
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── init.bat                # 初始化脚本
│   └── start.bat               # 启动脚本
│
├── docker-compose.yml           # Docker Compose 配置
├── docker-compose.prod.yml     # 生产环境配置
│
├── docs/                       # 文档
│   ├── architecture.md         # 系统架构
│   ├── getting-started.md      # 快速开始
│   ├── api.md                  # API 接口
│   ├── deployment.md           # 部署指南
│   ├── data-source.md          # 数据源说明
│   └── backend/
│       └── python-development.md  # FastAPI 开发指南
│
└── README.md
```

---

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 20
- Docker >= 24
- Git

### 方式一：Docker 一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/your-org/attribution-analysis.git
cd attribution-analysis

# 复制环境变量
cp .env.example .env
# 编辑 .env 填入必要的配置

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 方式二：本地开发

```bash
# 1. 启动基础设施
docker-compose up -d postgres redis

# 2. 后端开发
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. 前端开发（新窗口）
cd frontend
npm install
npm run dev
```

### 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# 采集数据
python scripts/collect_data.py -m single    # 单只股票
python scripts/collect_data.py -m batch    # 多只股票
python scripts/collect_data.py -m market   # 全市场

# 访问 API 文档
# http://localhost:8000/docs
```

详细说明请参阅 [FastAPI 开发指南](./docs/backend/python-development.md)

---

## 开发计划

| 阶段 | 时间 | 核心任务 |
|------|------|----------|
| **Phase 1** | 第1周 | FastAPI 后端初始化 + A股数据接入（AkShare） |
| **Phase 2** | 第2周 | 数据库模型（PostgreSQL + pgvector）+ CRUD API |
| **Phase 3** | 第3周 | Redis 缓存集成 + API 限流 |
| **Phase 4** | 第4周 | 异常检测算法（8种统计检测）+ 技术指标计算 |
| **Phase 5** | 第5周 | LangGraph Agent 编排 + 经验检索（pgvector） |
| **Phase 6** | 第6周 | 归因分析算法（基期拆解 + 贡献度） |
| **Phase 7** | 第7周 | 报告生成 Agent + AI 业务洞察（LLM） |
| **Phase 8** | 第8周 | Vue 看板 + ECharts 可视化 |
| **Phase 9** | 第9周 | 用户反馈闭环 + 置信度更新 |
| **Phase 10** | 第10周 | Docker 部署 + 生产环境配置 |

> ✅ 已完成

---

## 文档

| 文档 | 说明 |
|------|------|
| [系统架构](./docs/architecture.md) | 系统架构设计、技术选型、模块划分 |
| [快速开始](./docs/getting-started.md) | 环境配置、项目启动、第一个分析示例 |
| [API 接口](./docs/api.md) | 后端 REST API 详细接口定义 |
| [部署指南](./docs/deployment.md) | Docker 部署、生产环境配置 |
| [数据源说明](./docs/data-source.md) | 数据源全景图、接入方式 |
| [FastAPI 开发指南](./docs/backend/python-development.md) | Python 后端初始化、架构、A股数据接入 |

---

## 技术亮点

1. **LangGraph 多 Agent 编排**：官方主力支持，生态完善，多 Agent 协作流畅
2. **双引擎架构**：算法保证精确计算 + AI 理解业务上下文
3. **pgvector 经验累积**：PostgreSQL 内嵌向量，向量检索匹配历史经验，系统越用越聪明
4. **Redis 高性能缓存**：热点数据缓存、API 限流、会话管理
5. **全栈 TypeScript**：前后端类型共享，开发效率高
6. **Docker 微服务**：基于 Docker Compose 的微服务模式，后期可升级 K8s 编排

---

## 联系方式

- 提交 Issue：https://github.com/your-org/attribution-analysis/issues
- 文档问题欢迎提交 PR 完善

# 重构目标与范围

## 一、项目背景

当前 `Attribution_Analysis/backend` 是一个基于 **Python + FastAPI + SQLAlchemy (Async) + PostgreSQL** 构建的智能金融数据归因分析平台。

核心功能：
- **数据采集**：通过 Tushare API / Pytdx / AKShare 采集 K线、财务、融资融券等金融数据
- **K线管理**：日K线 + 17 个技术指标（MA/EMA/MACD/RSI/KDJ/BOLL）的存储与查询
- **操作池**：用户自选股票池的 CRUD + 批量操作（采集、归因分析）
- **归因分析**：股票技术形态检测（金叉、超买、突破等）

## 二、重构目标

### 核心目标
使用 **Java 21 (Virtual Threads) + Spring Boot 3.3** 重写后端，保留 100% 业务功能等价性。

### 成功标准
1. 所有 REST API 端点功能等价（请求/响应格式一致）
2. 数据采集流水线行为一致（Tushare → PostgreSQL）
3. 股票归因分析结果一致（技术指标计算逻辑一致）
4. 操作池 CRUD + 操作历史完整保留
5. 原有 PostgreSQL 数据库可直接复用（共享同一数据库实例）

### 不做的事（Scope Boundaries）
| 排除项 | 原因 |
|---|---|
| 前端 Vue/React | 与后端语言无关，直接复用 |
| AI/RAG 功能 | Phase 2 单独规划 |
| 缓存层（Redis） | Phase 2 按需引入 |
| 性能基准测试 | Phase 2 架构稳定后做 |
| 100% 等价覆盖 Python 边界 case | 先跑通核心路径，边界 case 后续迭代 |

## 三、技术现状分析

### Python 项目规模
- **23 个领域模型** (`src/domain/*/entity.py`)
- **25 个数据库模型** (`src/infrastructure/database/models/`)
- **9 个 API 路由模块** (`src/route/api/v1/`)
- **核心服务**：
  - `StockPoolAppService` - 操作池 CRUD
  - `PoolOperationAppService` - 池操作（采集任务派发）
  - `StockAnalysisService` - 股票归因分析
  - `KlineAppService` - K线查询与采集

### 主要技术栈
- **ORM**：SQLAlchemy 2.0 (async) + Alembic
- **API**：FastAPI 0.115+
- **数据采集**：Tushare Pro API + Pytdx + AKShare
- **数据库**：PostgreSQL 15+ (pgvector 扩展已安装)
- **异步任务**：Python asyncio + threading

### Java 重构价值分析
| 模块 | Python 代码行数 | 重构复杂度 | 优先级 |
|---|---|---|---|
| 领域模型 (Entity) | ~3000 | 低（模板化） | P0 |
| API 路由 | ~2000 | 低（一对一映射） | P0 |
| 数据采集 | ~2500 | **高（业务逻辑核心）** | P0 |
| 技术指标计算 | ~800 | 中（数学公式固定） | P1 |
| 操作池服务 | ~1500 | 中（业务规则多） | P1 |
| 异步任务调度 | ~1000 | 中（框架差异大） | P1 |

## 四、迁移策略

### 策略：渐进式迁移（Parallel Rewrite）
1. **Phase 1**（Week 1-3）：核心骨架 + 简单模块
   - 项目脚手架搭建
   - Entity + Repository 批量生成
   - K线查询 API（最简单的模块验证）

2. **Phase 2**（Week 4-5）：核心业务
   - 操作池 CRUD + 成员管理
   - 数据采集流水线（Tushare）
   - 技术指标计算

3. **Phase 3**（Week 6）：集成与验收
   - 完整 API 端到端测试
   - 数据一致性验证
   - 部署脚本

### 复用策略
- **数据库**：直接复用 PostgreSQL，表结构不变
- **前端**：无需修改，REST API 格式保持一致
- **配置**：环境变量映射（settings → application.yml）
- **测试数据**：复用现有 Tushare token

## 五、关键风险与缓解

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| Tushare API 调用模式差异 | 高 | 使用 Spring WebClient 模拟 Python requests |
| Virtual Threads 性能不确定 | 中 | 先用 ThreadPerTaskExecutor 保守方案 |
| SQLAlchemy → JPA 范式差异 | 中 | JPA Entity 设计参考现有 SQLAlchemy 模型 |
| 技术指标计算不一致 | 高 | 建立单元测试对照 Python 结果 |
| 重构周期过长 | 高 | 每日 Standup，每周验收里程碑 |

## 六、文档目录

```
backend-java/docs/rebuild/
├── 00-overview.md          ← 本文件：目标、范围、策略
├── 01-tech-stack.md        ← JDK 21 + Spring Boot 3.3 选型理由
├── 02-architecture.md       ← 分层架构（DDD + Hexagonal）
├── 03-domain-mapping.md     ← Python → Java 字段映射规则（核心杠杆）
├── 04-data-collection.md    ← Tushare/Pytdx 数据采集设计
├── 05-api-migration.md      ← FastAPI → Spring MVC 路由对照
├── 06-deployment.md         ← 打包、Docker、虚拟线程配置
└── 07-roadmap.md            ← 6 周详细迁移计划
```

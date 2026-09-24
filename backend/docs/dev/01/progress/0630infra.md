# 项目进度快照 — 2026-06-30（infra 重构）

> 供新 Agent 窗口快速上手使用。本文档是 [0630data.md](./0630data.md) 的后续更新，描述 infra 层提取和 app 层完善后的实际代码状态。

---

## 本次变更摘要

1. **提取 `infra/` 基础设施层**：将数据库相关代码从 `app/database/` 迁移到独立的 `infra/database/`，修正 `data/` 依赖 `app/` 的错误方向
2. **完善 `app/` 为纯 HTTP 层**：新增 `middleware/`（请求日志、耗时）和 `handlers/`（全局异常处理）

---

## 当前目录结构（完整）

```
backend/
├── app/                         # HTTP 层（FastAPI 专属）
│   ├── main.py                  # 应用工厂：注册路由/中间件/异常处理/lifespan
│   ├── config.py                # Pydantic Settings，读取 .env
│   ├── dependencies.py          # re-export get_db_session（DI 出口）
│   ├── middleware/
│   │   ├── logging.py           # LoggingMiddleware：记录 method/path/status/耗时
│   │   └── timing.py            # TimingMiddleware：注入 X-Process-Time 响应头
│   ├── handlers/
│   │   └── http_errors.py       # HTTP 4xx/5xx 统一格式；500 不暴露堆栈
│   ├── schemas/
│   │   └── stock.py             # DailyKlineResponse、DailyKlineListResponse、CollectRequest、CollectResponse
│   ├── api/
│   │   ├── router.py            # 汇总路由
│   │   └── v1/
│   │       ├── health.py        # GET /api/v1/health
│   │       └── stocks.py        # GET /stocks/  /stocks/{symbol}  POST /stocks/collect
│   └── services/                # 预留（当前为空）
│
├── infra/                       # 基础设施层（所有域共享）
│   └── database/
│       ├── base.py              # Base = declarative_base()
│       ├── connection.py        # engine、SessionLocal、get_db_session
│       └── models/
│           ├── mixins.py        # TimestampMixin（created_at/updated_at）
│           └── stock.py         # DailyKlineDB，表名 daily_klines
│
├── data/                        # 数据采集域
│   ├── interfaces/
│   │   └── fetcher.py           # FetcherProtocol、CollectParams
│   ├── schemas/
│   │   ├── base.py              # BaseData
│   │   └── kline.py             # DailyKline、StockInfo
│   ├── adapters/
│   │   └── akshare/
│   │       └── fetcher.py       # AkShareFetcher（dispatch 模式）
│   ├── parsers/
│   │   └── kline_parser.py      # DataFrame → list[DailyKline]
│   ├── collectors/
│   │   └── collector.py         # 通用 Collector
│   ├── services/
│   │   └── stock_service.py     # 装配层 + DB CRUD
│   └── scripts/
│       ├── collect_stock.py     # CLI 单只采集
│       └── batch_collect.py     # CLI 批量采集
│
├── test_core.py                 # 验证配置加载
├── test_db.py                   # 验证 infra.database 连接 + 模型
└── test_data.py                 # 验证 AkShareFetcher + StockService
```

---

## 依赖方向（重要）

```
app/      →  infra/database   ✓
data/     →  infra/database   ✓
data/     →  app/             ✗  （已修正，不再存在）

唯一遗留耦合：
infra/database/connection.py  →  app/config.py
（TODO: Phase 3 加 Redis 时将 config.py 提到顶层一并解决）
```

---

## app 层职责划分

| 目录 | 职责 |
|------|------|
| `main.py` | 应用工厂，组装所有组件 |
| `config.py` | 读取 .env，提供 `Settings` 单例 |
| `dependencies.py` | FastAPI 依赖注入的统一出口 |
| `middleware/` | HTTP 横切关注点：日志、耗时 |
| `handlers/` | 全局异常拦截，统一错误响应格式 |
| `schemas/` | API 请求/响应 Pydantic 模型 |
| `api/` | 路由定义 |
| `services/` | 预留（业务编排，当前为空） |

---

## infra 层职责划分

| 文件 | 职责 |
|------|------|
| `database/base.py` | `Base = declarative_base()`，所有 ORM 模型的注册中心 |
| `database/connection.py` | `engine`（连接池）、`SessionLocal`（Session 工厂）、`get_db_session`（上下文管理器） |
| `database/models/mixins.py` | `TimestampMixin`，通过多重继承为模型添加时间戳字段 |
| `database/models/stock.py` | `DailyKlineDB`，日K线表的 ORM 映射 |

### `get_db_session` 双重兼容

```python
# FastAPI Depends（自动管理生命周期）
db: Session = Depends(get_db_session)

# 普通 Python 代码（with 语句）
with get_db_session() as db:
    ...
```

---

## 命名约定（三层对应关系）

| 数据概念 | data 层（管道内） | infra 层（数据库） | app/schemas 层（API） |
|---------|-----------------|-------------------|----------------------|
| 日K线 | `DailyKline(BaseData)` | `DailyKlineDB(Base)` | `DailyKlineResponse` |
| 表名 | — | `daily_klines` | — |

---

## middleware 注册顺序说明

FastAPI/Starlette 中间件的执行顺序与注册顺序**相反**（后注册先执行）：

```python
# main.py 注册顺序：
app.add_middleware(TimingMiddleware)    # 第3层（最内）
app.add_middleware(LoggingMiddleware)   # 第2层
app.add_middleware(CORSMiddleware)      # 第1层（最外，先执行）

# 实际执行顺序：CORS → Logging → Timing → 路由处理 → Timing → Logging → CORS
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查（根路径） |
| GET | `/api/v1/health` | 健康检查（v1） |
| GET | `/api/v1/stocks/` | 查询日K线 |
| GET | `/api/v1/stocks/{symbol}` | 获取指定股票K线 |
| POST | `/api/v1/stocks/collect` | 触发采集并存储 |

---

## 环境配置（.env）

```
DATABASE_URL=postgresql://postgres:xxx@host:5432/attribution
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:xxx@host:5432/attribution
REDIS_URL=redis://localhost:6379/0
```

---

## 当前已完成 / 待开发

```
✅ Phase 1   FastAPI 初始化 + AkShare 日K线采集
✅ Phase 2   数据库模型(DailyKlineDB) + CRUD API
✅           data 层重构：Collector(Fetcher(DataType)) 架构
✅           infra 层提取：database 从 app/ 迁移到 infra/
✅           app 层完善：middleware（日志/耗时）+ handlers（异常处理）

⏳ Phase 3   Redis 缓存 + API 限流（同步将 config 提到顶层）
⏳ Phase 4   异常检测算法（Z-score / IQR / 3σ / Isolation Forest）
⏳ Phase 5   LangGraph Agent 编排（graph/ 模块）
⏳ Phase 6   归因分析 + LLM 报告生成
⏳ Phase 7   新闻情感分析（接入新数据类型）
⏳ Phase 8   tushare 接入（新数据源适配器）
⏳ Phase 9   Vue 前端看板
⏳ Phase 10  Docker 部署
```

---

## 快速启动

```bash
cd backend
.venv\Scripts\activate

# 启动 API 服务
uvicorn app.main:app --reload

# 采集单只股票（30天）
python -m data.scripts.collect_stock 000001 --days 30

# 批量采集（默认5只蓝筹）
python -m data.scripts.batch_collect

# 验证
python test_core.py
python test_db.py
python test_data.py
```

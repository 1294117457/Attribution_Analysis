# 后端架构重构方案

> 基于当前 `backend/` 现状，参考 ID 项目分层设计，迁移为 DDD 域驱动结构。

---

## 一、现状分析与问题

### 当前目录结构

```
backend/
├── app/           ← FastAPI路由 + API Schema
├── infra/         ← 数据库连接 + ORM模型
└── data/          ← 采集适配器 + Collector + 采集Schema + Service
```

### 核心问题

| 问题 | 具体表现 |
|------|---------|
| **职责散乱** | ORM 模型在 `infra/database/models/`，采集 Schema 在 `data/schemas/`，API Schema 在 `app/schemas/`，三套 Schema 概念不统一 |
| **缺少 Repo 层** | `StockService` 直接操作 `db.query(DailyKlineDB)`，Service 既做业务编排又写 SQL，职责混杂 |
| **同步 Session** | 使用同步 `Session`，阻塞 FastAPI 异步事件循环；ID 项目使用 `AsyncSession` |
| **域边界模糊** | `kline` 和 `stock_info` 的逻辑混在同一个 `StockService`，难以独立扩展 |
| **路由 try/except** | `stocks.py` 的 route 层自己 try/except，应由全局 exception handler 统一处理 |
| **data/ 命名歧义** | `data/` 在 Python 项目中通常指原始数据目录，用于业务域容易误导 |

---

## 二、目标架构

### 设计原则（参考 ID 项目）

1. **Route 层**：只做三件事 —— 接收 DTO、调 Service、包 Response，零 try/except
2. **Service 层**：只做业务编排，调用 Repo 和 Collector，不写 SQL
3. **Repo 层**：只做 SQL 读写，无业务规则
4. **Collector 层**：只做外部数据采集（tushare/akshare），不触碰数据库
5. **域自治**：每个业务域（kline/stock_info）内部完整包含自己的 model/schema/repo/service/router

### 目标目录结构

```
backend/src/
│
├── app/                            ← FastAPI 入口（薄层，只做框架配置）
│   ├── main.py                     ← lifespan, CORS, 注册路由
│   ├── dependencies.py             ← get_db (AsyncSession)
│   ├── response.py                 ← 统一响应格式 R.ok() / R.err()
│   └── middleware/
│       ├── __init__.py
│       ├── logging.py              ← 请求日志
│       └── timing.py               ← X-Process-Time header
│
├── infra/                          ← 基础设施（无业务逻辑）
│   ├── config.py                   ← Settings (pydantic-settings)
│   └── database/
│       ├── base.py                 ← declarative_base()
│       ├── connection.py           ← 异步引擎 + get_db() + get_db_context()
│       └── mixins.py               ← TimestampMixin
│
├── collectors/                     ← 数据采集层（独立，不属于任何业务域）
│   ├── interfaces/
│   │   ├── __init__.py
│   │   └── fetcher.py              ← FetcherProtocol, CollectParams, BaseData
│   ├── tushare/
│   │   ├── __init__.py
│   │   └── fetcher.py              ← TushareFetcher（待实现）
│   └── akshare/
│       ├── __init__.py
│       ├── fetcher.py              ← AkShareFetcher（现有迁移）
│       └── parser.py               ← KlineParser（现有迁移）
│
│  ═══════════════ 业务域 ═══════════════════════════════════
│
├── kline/                          ← K线域
│   ├── __init__.py
│   ├── model.py                    ← ORM: DailyKlineDB（从 infra/database/models/ 迁移）
│   ├── schema.py                   ← Pydantic: DailyKline(采集), KlineResponse(API响应)
│   ├── repo.py                     ← SQL: save_batch / query / delete（新增）
│   ├── service.py                  ← 业务: collect_and_save / get_klines（重构）
│   └── router.py                   ← 路由: GET/POST/DELETE /api/klines
│
├── stock_info/                     ← 股票基本信息域
│   ├── __init__.py
│   ├── model.py                    ← ORM: StockInfoDB（从 infra/ 迁移）
│   ├── schema.py                   ← Pydantic: StockInfoResponse, StockListItem
│   ├── repo.py                     ← SQL: get / upsert / list_with_stats
│   ├── service.py                  ← 业务: upsert_info / list_stocks
│   └── router.py                   ← 路由: GET /api/stocks
│
├── indicators/                     ← 技术指标域（计算，不采集，不存储）
│   ├── __init__.py
│   ├── calculator.py               ← pandas: MA / MACD / RSI / KDJ / BOLL
│   ├── schema.py                   ← Pydantic: IndicatorResponse
│   └── router.py                   ← 路由: GET /api/indicators/{symbol}
│
│  ═══════════════ 分析层（未来扩展）══════════════════════════
│
├── news/                           ← 新闻域（Phase 2）
│   └── ...
│
├── analysis/                       ← 数据分析层（Phase 3）
│   ├── anomaly/
│   │   ├── detector.py             ← 异常检测算法
│   │   ├── schema.py
│   │   └── router.py
│   └── attribution/
│       ├── engine.py               ← 归因分析引擎
│       ├── schema.py
│       └── router.py
│
└── agent/                          ← LangGraph Agent（Phase 4）
    ├── graph/
    │   ├── builder.py
    │   └── routers.py
    ├── nodes/
    │   ├── data_node.py            ← 调用 kline.service
    │   ├── anomaly_node.py         ← 调用 analysis.anomaly
    │   └── report_node.py
    ├── tools/
    │   └── stock_tool.py
    └── router.py                   ← POST /api/agent/chat
```

---

## 三、分层职责与调用规则

### 调用链

```
HTTP Request
    ↓
router.py          (接收DTO → 调service → 返回Response，零try/except)
    ↓
service.py         (业务编排 → 调repo + collector，不写SQL)
    ↓                              ↓
repo.py            collectors/akshare 或 collectors/tushare
(只做SQL读写)       (只做外部数据采集，不碰DB)
    ↓
AsyncSession → PostgreSQL
```

### 域间通信规则

```python
# ❌ 禁止：域之间直接 import model 或 repo
# kline/service.py 不能直接 import stock_info/repo.py

# ✅ 正确：通过注入 service 实例协调
# kline/service.py 接收 stock_info_service 参数（依赖注入）
async def collect_and_save(
    self,
    symbol: str,
    db: AsyncSession,
    stock_info_service: StockInfoService,  # 注入
) -> tuple[int, str]:
    ...
```

### 依赖方向（单向，不可逆）

```
agent → analysis → kline/stock_info/news → collectors → infra
                                           ↑
                                    （只有 service 层可以调用）
```

---

## 四、关键重构点

### 4.1 同步 → 异步（重要）

参考 ID 项目的 `infra/database.py`，将同步 Session 改为异步：

```python
# 旧：infra/database/connection.py（同步）
def get_db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 新：infra/database/connection.py（异步，参考ID项目）
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

对应所有 router / service / repo 函数签名改为 `async def`。

### 4.2 新增 Repo 层

将 Service 中的 SQL 操作剥离到 Repo：

```python
# 旧：kline 查询混在 StockService
def get_klines(self, symbol, ...):
    return self.db.query(DailyKlineDB).filter(...).all()

# 新：kline/repo.py
class KlineRepo:
    @staticmethod
    async def query(db: AsyncSession, symbol: str, ...) -> list[DailyKlineDB]:
        stmt = select(DailyKlineDB).where(...)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def save_batch(db: AsyncSession, klines: list[DailyKlineDB]) -> int:
        # upsert or skip duplicates
        ...
```

### 4.3 拆分 Schema

| 旧位置 | 新位置 | 用途 |
|--------|--------|------|
| `data/schemas/kline.py` → `DailyKline` | `kline/schema.py` → `DailyKlineData` | 采集数据结构 |
| `app/schemas/stock.py` → `DailyKlineResponse` | `kline/schema.py` → `KlineResponse` | API 响应 |
| `infra/database/models/stock.py` → `DailyKlineDB` | `kline/model.py` → `DailyKlineDB` | ORM 模型 |

每个域的 `schema.py` 同时包含：采集 Pydantic 模型 + API 请求/响应 DTO，不再分散三处。

### 4.4 路由注册统一化（参考 ID 项目）

```python
# app/main.py（参考 ID 项目 app/routes/__init__.py 模式）
from kline.router import router as kline_router
from stock_info.router import router as stock_info_router
from indicators.router import router as indicators_router

ROUTERS = [
    kline_router,        # /api/klines
    stock_info_router,   # /api/stocks
    indicators_router,   # /api/indicators
]

def register_all_routes(app):
    for router in ROUTERS:
        app.include_router(router)
```

### 4.5 统一响应格式（参考 ID 项目 app/response.py）

```python
# app/response.py
from fastapi.responses import JSONResponse

def ok(data=None, message="success"):
    return {"code": 200, "message": message, "data": data}

def err(message: str, code: int = 400):
    return JSONResponse(
        status_code=code,
        content={"code": code, "message": message, "data": None}
    )
```

路由层统一返回 `R.ok(data)` / `R.err("message")`，不再在 router 里手动构造各种 Response 模型。

---

## 五、文件迁移对照表

| 旧文件 | 新文件 | 操作 |
|--------|--------|------|
| `infra/database/models/stock.py` | `kline/model.py` | 移动 |
| `infra/database/models/stock_info.py` | `stock_info/model.py` | 移动 |
| `infra/database/models/mixins.py` | `infra/database/mixins.py` | 移动 |
| `data/schemas/kline.py` | `kline/schema.py`（合并API schema） | 重构 |
| `app/schemas/stock.py` | 拆入各域 `schema.py` | 重构后删除 |
| `data/services/stock_service.py` | `kline/service.py` + `stock_info/service.py` | 拆分 |
| `app/api/v1/stocks.py` | `kline/router.py` + `stock_info/router.py` | 拆分 |
| `data/adapters/akshare/fetcher.py` | `collectors/akshare/fetcher.py` | 移动 |
| `data/parsers/kline_parser.py` | `collectors/akshare/parser.py` | 移动 |
| `data/interfaces/fetcher.py` | `collectors/interfaces/fetcher.py` | 移动 |
| `data/collectors/collector.py` | `collectors/collector.py` | 移动 |
| `infra/database/base.py` | `infra/database/base.py` | 保留 |
| `infra/database/connection.py` | `infra/database/connection.py` | 重构为异步 |
| `infra/config.py` | `infra/config.py` | 保留 |

---

## 六、分阶段实施计划

### Phase 1（当前）：核心域 + 采集可视化

- [ ] 搭建 `src/` 新目录结构
- [ ] 迁移 `infra/` 并改为异步引擎
- [ ] 实现 `kline/` 域（model + repo + service + schema + router）
- [ ] 实现 `stock_info/` 域
- [ ] 迁移 `collectors/akshare/`
- [ ] 实现 `indicators/`（MA/MACD/RSI，pandas计算）
- [ ] 前端 K 线图（ECharts）

### Phase 2：数据扩展

- [ ] `collectors/tushare/`（TushareFetcher）
- [ ] `news/` 域（新闻采集 + 存储）
- [ ] 补全 `stock_info` 行业/市值字段

### Phase 3：分析层

- [ ] `analysis/anomaly/`（异常检测）
- [ ] `analysis/attribution/`（归因分析）

### Phase 4：Agent

- [ ] `agent/`（LangGraph，调用 analysis + 各域 service）

---

## 七、现有代码可直接复用的部分

| 模块 | 可复用程度 | 说明 |
|------|----------|------|
| `AkShareFetcher` | 直接复用 | 移动到 `collectors/akshare/` 即可 |
| `KlineParser` | 直接复用 | 移动到 `collectors/akshare/parser.py` |
| `FetcherProtocol` / `CollectParams` | 直接复用 | 移动到 `collectors/interfaces/` |
| `Collector` | 直接复用 | 移动到 `collectors/collector.py` |
| `DailyKlineDB` ORM | 直接复用 | 移动到 `kline/model.py` |
| `StockInfoDB` ORM | 直接复用 | 移动到 `stock_info/model.py` |
| `TimestampMixin` | 直接复用 | 移到 `infra/database/mixins.py` |
| `StockService` 逻辑 | 拆分复用 | K线逻辑 → `kline/service.py`，stock_info 逻辑 → `stock_info/service.py` |
| Route 处理逻辑 | 部分复用 | 去掉 try/except，改用全局 exception handler |

---

## 八、参考项目对比

| 层 | ID 项目 | 本项目（目标） |
|----|---------|--------------|
| 路由 | `app/routes/` | `kline/router.py` 等（域内） |
| Schema | `app/schemas/` | 各域 `schema.py`（域内）|
| 业务 | `services/` | 各域 `service.py`（域内）|
| 持久化 | `repositories/` | 各域 `repo.py`（域内）|
| ORM | `models/` | 各域 `model.py`（域内）|
| 外部集成 | `infra/ai/` | `collectors/`（数据采集专用）|
| 基础设施 | `infra/` | `infra/`（保持一致）|

主要差异：ID 项目是扁平分层，本项目按域聚合（DDD 风格），适合未来多域并行扩展。

# Phase 2 DDD 重构文档索引

> 基于 Phase 1 的分层架构，采用 **DDD（领域驱动设计）** 进行重构
> 目标：建立清晰的领域层，实现路由层、应用层、领域层、基础设施层的分离
> 重构策略：彻底替换，不考虑向后兼容

---

## 文档列表

| 文件 | 内容 | 对应代码目录 |
|------|------|------------|
| [01-domain.md](./01-domain.md) | 领域层：实体、值对象、领域事件、BO/VO Schema | `src/domain/` |
| [02-infrastructure.md](./02-infrastructure.md) | 基础设施层：数据库、ORM 模型、仓储实现 | `src/infrastructure/` |
| [03-application.md](./03-application.md) | 应用层：应用服务（编排业务用例） | `src/application/` |
| [04-route.md](./04-route.md) | 路由层：API 路由、DTO 定义、统一响应 | `src/route/` |
| [05-collectors.md](./05-collectors.md) | 防腐层：外部数据采集（ACL） | `src/infrastructure/collectors/` |
| [06-migration.md](./06-migration.md) | 迁移指南：从 Phase 1 到 Phase 2 | - |

---

## DDD 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                       Route Layer (路由层)                         │
│                       src/route/                                 │
│   ┌───────────────────┬────────────────────┐                      │
│   │   kline_router    │   stock_router     │                      │
│   │   DTO (请求)      │   DTO (请求)        │                      │
│   └─────────┬─────────┴─────────┬──────────┘                      │
│             │                   │                                 │
│             ▼                   ▼                                 │
│   ┌─────────────────────────────────────────┐                    │
│   │        Application Layer (应用层)           │                 │
│   │         src/application/                   │                  │
│   │  ┌─────────────────┬─────────────────┐    │                  │
│   │  │ KlineAppService │ StockAppService │    │                  │
│   │  │   (用例编排)    │   (用例编排)      │    │                  │
│   │  └────────┬────────┴────────┬────────┘    │                  │
│   └───────────┼─────────────────┼─────────────┘                  │
│               │                 │                                  │
│               ▼                 ▼                                  │
│   ┌─────────────────────────────────────────┐                    │
│   │          Domain Layer (领域层)             │                  │
│   │           src/domain/                     │                  │
│   │  ┌─────────────────┬─────────────────┐    │                  │
│   │  │ KlineAggregate  │ StockInfoAgg    │    │                  │
│   │  │  - KlineVO      │  - StockInfo    │    │                  │
│   │  │  - KlineEntity  │                 │    │                  │
│   │  │  - KlineEvent   │                 │    │                  │
│   │  └─────────────────┴─────────────────┘    │                  │
│   └─────────────────────────────────────────┘                    │
│                           │                                       │
│                           ▼                                       │
│   ┌─────────────────────────────────────────┐                    │
│   │    Infrastructure Layer (基础设施层)         │                │
│   │       src/infrastructure/                  │                │
│   │  ┌─────────────────┬─────────────────┐    │                  │
│   │  │  Repository     │  Collectors     │    │                  │
│   │  │  (持久化实现)    │  (ACL 防腐层)    │    │                  │
│   │  │  KlineRepo      │  AkShareFetcher │    │                  │
│   │  │  StockRepo      │  TushareFetcher │    │                  │
│   │  └─────────────────┴─────────────────┘    │                  │
│   │  ┌─────────────────────────────────────┐ │                  │
│   │  │    infra/ (DB 连接、配置)             │ │                  │
│   │  └─────────────────────────────────────┘ │                  │
│   └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 目标目录结构

```
backend/src/
├── main.py                          # FastAPI 应用入口
├── dependencies.py                  # 依赖注入
├── config.py                        # 配置（从 infra/config.py 迁移）
│
├── domain/                          # ⭐ 领域层（DDD 核心）
│   ├── __init__.py
│   ├── base.py                      # 领域基类（Entity、ValueObject）
│   ├── events.py                    # 领域事件定义
│   ├── kline/
│   │   ├── __init__.py
│   │   ├── entity.py                # KlineAggregate（聚合根）
│   │   ├── value_objects.py         # KlineId、TradeDate 等值对象
│   │   ├── events.py                # KlineCollected 等领域事件
│   │   ├── schemas.py               # KlineVO、KlineBO 等
│   │   └── repository.py            # KlineRepository 接口（抽象）
│   └── stock_info/
│       ├── __init__.py
│       ├── entity.py                # StockInfoAggregate
│       ├── value_objects.py         # StockCode 等值对象
│       ├── schemas.py               # StockInfoVO 等
│       └── repository.py            # StockInfoRepository 接口
│
├── application/                     # ⭐ 应用层（用例编排）
│   ├── __init__.py
│   ├── kline_service.py             # KlineAppService（采集+查询用例）
│   ├── stock_service.py              # StockAppService（股票管理用例）
│   └── dto/                          # 应用层 DTO
│       ├── __init__.py
│       ├── kline.py                 # 请求/响应 DTO
│       └── stock.py
│
├── infrastructure/                  # ⭐ 基础设施层
│   ├── __init__.py
│   ├── config.py                    # 配置（pydantic-settings）
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base.py                  # DeclarativeBase
│   │   ├── connection.py            # 异步引擎、Session
│   │   ├── models/                  # ORM 模型（PO）
│   │   │   ├── __init__.py
│   │   │   ├── kline.py             # DailyKlineDB
│   │   │   └── stock_info.py        # StockInfoDB
│   │   └── mixins.py                # TimestampMixin
│   │
│   ├── repositories/                # 仓储实现（实现 domain 层接口）
│   │   ├── __init__.py
│   │   ├── kline_repository.py     # KlineRepoImpl
│   │   └── stock_repository.py      # StockRepoImpl
│   │
│   └── collectors/                   # ACL 防腐层（采集器）
│       ├── __init__.py
│       ├── interfaces.py             # FetcherProtocol
│       ├── base.py                   # Collector 基类
│       └── akshare/
│           ├── __init__.py
│           ├── fetcher.py            # AkShareFetcher
│           └── parser.py             # KlineParser
│
└── route/                            # ⭐ 路由层（API 端点）
    ├── __init__.py
    ├── api/
    │   ├── __init__.py
    │   ├── v1/
    │   │   ├── __init__.py
    │   │   ├── kline.py              # K线路由
    │   │   └── stock.py              # 股票路由
    │   └── router.py                 # API 路由聚合
    └── schemas/                       # API 响应 Schema
        ├── __init__.py
        └── response.py               # 统一响应格式
```

---

## 核心概念说明

### 1. 聚合 (Aggregate)

聚合是一组相关领域对象的集合，有明确的边界。聚合根（Aggregate Root）是聚合内唯一对外暴露的入口。

| 聚合 | 聚合根 | 职责 |
|------|--------|------|
| **KlineAggregate** | `Kline` | 管理日K线数据，是查询和采集的核心对象 |
| **StockInfoAggregate** | `StockInfo` | 管理股票基本信息 |

### 2. 值对象 (Value Object)

值对象是没有唯一标识的不可变对象，通过其属性值来定义。

| 值对象 | 属性 | 用途 |
|--------|------|------|
| `StockCode` | code: str | 股票代码，封装验证逻辑 |
| `TradeDate` | date: date | 交易日期，封装日期格式转换 |
| `Money` | amount: float, currency: str | 金额，支持精度处理 |

### 3. 领域事件 (Domain Event)

领域事件表示领域中已发生的重要业务事件，用于解耦和追踪。

| 事件 | 触发时机 | 用途 |
|------|----------|------|
| `KlineCollected` | 成功采集K线后 | 触发后续业务（如通知、缓存更新） |
| `StockInfoUpdated` | 股票信息更新后 | 同步其他系统 |

### 4. 仓储 (Repository)

仓储是领域对象持久化的抽象，定义在领域层，实现放在基础设施层。

```python
# 领域层：定义接口
class KlineRepository(Protocol):
    async def save(self, kline: Kline) -> None: ...
    async def find_by_symbol(self, symbol: str) -> list[Kline]: ...

# 基础设施层：实现
class KlineRepoImpl:
    async def save(self, kline: Kline) -> None:
        # 具体数据库操作
        ...
```

### 5. 防腐层 (ACL)

防腐层（Anti-Corruption Layer）封装对外部系统的调用，保护领域模型不受外部污染。

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Application    │ ───▶ │     Domain      │ ───▶ │  Repository     │
│    Service      │      │    (纯净)       │      │  (持久化)       │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                              ▲
                              │ 领域事件
                              │
                       ┌──────┴──────┐
                       │  Collectors │
                       │   (ACL)     │
                       └─────────────┘
```

---

## 迁移概览

| Phase 1 | Phase 2 (DDD) |
|---------|---------------|
| `data/services/stock_service.py` | `application/kline_service.py` + `application/stock_service.py` |
| `data/schemas/kline.py` | `domain/kline/schemas.py` + `domain/kline/entity.py` |
| `data/interfaces/fetcher.py` | `infrastructure/collectors/interfaces.py` |
| `data/collectors/` | `infrastructure/collectors/` |
| `app/api/v1/stocks.py` | `route/api/v1/kline.py` + `route/api/v1/stock.py` |
| `app/main.py` | `src/main.py`（重写） |
| - | 新增：`domain/` 领域层 |

---

## 开发顺序建议

```
Step 1  domain/base.py              领域基类（Entity、ValueObject）
Step 2  domain/kline/               定义 Kline 聚合（entity、schemas、repository接口）
Step 3  domain/stock_info/          定义 StockInfo 聚合
Step 4  infrastructure/database/    数据库连接、ORM 模型（PO）
Step 5  infrastructure/repositories/ 仓储实现
Step 6  infrastructure/collectors/   采集器（AkShareFetcher）
Step 7  application/                应用服务
Step 8  route/                      API 路由
Step 9  main.py                      应用入口
```

---

## 依赖安装

```bash
pip install fastapi uvicorn[standard] sqlalchemy asyncpg pydantic-settings akshare pandas
```

---

## 注意事项

1. **领域层纯净性**：领域层不依赖任何外部库（除了 Python 标准库），确保业务逻辑可测试
2. **依赖方向**：路由层 → 应用层 → 领域层 → 基础设施层，依赖只能向内
3. **仓储实现分离**：Repository 接口在领域层，实现类在基础设施层，通过依赖注入组合
4. **事件驱动**（可选）：可用 `evtor` 或 `litestar` 的事件机制实现领域事件传播

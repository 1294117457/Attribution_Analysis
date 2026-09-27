# 采集器架构（Mermaid）

> 与 `数据链路uml图设计规范.md` 的 PlantUML 规范**互补**，不替换。
> 本文档用 mermaid 描述采集器层（`infrastructure/collectors/`）的**整体架构**与**关键路径**。
>
> 适用范围：仅 collector 层（协议 / 注册中心 / 4 个数据源 fetcher），不展开应用层业务。

---

## 1. 静态结构（类图）

```mermaid
classDiagram
    class BaseCollector {
        <<abstract>>
        +SOURCE_NAME: str
        +source_name: str
        #_logger
        +_log(level, msg, **kwargs)
        +_wrap_error(msg, err) RuntimeError
    }

    class CollectParams {
        <<dataclass>>
        +symbol: Optional[str]
        +start_date: Optional[date]
        +end_date: Optional[date]
        +days: int = 30
        +adjust: str = "qfq"
        +list_status: str = "L"
        +name: Optional[str]
    }

    class KlineFetcher {
        <<protocol, runtime_checkable>>
        +fetch(params) list
        +source_name* str
    }

    class MinuteKlineFetcher {
        <<protocol, runtime_checkable>>
        +fetch_minute_klines(symbol, interval, count, name) list
        +source_name* str
    }

    class StockBasicFetcher {
        <<protocol, runtime_checkable>>
        +fetch_stock_basic(params) list
        +source_name* str
    }

    class DailyBasicFetcher {
        <<protocol, runtime_checkable>>
        +fetch_daily_basic(trade_date) list
        +source_name* str
    }

    class ConceptFetcher {
        <<protocol, runtime_checkable>>
        +fetch_concept_list() list
        +fetch_concept_stocks(name) list
        +fetch_concepts_by_stock(symbol) list
        +source_name* str
    }

    class TushareFetcher {
        +SOURCE_NAME = "Tushare"
        +fetch(params) list[KlineBO]
        +fetch_stock_basic(params) list[StockInfoBO]
        +fetch_daily_basic(trade_date) list[FinDailyBasicBO]
    }

    class PytdxFetcher {
        +SOURCE_NAME = "Pytdx"
        +fetch_minute_klines(...) list[MinuteKlineBO]
    }

    class AkShareConceptFetcher {
        +SOURCE_NAME = "AkShare-THS"
        +fetch_concept_list() list
        +fetch_concept_info_ths(name) Snapshot
        +fetch_concept_index_ths(name, start, end) list
        +fetch_concept_stocks(name) []  // 不支持
        +fetch_concepts_by_stock(symbol) []  // 不支持
    }

    class AdataConceptFetcher {
        +SOURCE_NAME = "Adata-THS"
        +fetch_concepts_by_stock(symbol) list
        +fetch_concept_list() []  // 废弃
        +fetch_concept_stocks(name) []  // 废弃
    }

    TushareFetcher       --|> BaseCollector
    PytdxFetcher         --|> BaseCollector
    AkShareConceptFetcher --|> BaseCollector
    AdataConceptFetcher  --|> BaseCollector

    TushareFetcher ..|> KlineFetcher
    TushareFetcher ..|> StockBasicFetcher
    TushareFetcher ..|> DailyBasicFetcher
    PytdxFetcher   ..|> MinuteKlineFetcher
    AkShareConceptFetcher ..|> ConceptFetcher
    AdataConceptFetcher   ..|> ConceptFetcher

    KlineFetcher ..> CollectParams : 使用
    StockBasicFetcher ..> CollectParams : 使用
```

**关键点**

- **结构化子类型**（`..|>` 表示 Protocol 实现）：fetcher **不显式继承**协议，duck typing 自动满足
- 一个 `TushareFetcher` 同时实现 3 个协议（日K线 / 股票基本信息 / 日频估值），节省实例化开销
- 概念 fetcher 是"互补型"分工：akshare 负责清单/行情/指数 K，adata 独家负责反查

---

## 2. 注册中心（启动期粘合层）

```mermaid
flowchart LR
    subgraph startup["应用启动 (main.py lifespan)"]
        direction TB
        lifespan["setup_default_registry()"]
    end

    subgraph registryNode["FetcherRegistry (singleton)"]
        direction TB
        providers["_providers<br/>Protocol → instance"]
        factories["_factories<br/>Protocol → factory"]
    end

    subgraph instances["单例 (低并发路径)"]
        t1["TushareFetcher"]
        p1["PytdxFetcher"]
        a1["AkShareConceptFetcher"]
    end

    subgraph factory_funcs["工厂 (高并发池路径)"]
        t2["lambda: TushareFetcher(KlineBO)"]
        p2["PytdxFetcher()"]
        a2["AkShareConceptFetcher()"]
        ad2["AdataConceptFetcher()"]
    end

    subgraph protocolSlots["协议槽 (Protocol keys)"]
        KlineF["KlineFetcher"]
        StockF["StockBasicFetcher"]
        DailyF["DailyBasicFetcher"]
        MinF["MinuteKlineFetcher"]
        ConceptF["ConceptFetcher"]
    end

    lifespan -- "register_instance" --> providers
    lifespan -- "register_factory"  --> factories

    providers -. 注册 .-> t1
    providers -. 注册 .-> p1
    providers -. 注册 .-> a1

    factories -. 注册 .-> t2
    factories -. 注册 .-> p2
    factories -. 注册 .-> a2
    factories -. 注册 .-> ad2

    t1 -. 实现 .-> KlineF
    t1 -. 实现 .-> StockF
    t1 -. 实现 .-> DailyF
    p1 -. 实现 .-> MinF
    a1 -. 实现 .-> ConceptF
    ad2 -. 实现 .-> ConceptF

    classDef regBoxStyle fill:#FFE0B2,stroke:#E65100,color:#000
    class registryNode regBoxStyle
```

**两种注册模式**

| 模式 | API | 适用场景 | 当前用法 |
| --- | --- | --- | --- |
| 单例 | `register_instance(Protocol, obj)` | 无状态 / 内部已做池化 | 路由层（低 QPS） |
| 工厂 | `register_factory(Protocol, lambda)` | 有状态 / 需并发隔离 | 后台采集池（每 worker 新实例） |

**降级策略**：`create()` 找不到工厂时降级取单例；都不存在则抛 `KeyError`。

---

## 3. 运行时调用流（一次 K 线采集）

```mermaid
sequenceDiagram
    autonumber
    participant Client as 前端 / 客户端
    participant Route as route/api/v1/kline.py
    participant Service as application/kline_service.py
    participant Reg as registry.get(KlineFetcher)
    participant Tushare as TushareFetcher (单例)
    participant DB as 数据库
    participant Remote as Tushare 远端 API

    Client->>Route: POST /api/v1/kline/collect
    activate Route
    Route->>Service: collect(request, fetcher)
    activate Service

    Note over Service: _lookup_name(symbol)<br/>优先复用本地 stock_infos

    Service->>DB: SELECT name FROM stock_infos WHERE symbol=?
    DB-->>Service: "平安银行" (可能为空)

    Service->>Service: params = CollectParams(symbol=..., name=prefetched)
    Service->>Reg: fetcher.fetch(params)
    activate Reg
    Reg-->>Tushare: (实际是单例转发)
    deactivate Reg

    activate Tushare
    alt params.name 已注入
        Tushare->>Tushare: name 走缓存<br/>(不再打 stock_basic)
    else 本地查不到 name
        Tushare->>Remote: pro.stock_basic(ts_code=...)
        Remote-->>Tushare: name
    end

    Tushare->>Remote: pro.daily(ts_code, start, end)
    Remote-->>Tushare: DataFrame
    Tushare->>Tushare: TushareKlineParser.parse()
    Tushare-->>Service: list[KlineBO]
    deactivate Tushare

    Service->>Service: to_entity() + 计算指标
    Service->>DB: UPSERT tech_klines + indicators
    DB-->>Service: ok
    Service-->>Route: KlineCollectResponse
    deactivate Service
    Route-->>Client: 200 OK
    deactivate Route
```

**关键观察**

1. 业务层（Route / Service）**全程只持有协议类型 `KlineFetcher`**，不知道也不关心 `TushareFetcher`
2. fetcher 选择在 `setup_default_registry()` 启动期一次性决定，运行时只读
3. name 解析做了**三级缓存**：本地 DB → fetcher 内存缓存 → 远端 stock_basic，避免每个新 symbol 多打一次 Tushare

---

## 4. 各 fetcher 负责的数据矩阵

| fetcher | 协议 | 数据 | 远端调用 |
| --- | --- | --- | --- |
| `TushareFetcher` | KlineFetcher | 日 K 线（开高低收/成交量/涨跌幅） | `pro.daily()` |
| `TushareFetcher` | StockBasicFetcher | 股票基本信息（代码/名称/行业/上市日期） | `pro.stock_basic()` |
| `TushareFetcher` | DailyBasicFetcher | 日频估值（PE/PB/PS/总市值/换手率） | `pro.daily_basic()` |
| `PytdxFetcher` | MinuteKlineFetcher | 1/5/15/30/60 分钟 K 线 | 通达信公网 `get_security_bars()` |
| `AkShareConceptFetcher` | ConceptFetcher | 概念清单 / 行情快照 / 指数日 K | `ak.stock_board_concept_*_ths()` |
| `AdataConceptFetcher` | ConceptFetcher | 股票→概念反查（含入选理由） | `adata.stock.info.get_concept_ths()` |

> ConceptFetcher 是"协议组合"：akshare 和 adata 都注册到同一个协议槽，调用方通过能力判断（`fetch_concepts_by_stock` 仅 adata 支持）选择具体 fetcher。

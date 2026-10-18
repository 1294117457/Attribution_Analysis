# DDD 架构规范

> 本文档只描述**架构分层原则**，与具体语言无关。
> 代码示例仅用于说明组织方式，不代表任何特定语言实现。

---

## 1. 分层总览

```
┌─────────────────┐
│ interface (接口) │  HTTP / RPC / 调度入口、请求响应 DTO
└────────┬────────┘
         ↓ 调
┌─────────────────┐
│  application     │  用例编排
│  (应用服务层)     │  事务、权限、缓存、幂等
└────────┬────────┘
         ↓ 调
┌─────────────────┐
│    domain        │  实体 / 值对象 / 仓储接口 / 领域服务
│   (领域层)        │  纯领域知识，无任何框架依赖
└────────┬────────┘
         ↑ 实现
┌─────────────────┐
│ infrastructure   │  持久化、外部 SDK 适配、配置、异常处理
└─────────────────┘
```

依赖方向**严格自上而下**：`interface → application → domain ← infrastructure`。
`domain` 不依赖任何外层，外层实现 `domain` 定义的接口。

> **命名约定**：本规范中 4 层使用 `interface`（不要用 `route`、`api`、`.api`、`web` 等替代名）。
> 历史原因 `route/` 曾经是 interface 的旧名，已统一改名为 `interface/`。
> 但 `interface/` **内部**的子结构必须用 `route/`（见 §2.3），别在 `interface/` 下直接放 `route_xxx.py`。

---

## 2. 各层职责与边界

### 2.1 domain（领域层）

领域层是**业务核心**，只表达"业务是什么"，不表达"怎么落到技术栈上"。

#### 内容组成

| 概念 | 定义 | 举例 |
|---|---|---|
| **entity** | 有唯一标识 + 有生命周期的领域对象。从持久层读入、承载核心业务规则 | `Kline`、`StockInfo`、`StockPool` |
| **vo**（value object） | 用值描述、没有身份的对象。可加校验、可传递、可组合 | `IndicatorValue`、`DateRange`、`Schedule` |
| **repository（接口）** | 实体持久化的**抽象接口**。定义在 domain 层，**由 infrastructure 实现** | `KlineRepository`、`StockPoolRepository` |
| **service**（领域服务） | 一段领域逻辑**不适合放在任何一个 entity 上**时（跨多对象、通用算法），用领域服务承载 | `IndicatorCalculator` |

#### 领域服务的特点

- 只依赖 domain（entity / VO / repository 接口），**不依赖任何外部 SDK**
- 不调 HTTP、不发 MQ、不取系统时钟
- 可以读 repository 接口查数据，但**绝不持久化**（持久化由 ApplicationService 管事务）
- 通常**没有副作用**（无 IO、无状态变更）
- 可独立单测，不需要外部容器

#### entity 与领域服务的分工

| 谁 | 管什么 |
|---|---|
| **entity** | 只动自己的状态、判断、能力（"我"的事） |
| **领域服务** | 跨多对象、纯算法（"我与世界共同的事"，但不写） |
| **ApplicationService** | 动多 entity + 外部（"我与世界的协作"，含 IO 与调度） |

#### 反例

- ❌ 在 ApplicationService 里写 "RSI 怎么算" 这种算法 → 应放领域服务
- ❌ 在 entity 里调外部 SDK → 应通过 ApplicationService 编排
- ❌ 在 repository 接口里加业务规则 → repository 只做"读出来 / 存进去"

---

### 2.2 application（应用服务层）

#### 用途

**编排一个完整业务用例**——一个方法对应一个"用户意图"（开始采集、取消操作、查询面板）。

#### 特点

1. **管事务边界**
2. **管权限 / 日志 / 缓存 / 幂等**：这里的"管"指**决定策略**（要不要缓存、TTL 多长、失败怎么降级）；Redis、单飞锁、重试这些**机制**由 infrastructure 实现
3. **调外部端口**（HTTP / MQ / 调度 / 时钟 / 外部 SDK）
4. 一个方法对应一个"用户意图"

#### 子结构

| 目录 | 职责 |
|---|---|
| `service/` | AppService 实现，编排用例。下可分 `service/collect/`（入库 service）+ `service/query/`（实时查询 service） |
| `bo/` | 外部数据进入系统时的载体（Business Object）。`bo/tech/`、`bo/capital/`、`bo/fundamental/` 等按 facet 分子目录 |
| `port/` | 对外抽象契约（接口、参数、port 契约级错误；不含限流/重试等机制） |
| `dto/` | **不保留**——DTO 放在 `interface/dto/`，见 §2.3 |

#### service/ 的子分类

当 service 数量较多（≥15 个）且存在"主要做入库"和"主要做实时查询"两类时，建议把 service 文件按主职责分目录：

| 子目录 | 职责 | 例子 |
|---|---|---|
| `service/collect/` | `collect()` 写库为主；scheduler + HTTP `/run/{name}` 都调它 | `AdjFactorService`、`MarginService` |
| `service/query/` | `get()` 实时查询为主；HTTP `/query/{name}?symbol=xxx` 调它 | `MinuteKlineService`、`DailyKlineService.get()` |

**注意**：service 同时实现 `collect()` + `get()` 是允许的，分目录是按"主职责"分类，不是按方法名。

#### port 的组成

一个 port 是一份**契约**，下面几样东西都属于契约，和接口定义放在一起（`application/port/` 下）：

| 组成 | 说明 | 举例 |
|---|---|---|
| 接口 | 抽象方法 / Protocol | `DataPort.fetch`、`SchedulerPort.upsert` |
| 参数类型 | 入参模型，带校验 | `MoneyflowParams`、`MinuteKlineParams` |
| port 契约级错误 | 调用方需要据此决定 重试 / 换源 / 降级；由 SDK 错误翻译而来 | `RateLimited`、`SourceUnavailable` |

注意：业务级异常（参数/能力合规）属于**领域知识**，放在 `domain/exceptions.py`，参见 §2.4「异常分层」。

port 的设计原则：

- **只描述"要什么"，不描述"怎么取"**：参数用业务语义（6 位代码、`date`、交易日数），不出现某个 SDK 特有的东西（`ts_code`、`"20261013"` 字符串、"最近 N 根"）。这些转换在 adapter 里做。
- **实现方的属性不进 port**：数据源名称、优先级、限流分组等由 infrastructure 自己声明。
- **参数类型尽量收紧**：可选值用枚举，范围用声明式约束，禁止多余字段。错误的参数应在入口报错，而不是在底层被吞掉变成"无数据"。
- **不包含限流 / 重试这种机制实现**：port 是"要什么"（契约），不是"怎么取"（机制）。Redis 限流、退避重试这种**机制**放在 `infrastructure/`（如 `throttler.py` / `retry.py`），用装饰器或函数暴露给 service 使用。ApplicationService 决定「要不要限流、限多少」这种**策略**。

**BO 与 domain VO 的区别**：BO 是外部数据进入系统时的载体，字段跟着数据源走，通常借助校验框架（如 pydantic）做类型转换，属于 port 契约；domain VO 表达业务概念，零外部依赖。BO 通过 `to_entity()` 转成 domain 对象后再落库或参与业务计算。

#### 反例

- ❌ 在 ApplicationService 里写 RSI 计算
- ❌ 让 AppService 跨层直接拿 ORM Session
- ❌ 让 AppService 同时是"查询器"和"采集器"（职责混在一起）
- ❌ port 的参数或返回类型引用 `interface/dto`（application 反向依赖 interface）
- ❌ 应用层内部用"字符串名 + dict"调用 port（放弃类型检查；按名调用只留给 HTTP / Agent 等运行时才知道调哪个接口的入口）

---

### 2.3 interface（接口层）

#### 职责

- HTTP / RPC / 调度**入口**
- 请求解析、参数校验
- 响应序列化
- **不包含业务规则**

#### 子结构

```
interface/
├── route/                  ← 路由文件目录（每个具体路由一个文件）
│   ├── user.py             ← 例：用户管理
│   ├── auth_login.py       ← 例：登录
│   ├── auth_register.py    ← 例：注册
│   └── ...                 ← 一个路由文件只装一个业务子模块
├── deps.py                 ← route 层横切依赖（如 get_current_user / require_role）
└── dto/                    ← 接口层 DTO（请求 / 响应）
    ├── request/            ← 入参 DTO，对应外部协议
    └── response/           ← 出参 DTO，含通用响应容器（如 Page<T>）
```

**强约束**：
- ❌ 不要在 `interface/` 下直接放 `route_xxx.py`（如 `route_user.py` / `route_auth.py`）——这种散文件会随着 endpoint 增长迅速失控
- ❌ 不要把"全部路由塞进一个 `route.py`"——一个 `route.py` 经常膨胀到 500+ 行
- ✅ 所有路由文件统一收进 `route/` 目录，按**业务子模块**（不是 HTTP method）分文件
- ✅ `route/` 目录的每个文件只装**一个**业务子模块的路由（如 `auth_login.py` / `auth_password.py` / `user.py` / `role.py`）

**命名建议**：
- 一个文件 = 一个子资源组：`auth_login.py`（登录相关）/ `auth_password.py`（改密、忘记密码）/ `user.py`（用户管理）
- 不要用 HTTP method 命名（不要 `auth_post.py` / `auth_get.py`）
- 文件名一般用**单数**（一个资源一个文件）

#### deps.py 放什么

`deps.py` 装**给 route 用的横切依赖**——这些不是"业务 service 的 DI 工厂"，而是 route 层的辅助 Depends：

| 类型 | 例子 |
|---|---|
| 当前用户解析 | `get_current_user_id`、`get_current_user` |
| 权限断言 | `require_role(...)`、`require_permission(...)` |
| 通用 guard | `get_tenant_id`、`get_request_id` |

**原则**：`deps.py` **不**组装业务 service——业务 service 工厂在 `infrastructure/di/`（见 §2.4）。

#### 为什么 DTO 放在 interface 而非 application

- DTO 是**协议载体**（JSON / protobuf / message），与具体传输方式绑定
- ApplicationService 不应知道"外面长什么样"，它只接收语义化参数、返回语义化结果
- 同一应用服务可能被 HTTP、调度、MQ 共用，DTO 各端各自管理即可

#### 应用服务到 DTO 的转换在哪做

- 在 route 层的 controller / handler 里**手动转换**，或借助 assembler
- 不在 entity 上做（entity 不感知协议）
- 不在 application 层做（application 不知道协议）

---

### 2.4 infrastructure（基础设施层）

对**外**实现 `domain/repository` 接口，对**外**实现 `application/port` 接口。

#### 子结构

```
infrastructure/
├── adapter/                ← 外部 SDK / 调度器的适配器（如 Tushare、AKShare、定时调度）
├── persistence/            ← domain/repository 的持久化实现（ORM、SQL、缓存）
│   ├── models/             ← ORM 模型
│   └── repositories/       ← domain/repository 的 SQL/ORM 实现
├── di/                     ← DI 工厂（依赖注入）
│   ├── __init__.py         ← re-export
│   └── ...                 ← 按资源类型分文件
├── throttler.py            ← 限流（Redis 令牌桶），@throttle 装饰器
├── retry.py                ← 重试，@retry_on_rate_limited + fetch_with_retry()
├── cache/                  ← Redis 缓存机制
├── exception/              ← 基础设施层异常
└── lifespan.py             ← lifespan 启动初始化（init_*_registry）
```

**强约束**：
- ✅ `infrastructure/di/` 是一个**目录**（不是 `di.py` 单文件）——因为不同资源的 DI 工厂天然会拆成多个文件
- ✅ `infrastructure/di/` 下按资源类型分文件（`db_session.py` / `redis_session.py` / `auth.py` ...）
- ❌ 不要把所有 DI 工厂塞进 `infrastructure/di.py` 一个文件
- ❌ 不要在 `infrastructure/di/` 下放非 DI 工厂（如 `init_*_registry()`）——这种是 lifespan 初始化器，应放 `lifespan.py`

#### 各 context 的 DI 自管理（重要）

**每个 context 自己负责自己的业务 DI**，不放在 `shared/` 下：

```
contexts/auth/infrastructure/di/
├── __init__.py
└── auth_service.py         # get_auth_service / get_password_hasher / get_jwt_service ...

contexts/market/infrastructure/di/
├── __init__.py
├── stock_info.py           # get_stock_info_service
└── concept.py              # get_concept_service

contexts/collect/infrastructure/di/
├── __init__.py
├── tushare.py              # get_tushare_client / get_adata_client / get_pytdx_client
└── schedule.py             # get_schedule_runner / get_schedule_repo
```

**为什么**：
- 改 auth 的 service 字段时，不需要动 `shared/`——shared/ 应该尽量"不动"
- 业务 service 工厂**就近维护**，跟 service 实现放一起
- 跨 context 复用（如 auth 的 jwt_service 被 market 用）通过 `Depends` 注入，**不**通过 `shared/.../di/`

**shared/ 只放基础设施级 DI**（所有 context 都会用的纯资源依赖）：

```
shared/infrastructure/di/
├── __init__.py
└── db_session.py           # get_db / get_raw_db / get_db_context / get_raw_db_context
```

#### 异常分层

| 异常来源 | 归属 |
|---|---|
| 业务规则违反（对象不存在 / 状态非法） | **`domain` 层定义的领域异常**，由各聚合根或领域服务抛出 |
| port 契约错误（调用方要据此决定重试 / 换源 / 降级，如限频、数据源不可用） | **`application/port/` 中与 port 一起定义**；infrastructure 负责把 SDK 原始异常翻译成这些类型 |
| 其他外部 IO / SDK 错误（调用方不需要区分处理） | `infrastructure/exception/` |
| 跨用例的应用级错误（极少见） | `application/` 局部 |

**注意**：业务异常属于领域知识，应由 domain 层定义；infrastructure 只翻译技术错误。如果应用层需要 `except` 某种技术错误，它就是 port 契约的一部分，不能定义在 infrastructure（否则 application 要 import infrastructure）。

#### 机制实现（限流 / 重试 / 缓存）放在 infrastructure

| 机制 | 归属 | 原因 |
|---|---|---|
| 限流（Redis 令牌桶） | `infrastructure/throttler.py` | 依赖具体存储（Redis）、具体数据源限流键 |
| 重试（捕获 RateLimited 退避） | `infrastructure/retry.py` | 依赖 port 契约的 RateLimited，但具体 sleep / 退避策略是机制 |
| 缓存（Redis 读/写） | `infrastructure/cache/` | 依赖具体缓存后端 |

原则：ApplicationService 决定**策略**（要不要限流、TTL 多长、失败怎么降级）；infrastructure 提供**机制**（具体怎么限、怎么退、怎么缓存）。port 不包含这些（port 是"要什么"契约，不是"怎么取"机制）。

---

### 2.5 shared（共享层）

- 放**完全无业务语义**的工具（如时间格式化、UUID 生成）
- **禁止**把任何带业务规则的工具放进来
- **禁止**把任何 context 的业务 DI 工厂放进来（见 §2.4「各 context 的 DI 自管理」）

#### shared/ 内部子结构

```
shared/infrastructure/
├── config/                 # 纯配置
│   ├── __init__.py
│   └── settings.py         # pydantic-settings；只放 .env 字段定义和 get_settings
│
├── di/                     # 基础设施级 DI（所有 context 都会用）
│   ├── __init__.py
│   └── db_session.py       # get_db / get_raw_db / get_db_context / get_raw_db_context
│
├── connection/             # 资源连接（实例 + 工厂，不带 FastAPI Depends）
│   ├── __init__.py
│   ├── db_factory.py       # engine + session_factory 实例（AsyncSessionLocal → db_session_factory）
│   └── redis_client.py     # aioredis 客户端构造（_build_client）
│
├── persistence/            # ORM（与 connection/ 解耦）
│   ├── orm_base.py
│   ├── mixins.py
│   └── ...
│
└── ...                     # 未来可加 http_client / smtp_client 等
```

**强约束**：
- ✅ `config/` 只放**纯配置**（pydantic-settings、.env、常量）——不能放 DI、不能放资源连接
- ✅ `connection/` 放**资源连接实例 + 工厂**（engine、redis client、http client ...）——不带 FastAPI Depends
- ✅ `di/` 放**FastAPI Depends 工厂**——只调 connection/ 里的实例
- ❌ 不要在 `config/` 下放 `di.py`（config 是配置，不是 DI 容器）
- ❌ 不要把 `connection/` 和 `di/` 混在一起——一个管"怎么造资源"，一个管"怎么注入"

**命名规范**：

| 旧名（不推荐） | 新名（推荐） | 位置 |
|---|---|---|
| `AsyncSessionLocal` | `db_session_factory` | `connection/db_factory.py` |
| `RawSessionLocal` | `raw_session_factory` | `connection/db_factory.py` |
| `async_engine` | `db_async_engine` | `connection/db_factory.py` |
| `raw_engine` | `raw_async_engine` | `connection/db_factory.py` |
| `redis_client.py`（混合体） | `connection/redis_client.py` | 只放 `_build_client()` |
| `get_redis()`（在 connection 里） | `di/redis_session.py` 里的 `get_redis()` | 移出来，connection 不带 Depends |

理由：`Local` 这个后缀是 SQLAlchemy 1.x / Flask `scoped_session(threading.local())` 时代的遗留；2.0 异步生态里 `async_sessionmaker` 实例官方就叫 "session factory"。

---

## 3. domain 层目录组织

### 3.1 整体结构：按"聚合根"分目录

```
domain/
├── entitys/                      ← 一个聚合根一个子目录（用 entitys 而非 entities）
│   ├── kline/
│   │   ├── entity.py
│   │   ├── repository.py         ← 仓储接口
│   │   └── vo.py                 ← 本聚合根专用 VO
│   ├── stock_info/
│   │   ├── entity.py
│   │   ├── repository.py
│   │   └── vo.py
│   └── ...（其他聚合根）
└── service/                      ← 跨聚合根的领域服务（纯算法）
    └── ...
```

### 3.2 设计原则

| 规则 | 说明 |
|---|---|
| **聚合根不单独建 `exceptions/` 子目录** | 例外只由 entity 自身抛出，不需要专门目录 |
| **聚合根内部不建 `service/` 子目录** | 聚合根内部的复杂算法直接放在 `entity.py` 中，作为实体的方法（"我自己的事我自己做"） |
| **VO 放在使用它的聚合根目录下** | `StockCode` / `TradeDate` 放在 `kline/vo.py`、采集方案的定时配置 `Schedule` 放在 `collect_plan/vo.py`；多个聚合根共用的 VO 放在最接近主语义的聚合根下。外部数据载体 BO 不是 domain VO，放在 port 契约中（见 §2.2） |
| **聚合根自己的规则写在聚合根里** | 如"采集间隔不小于 30 秒"属于采集方案，写在 `Schedule` VO 的校验里，而不是 `domain/service/` |
| **领域服务放 `domain/service/`** | 只有**跨多聚合根**的通用算法才放在这里；属于某一聚合根的逻辑就属于那个聚合根 |

### 3.3 决策流程图

```
一段领域逻辑 X 要写在哪里？
│
├─ X 只涉及一个聚合根自己的状态/规则？
│   └─ → 写在 entity 里（成为该 entity 的方法）
│
├─ X 涉及本聚合根内部多个实体的协作，但仍属"本聚合根的事"？
│   └─ → 仍放在 entity 内（如果是协作，加到主聚合根 entity 上）
│
├─ X 真的跨多个聚合根，但是纯算法无副作用？
│   └─ → domain/service/ 下新建领域服务
│
└─ X 跨多聚合 + 有副作用（持久化 / 调外部）？
    └─ → application/service 的 AppService
```

---

## 4. 依赖关系规则

| 上层 | 可以依赖 | 不可以依赖 |
|---|---|---|
| `interface` | application、domain（仅使用其 VO 作为契约载体） | infrastructure |
| `application` | domain（含 repository 接口）、自身的 port 接口；port 的实现通过注入获得 | interface（含 `interface/dto`）、infrastructure 的具体实现、任何 SDK |
| `domain` | 仅自身（entity、vo、repository 接口、service） | **任何**外层 |
| `infrastructure` | domain（实现其接口）、application（实现其 port） | interface |

**铁律**：

1. `domain` **零外部依赖**（不 import 任何 framework / SDK）
2. `domain` 的 `repository` 接口由 `infrastructure/persistence/` **实现并注入**
3. `application` 通过 `port` 接口使用外部能力，**不知道**具体 SDK
4. `interface/route/` 里的 route 文件通过 `Depends(...)` 引用本 context 的 `infrastructure/di/` 工厂
5. 跨 context 复用时，本 context 的 `infrastructure/di/` 通过 `Depends(...)` 引用其他 context 的 `infrastructure/di/`

---

## 5. 关键反模式（不要做的事）

| 反模式 | 后果 |
|---|---|
| Anemic Domain Model（只有 setter/getter 的实体） | 领域逻辑泄到 service / controller |
| 在 ApplicationService 里算指标 | 业务规则散落，难以单测 |
| 让 entity 直接调 `db.query()` | 测试必须起数据库 |
| 让 controller 跨过 app 层直接调 repository 或 port | 事务、权限、缓存全部丢失 |
| port 参数里出现 SDK 特有字段（`ts_code`、"最近 N 根"） | 换数据源要改接口，上层跟着改 |
| 业务异常放在 `infrastructure/exception/` | infra 不知道业务规则 |
| VO 散落到各层（interface 一份、app 一份、domain 一份） | 同一概念三种类型，转换繁琐 |
| 在 `interface/` 下直接放 `route_xxx.py`（不收进 `route/`） | 路由散乱，跨文件搜索痛苦 |
| 把全部路由塞进一个 `interface/route.py` | 单文件膨胀到 500+ 行 |
| 把所有 DI 工厂塞进 `shared/.../config/di.py` 一个文件 | `config/` 不再是纯配置；改业务要动 `shared/` |
| 把所有 DI 工厂塞进 `infrastructure/di.py` 一个文件 | 文件膨胀后无法维护 |
| 业务 DI 工厂放 `shared/.../di/` | 改业务 service 要动 `shared/`——破坏 shared 不动原则 |
| 在 `config/` 下放 `di.py` 或资源连接 | config 应该只有 .env 字段定义 |

---

## 6. 一个用例：按本规范应该写在哪

用例：**"为某只股票计算 20 日 RSI 指标"**

| 步骤 | 层 | 位置 |
|---|---|---|
| 1. HTTP 接收 `KlineCollectRequest` | interface | `interface/route/kline.py`、`interface/dto/request/kline.py` |
| 2. interface 将参数翻译为 AppService 调用 | interface | 同上文件 |
| 3. AppService 开事务、取 Kline 列表、调用领域服务、返回结果 | application | `application/service/kline_app_service.py` |
| 4. 领域服务计算 RSI（纯算法，跨 K线多时间点） | domain | `domain/service/rsi_calculator.py` |
| 5. repo 接口取 Kline 列表 | domain | `domain/entitys/kline/repository.py` |
| 6. repo 实现查 DB | infrastructure | `infrastructure/persistence/repositories/xxx_repository.py` |
| 7. AppService 把 `IndicatorValue` 返回给 interface | application | 同 3 |
| 8. interface 把 `IndicatorValue` 包成 `KlineIndicatorVO` JSON 响应 | interface | `interface/dto/response/kline.py` |

> 任何"指标如何计算"的细节都集中在 step 4，可以脱离数据库 / Spring / FastAPI 单测。

---

## 7. 与具体代码实现的对应

> 本节只用于让阅读者快速对照。**实现可随技术栈演进；分层原则不变。**

代码目录通常形态：

```
src/
├── interface/                      ← 接口层
│   ├── route/                      ← 路由文件（按业务子模块分文件，不是按 HTTP method）
│   │   ├── auth_login.py
│   │   ├── auth_password.py
│   │   ├── user.py
│   │   └── ...
│   ├── deps.py                     ← route 层横切依赖（get_current_user / require_role）
│   └── dto/
│       ├── request/                ← 入参 DTO
│       └── response/               ← 出参 DTO（含 Page<T> 等通用响应）
│
├── application/                    ← 应用层
│   ├── service/                    ← AppService
│   │   ├── collect/                ← 写库 service（collect() 为主）
│   │   ├── query/                  ← 实时查询 service（get() 为主）
│   │   ├── base.py                 ← CollectService Protocol / CollectResult
│   │   └── registry.py             ← 内存 ServiceRegistry
│   ├── bo/                         ← 外部数据载体（按 facet 分子目录）
│   │   ├── tech.py                 ← tech 类 BO
│   │   ├── capital.py              ← capital 类 BO
│   │   └── fundamental.py          ← fundamental 类 BO
│   └── port/                       ← 对外抽象契约
│       ├── scheduler_port.py       ← SchedulerPort 接口
│       ├── params.py               ← 参数类型
│       └── errors.py               ← port 契约级错误（RateLimited / SourceUnavailable）
│
├── domain/                         ← 领域层（零外部依赖）
│   ├── entitys/                    ← 一个聚合根一个子目录
│   │   ├── <aggregate>/
│   │   │   ├── entity.py
│   │   │   ├── repository.py       ← 仓储接口（Protocol）
│   │   │   └── vo.py
│   │   └── ...
│   ├── exceptions.py               ← 业务级异常（InvalidParams / NotSupported；参考 market/domain）
│   └── service/                    ← 跨聚合根的领域服务
│
├── infrastructure/                 ← 基础设施层（按 context 自管理 DI）
│   ├── adapter/                    ← 外部 SDK / 调度适配
│   ├── persistence/
│   │   ├── models/                 ← ORM 模型（DB 表映射）
│   │   └── repositories/           ← domain/repository 的 SQL/ORM 实现
│   ├── di/                         ← DI 工厂（**目录**，按资源类型分文件）
│   │   ├── __init__.py             ← re-export
│   │   ├── <service_a>.py          ← get_service_a（业务 service 工厂）
│   │   └── <service_b>.py          ← get_service_b
│   ├── throttler.py                ← 限流（Redis 令牌桶），@throttle 装饰器 + check()
│   ├── retry.py                    ← 重试，@retry_on_rate_limited + fetch_with_retry()
│   ├── cache/                      ← Redis 缓存机制
│   ├── exception/                  ← 基础设施异常
│   └── lifespan.py                 ← lifespan 启动初始化（init_service_registry 等）
│
└── shared/                         ← 跨 context 的纯通用能力（**无业务**）
    └── infrastructure/
        ├── config/                 ← 纯配置（pydantic-settings）
        │   └── settings.py
        ├── di/                     ← 基础设施级 DI（所有 context 都会用）
        │   └── db_session.py       ← get_db / get_raw_db / *_context
        ├── connection/             ← 资源连接实例 + 工厂
        │   ├── db_factory.py       ← engine + db_session_factory（替换 AsyncSessionLocal）
        │   └── redis_client.py     ← aioredis 客户端构造
        └── persistence/            ← ORM 基类（与 connection/ 解耦）
            ├── orm_base.py
            └── mixins.py
```

`contexts/` 下每个 context 都按上述模板组织，DI 自管理：

```
contexts/auth/
├── application/
├── domain/
├── infrastructure/
│   ├── adapter/
│   ├── persistence/
│   ├── di/                         ← auth 的业务 DI 工厂
│   │   ├── __init__.py
│   │   └── auth_service.py
│   ├── security/
│   └── ...
└── interface/
    ├── route/                      ← 路由（按业务子模块分文件）
    │   ├── auth_login.py
    │   └── auth_password.py
    ├── deps.py                     ← get_current_user / require_role
    └── dto/
```

`collect/` context 因为有 lifespan 初始化（`init_service_registry`），需要额外：

```
contexts/collect/
└── infrastructure/
    ├── di/                         ← 业务 DI 工厂
    │   ├── tushare.py              ← get_tushare_client / get_adata_client / get_pytdx_client
    │   └── schedule.py             ← get_schedule_runner / get_schedule_repo / get_run_log_repo
    └── lifespan.py                 ← init_service_registry() / init_schedule_runner()
```

`lifespan.py` 调 `infrastructure/di/` 里的工厂，组装 registry。

---

## 8. 命名规范速查

| 类别 | 旧名（不推荐） | 新名（推荐） |
|---|---|---|
| DB session 工厂 | `AsyncSessionLocal` | `db_session_factory` |
| DB session 工厂 | `RawSessionLocal` | `raw_session_factory` |
| DB engine | `async_engine` | `db_async_engine` |
| DB engine | `raw_engine` | `raw_async_engine` |
| DB 资源目录 | `persistence/connection.py` | `connection/db_factory.py` |
| Redis 客户端 | `redis_client.py`（混合体） | `connection/redis_client.py`（只造 client） |
| Redis 注入 | `redis_client.get_redis()` | `di/redis_session.get_redis()` |
| 路由文件 | `interface/route_xxx.py` | `interface/route/xxx.py` |
| 单文件大路由 | `interface/route.py` | `interface/route/{auth_login,auth_password,...}.py` |
| 业务 DI 单文件 | `infrastructure/di.py` | `infrastructure/di/<resource>.py` |
| 业务 DI 在 shared | `shared/.../di/<resource>.py` | `contexts/<ctx>/infrastructure/di/<resource>.py` |
| config 里放 DI | `shared/.../config/di.py` | 拆到各 context 的 `infrastructure/di/` |

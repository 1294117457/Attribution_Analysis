# 总统架构规范

> 5 分钟看懂全局。新人必读。

## 1. 分层模型

```
┌─────────────────┐
│ interface       │  HTTP / RPC / 调度入口 + DTO
└────────┬────────┘
         ↓ 调
┌─────────────────┐
│ application     │  用例编排（事务、缓存、调外部）
└────────┬────────┘
         ↓ 调
┌─────────────────┐
│ domain          │  核心业务（entity / vo / 领域接口）
└────────┬────────┘
         ↑ 实现
┌─────────────────┐
│ infrastructure  │  外部实现（适配器、JPA、配置、异常）
└─────────────────┘
```

## 2. 依赖铁律

| 规则 | 反例 |
|------|------|
| `domain` 不依赖任何外部 | ❌ `domain` import `service` / `controller` / `Spring` |
| `application` 不依赖 `infrastructure` 实现 | ❌ AppService 直接 `new KlineCollectionExecutor()` |
| `infrastructure` 不被 `domain` 引用 | ❌ `entity` import `infrastructure.adapter` |
| `interface` 不写业务 | ❌ Controller 里写 if-else 校验 |
| **DTO 只属于 `interface` 层** | ❌ `service` / `adapter` / `domain.repository` 引用 DTO |

**反向依赖怎么实现？**
- application 调外部 → 通过 `port` 接口
- infrastructure 实现 `port` 接口 → 注入到 application

## 3. 模块包结构（精简版）

```
com.attribution/
├── domain/               ← 核心
│   ├── entity/           实体（有 ID、有生命周期）
│   ├── vo/               值对象（无 ID、按值相等）
│   ├── repository/       仓储接口
│   └── service/          领域服务（跨多实体逻辑）
│
├── application/          ← 用例
│   └── service/          AppService（一个方法 = 一个用例）
│
├── infrastructure/       ← 外部
│   ├── adapter/          port 实现 + 外部 SDK
│   ├── persistence/      repository 实现
│   ├── config/           Spring Bean / 外部客户端
│   └── exception/        业务异常类
│
└── interface/            ← 对外
    ├── controller/       HTTP 入口
    └── dto/              跨层数据传输（Request / Response / VO）
        └── response/     ApiResponse / PageResponse / ErrorResponse（跨模块通用响应）
```

### 3.1 dto 子包约定

> dto 子包**按业务模块划分**，模块名随业务演进自然增长，不在规范中预先枚举。

| 类别 | 位置 | 说明 |
|------|------|------|
| **跨模块通用响应** | `interface/dto/response/` | `ApiResponse` / `PageResponse` / `ErrorResponse`，所有 controller 共用 |
| **单模块 DTO** | `interface/dto/{module}/` | 按业务模块划分，如 `pool/`、`kline/`、`stock/` 等。模块名与 `controller/` 下的 Controller 名对齐（如 `PoolController` → `pool/`） |

**模块命名规则**：
- 用单数名词（`pool` / `kline`），不用复数
- 全小写，不带连字符
- 模块内 DTO 命名：`{Module}VO` / `{Module}Request` / `{Module}DetailVO` 等

> **未来扩展**（需要时再加，不预先建）：
> - `domain/event/` —— 领域事件
> - `application/port/` —— 端口接口
> - `application/assembler/` —— 转换器
> - `application/bootstrap/` —— 启动钩子

## 4. DTO 分类与边界

> DTO 是**对外接口契约**（Request / Response），属于 `interface` 层，不应被下层引用。

### 4.1 三类 DTO 的区分

| 类型 | 位置 | 用途 | 例 |
|------|------|------|----|
| **Request** | `interface/dto/{module}/` | 入参（带 `@Valid`） | `PoolCreateRequest`、`KlineQueryRequest` |
| **VO** | `interface/dto/{module}/` | 出参（响应体） | `PoolVO`、`KlineVO` |
| **Response 封装** | `interface/dto/response/` | 跨模块统一响应 | `ApiResponse` / `PageResponse` / `ErrorResponse` |

### 4.2 与 domain/vo 的边界

| 类型 | 位置 | 特征 |
|------|------|------|
| **DomainVO** | `domain/vo/` | 无 ID、按值相等、含业务校验、构造时校验（如 `TradeDate`、`OperationStatus`、`PoolType`） |
| **DTO VO** | `interface/dto/{module}/*VO` | 有 ID、带关联字段、为 HTTP 响应定制（如 `PoolVO`、`KlineVO`） |

> 💡 **怎么判定**：
> - 看代码里出现 `this.xxx()` 跨多 entity 计算 → **DomainVO**（放 `domain/vo/`）
> - 单纯把 entity 字段搬过来给前端看 → **DTO VO**（放 `interface/dto/{module}/`）

### 4.3 DTO 不跨层（铁律）

> ❌ `domain.repository` 接口返回 DTO  
> ❌ `infrastructure.query` 返回 DTO  
> ❌ `adapter.collector` 返回 DTO  
> ❌ `service`（包括 application service）返回 DTO

> ✅ 只有 `interface.controller` 才返回 DTO  
> ✅ 下层返回 entity / domain VO，controller 在最后一公里装配

**理由**：
- DTO 是 HTTP 序列化对象，可能含 JSON 注解、Lombok `@Builder` 等。
- 下层依赖 DTO 会导致下层被"对外格式"绑定，违反依赖倒置。

> ⚠️ **当前代码违规清单**（详见 `04-interface-spec.md §8`）：
>
> | # | 位置 | 现状 |
> |---|------|------|
> | 1 | `service/ConceptService` | 直接返回 `ConceptBriefVO` / `ConceptDetailVO` 等 |
> | 2 | `service/StockPanelService` | 入参接 `StockPanelQuery`，出参返回 `StockPanelResponse` |
> | 3 | `adapter/collector/.../TushareKlineCollector` | 直接返回 `KlineCollectVO` |
> | 4 | `domain/repository/StockPanelComposeRepository` | 接口方法返回 `StockPanelRowVO` |
> | 5 | `infrastructure/query/StockPanelComposeRepositoryImpl` | 实现方法返回 `StockPanelRowVO` |
>
> 这些是**存量违规**，迁移到 `interface/dto/` 时**必须一并修复**（详见后续 PR 计划）。

## 5. 核心概念速查

| 概念 | 一句话定义 | 在哪 |
|------|----------|------|
| Entity | 有 ID、有状态、有生命周期 | `domain/entity/` |
| **DomainVO** | **无 ID、按值相等、自带校验（域内纯值对象）** | `domain/vo/` |
| **DTO VO** | **HTTP 响应专用，可带 ID / 关联字段 / JSON 注解** | `interface/dto/{module}/` |
| **Request DTO** | **HTTP 入参专用，带 `@Valid`** | `interface/dto/{module}/` |
| Repository | 持久化接口 | `domain/repository/` |
| DomainService | 跨多实体的纯领域逻辑 | `domain/service/` |
| AppService | 一个方法 = 一个用例 | `application/service/` |
| Adapter | 外部 SDK 适配器 | `infrastructure/adapter/` |
| DTO | 跨层数据传输 | `interface/dto/` |

## 6. 判定口诀（搬代码时用）

看到一段方法体，按顺序判定放哪：

```
① 只出现 this.xxx() / this.xxx()        → domain/entity
② 出现别的 entity 类型 / DomainVO 计算   → domain/service
③ 出现 repository / HttpClient / Clock   → application/service
④ 出现 Spring Bean / 第三方 SDK           → infrastructure/adapter
⑤ 出现 @RequestMapping / @PathVariable   → interface/controller
⑥ 出现 @RequestBody / ResponseBody VO    → interface/dto
```

## 7. 与代码现状的差异

> ⚠️ 本节记录**文档与代码的实际差异**，待后续 PR 收口。

| 项 | 文档定义 | 代码现状 | 差异 |
|----|---------|---------|------|
| AppService 包路径 | `application/service/` | `service/`（顶级包） | ⚠️ 路径偏差 |
| dto 包路径 | `interface/dto/` | `dto/`（顶级包） | ⚠️ 路径偏差 |
| dto 跨层引用 | 不允许 | 5 处违规（详见 §4.3） | ⚠️ 违规 |

> 这 3 项是**当前已知偏差**，迁移期间保持兼容，不影响规范文档的有效性。

## 8. 详细规范

- [01-domain-spec.md](./01-domain-spec.md)
- [02-application-spec.md](./02-application-spec.md)
- [03-infrastructure-spec.md](./03-infrastructure-spec.md)
- [04-interface-spec.md](./04-interface-spec.md)

## 9. 与现有 DDD.md 的关系

| 文档 | 目的 |
|------|------|
| `../DDD.md` | 概念入门（DDD 是什么） |
| `design/` | 项目落地规范（在我们项目里怎么写） |

## 10. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-25 | -      | 初稿 |
| v0.2  | 2026-09-25 | -      | dto 纳入 `interface/dto/` 顶层包；新增 DTO 分类、DTO vs DomainVO 边界、DTO 不跨层铁律 |

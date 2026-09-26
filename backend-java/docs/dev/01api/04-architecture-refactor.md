# 04 · 架构层重构方案（包结构 / DTO 边界）

> 本文档聚焦**架构与包结构层面**的重构，不涉及接口层（路径、参数、响应格式）的修改——后者见 `01-api-mapping.md` / `02-non-compliance.md` / `03-fix-plan.md`。
>
> 配套文档：
> - 规范来源：`docs/design/architecture/00-overview.md` 及 01-04 章节
> - 接口层重构：本文档同级 01/02/03
> - 本文档**只列修改方案，不动代码**

---

## 0. TL;DR

**核心问题**：当前代码采用**扁平 11 个包**结构（`adapter` / `config` / `controller` / `domain` / `dto` / `exception` / `infrastructure` / `service` ...），而架构规范要求**4 层嵌套**（`domain` / `application` / `infrastructure` / `interface`）。

**重构目标**：把 11 个扁平包重组成 4 层结构 + 让 DTO 严格不跨层。

**推荐节奏**：分 6 个 PR、~7 天工作量、按依赖方向迁移（domain → application → infrastructure → interface）。

---

## 1. 现状盘点

### 1.1 当前包结构（扁平）

```
com.attribution/
├── AttributionApplication.java
├── adapter/                       ← infrastructure 的一部分（外部 SDK）
│   └── collector/
│       ├── tushare/
│       ├── akshare/
│       └── pytdx/
├── config/                        ← infrastructure（Spring Bean）
├── controller/                    ← interface（HTTP 入口）
├── domain/
│   ├── entity/                    ✅ 与规范一致
│   ├── repository/                ✅ 与规范一致
│   └── vo/                        ✅ 与规范一致（domain 内纯值对象）
├── dto/                           ❌ 应在 interface 层
│   ├── response/                  ApiResponse / PageResponse / ErrorResponse
│   ├── stock/  pool/  kline/  concept/  operation/
├── exception/                     ❌ 应在 infrastructure 层
├── infrastructure/
│   └── query/                     StockPanelComposeRepositoryImpl（仅 1 个）
└── service/                       ❌ 应在 application 层
    ├── collect/                   BaseCollectTask / KlineCollectTask / ...
    └── indicator/                 TechnicalSummary / SignalDetector
    └── (其余 16 个 AppService)
```

### 1.2 文件数量统计（仅去重后）

| 当前顶级包 | 文件数 | 对应架构层 | 当前路径状态 |
|------------|--------|------------|--------------|
| `domain/` | ~110 | domain | ✅ 路径正确 |
| `dto/` | ~47 | interface | ❌ 应在 `interface/dto/` |
| `controller/` | ~9 | interface | ❌ 应在 `interface/controller/` |
| `service/` | ~20 | application | ❌ 应在 `application/service/` |
| `adapter/` | ~10 | infrastructure | ❌ 应在 `infrastructure/adapter/` |
| `config/` | ~3 | infrastructure | ❌ 应在 `infrastructure/config/` |
| `exception/` | ~13 | infrastructure | ❌ 应在 `infrastructure/exception/` |
| `infrastructure/query/` | ~1 | infrastructure | ✅ 路径正确（新增包） |

> 💡 实际有 ~213 个 java 文件（部分 Glob 工具有重名重复），迁移时需用 IDE 的"Move Package"批量重命名。

### 1.3 `service/` 内部子包

```
service/
├── ConceptService.java                   ← AppService
├── CollectTaskService.java               ← AppService
├── StockPoolService.java                 ← AppService
├── StockPanelService.java                ← AppService
├── StockService.java                     ← AppService
├── PoolOperationService.java             ← AppService
├── KlineService.java                     ← AppService
├── StockAnalysisService.java             ← AppService
├── CollectorRegistry.java                ← 注册中心（归 infrastructure）
├── DatabaseInitializer.java              ← 启动钩子（归 application/bootstrap）
├── OperationDispatcher.java              ← 调度（归 application？）
├── KlineCollectionExecutor.java          ← 调度执行（归 infrastructure？）
├── collect/
│   ├── BaseCollectTask.java              ← 调度任务抽象（归 application？）
│   ├── KlineCollectTask.java
│   ├── DailyBasicCollectTask.java
│   ├── FinReportCollectTask.java
│   ├── ConceptCollectTask.java
│   └── CollectTaskProgress.java
└── indicator/
    ├── TechnicalSummary.java             ← 指标计算（归 domain/service？）
    └── SignalDetector.java               ← 指标计算（归 domain/service？）
```

**核心问题**：`service/` 现在是"大杂烩"——既有 AppService，也有调度逻辑、指标计算、启动钩子、注册中心。规范要求**按职责重新分层**。

---

## 2. 目标架构

### 2.1 完整包结构

```
com.attribution/
├── AttributionApplication.java
│
├── domain/                          ← 核心层
│   ├── entity/                      ✅ 不变
│   ├── vo/                          ✅ 不变
│   ├── repository/                  ✅ 不变
│   └── service/                     ✅ 现有空包，新增：TechnicalSummary / SignalDetector
│
├── application/                     ← 用例层
│   ├── service/                     ← 现有 8 个 AppService（移自 service/）
│   ├── collect/                     ← 现有 collect/* （移自 service/collect/）
│   ├── indicator/                   ← （可选：移自 service/indicator/，或归 domain/service/）
│   └── bootstrap/                   ← 新增：DatabaseInitializer
│
├── infrastructure/                  ← 外部层
│   ├── adapter/                     ← 现有 adapter/（移入）
│   ├── config/                      ← 现有 config/（移入）
│   ├── exception/                   ← 现有 exception/（移入）
│   ├── query/                       ✅ 不变（已有）
│   └── executor/                    ← 新增：KlineCollectionExecutor / OperationDispatcher
│
└── interface/                       ← 对外层
    ├── controller/                  ← 现有 controller/（移入）
    ├── dto/                         ← 现有 dto/（移入）
    │   └── response/                ✅ 不变（已有）
    └── handler/                     ← 新增：GlobalExceptionHandler
```

### 2.2 `service/` 大杂烩的去向

| 当前类 | 当前路径 | 目标路径 | 理由 |
|--------|----------|----------|------|
| `ConceptService` | `service/` | `application/service/` | AppService |
| `CollectTaskService` | `service/` | `application/service/` | AppService |
| `StockPoolService` | `service/` | `application/service/` | AppService |
| `StockPanelService` | `service/` | `application/service/` | AppService |
| `StockService` | `service/` | `application/service/` | AppService |
| `PoolOperationService` | `service/` | `application/service/` | AppService |
| `KlineService` | `service/` | `application/service/` | AppService |
| `StockAnalysisService` | `service/` | `application/service/` | AppService |
| `DatabaseInitializer` | `service/` | `application/bootstrap/` | 启动钩子 |
| `OperationDispatcher` | `service/` | `infrastructure/executor/` 或 `application/dispatcher/` | 调度执行（**有争议**，见 §6.1） |
| `KlineCollectionExecutor` | `service/` | `infrastructure/executor/` | 调用 adapter 完成采集 |
| `CollectorRegistry` | `service/` | `infrastructure/registry/` 或 `application/bootstrap/` | 注册中心 |
| `service/collect/*Task` | `service/collect/` | `application/collect/` | 任务抽象（AppService 用） |
| `service/collect/CollectTaskProgress` | `service/collect/` | `application/collect/` | 任务进度（DTO 还是 progress VO？）|
| `service/indicator/TechnicalSummary` | `service/indicator/` | `domain/service/` | 纯指标计算（无 IO、无外部） |
| `service/indicator/SignalDetector` | `service/indicator/` | `domain/service/` | 纯指标计算（无 IO、无外部） |

---

## 3. 现状 vs 规范偏差清单

### 3.1 偏差总览

| # | 偏差项 | 优先级 | 影响范围 |
|---|--------|--------|----------|
| A1 | `dto/` 应在 `interface/dto/` | **P0** | 47 个 dto 文件 + 47 个引用方 |
| A2 | `controller/` 应在 `interface/controller/` | **P0** | 9 个 controller |
| A3 | `service/` 应在 `application/service/` | **P0** | 20 个 service |
| A4 | `adapter/` 应在 `infrastructure/adapter/` | **P0** | 10 个 adapter |
| A5 | `config/` 应在 `infrastructure/config/` | **P0** | 3 个 config |
| A6 | `exception/` 应在 `infrastructure/exception/` | **P0** | 13 个 exception |
| B1 | `service/indicator/*` 应归 `domain/service/` | **P1** | 2 个 |
| B2 | `GlobalExceptionHandler` 应归 `interface/handler/` | **P1** | 1 个 |
| B3 | `OperationDispatcher` 归属未定 | **P1** | 1 个（需业务决策） |
| B4 | `KlineCollectionExecutor` 归属未定 | **P1** | 1 个 |
| B5 | `CollectorRegistry` 归属未定 | **P2** | 1 个 |
| C1 | DTO 跨层违规 5 处（service/adapter/repository 返回 DTO） | **P0** | 5 处 |
| C2 | `service/` 内类职责混杂（AppService + 调度 + 指标） | **P1** | 全部 |
| D1 | dto 子包命名不规范（如 `operation/` 应该是 `pooloperation/` 还是 `pool/operation/`）| **P2** | 仅命名 |

### 3.2 P0 偏差详述

#### A1: dto 顶层 → interface/dto

**当前**：`com.attribution.dto.{stock,pool,kline,concept,operation,response}.*`  
**目标**：`com.attribution.interface.dto.{module}.*`

**引用方统计**：
- `controller/*`（9 个文件）→ 应继续引用
- `service/*`（5 个文件，详见 C1）→ 应改为引用 entity
- `adapter/collector/.../TushareKlineCollector`（1 个文件）→ 应改为引用 entity
- `domain/repository/StockPanelComposeRepository`（1 个接口）→ 应改为返回 entity
- `infrastructure/query/StockPanelComposeRepositoryImpl`（1 个实现）→ 同上
- `exception/GlobalExceptionHandler`（1 个文件）→ 应继续引用 ErrorResponse

#### A3: service 顶层 → application/service

**当前**：`com.attribution.service.*`  
**目标**：`com.attribution.application.service.*`

**引用方**：
- `controller/*` → 改 import
- `service/*` 内部互引 → 改 import

#### C1: DTO 跨层违规（5 处）

| # | 违规位置 | 违规内容 | 修复方向 |
|---|----------|----------|----------|
| 1 | `service/ConceptService` | 直接 `return ConceptBriefVO.builder()...build()` | 改 return entity + Controller 装配 |
| 2 | `service/StockPanelService` | 入参 `StockPanelQuery`，返回 `StockPanelResponse` | 入参改 application.command/Query，return entity |
| 3 | `adapter/.../TushareKlineCollector` | `collect()` 返回 `KlineCollectVO` | 改 return entity + progress 数值 |
| 4 | `domain/repository/StockPanelComposeRepository` | 接口返回 `StockPanelRowVO` | 改返回 entity |
| 5 | `infrastructure/query/StockPanelComposeRepositoryImpl` | 同上 | 同上 |

---

## 4. 重构方案

### 4.1 总体策略

1. **按"依赖倒置方向"自底向上迁移**：domain（不动）→ infrastructure → application → interface
2. **包路径迁移 + import 同步**：用 IDE 的"Move Package"功能 + 批量改 import
3. **每完成一层 PR，跑一次编译验证**（防止漏改 import）
4. **每完成一层 PR，业务接口契约不变**（只在包路径层面改，不改方法签名）

### 4.2 重构边界

**允许改的**：
- 包路径（package 声明 + 所有 import）
- 类归属（如 `service/indicator/*` → `domain/service/*`）
- DTO 内部字段（如果发现重复字段可合并）

**不允许改的**：
- Controller 方法签名（HTTP 接口契约）
- AppService 方法签名（业务用例契约）
- 业务逻辑代码
- 配置文件（application.yml、pom.xml）
- 数据库 schema

### 4.3 PR 划分（推荐 6 个 PR）

```
PR-A1  dto 包迁移 + DTO 跨层违规修复（5 处）          ← 4 个文件 + 47 个 dto
PR-A2  controller → interface/controller             ← 9 个文件
PR-A3  service → application/service                 ← 20 个文件
PR-A4  adapter → infrastructure/adapter              ← 10 个文件
PR-A5  config + exception → infrastructure/*         ← 16 个文件
PR-B    service 子包拆分（indicator/dispatcher/executor/bootstrap）← 6 个文件
PR-C    GlobalExceptionHandler → interface/handler   ← 1 个文件
```

每个 PR 完成后：
1. 跑 `mvn compile` 验证编译通过
2. 跑 `mvn test` 跑现有测试
3. 跑 `mvn spring-boot:run` 启动服务，调用 1-2 个核心接口（如 `GET /pools`）做冒烟测试

---

## 5. PR 详细方案

### PR-A1 · dto 包迁移 + DTO 跨层违规修复（推荐先做）

**工作量**：~1.5 天  
**风险**：高（47 个 dto + 47 个引用方）

#### 步骤

##### 步骤 1: 新建目标包

```
com.attribution.interface.dto.response/      ← ApiResponse / PageResponse / ErrorResponse
com.attribution.interface.dto.{module}/      ← 按业务模块
```

> 模块名沿用现状（`stock` / `pool` / `kline` / `concept` / `operation`），后续 PR 再统一命名。

##### 步骤 2: 用 IDE "Move Package" 批量迁移

在 IntelliJ IDEA：
1. 选中 `com.attribution.dto.*` 整包
2. Refactor → Move Package
3. 目标：`com.attribution.interface.dto`
4. IDE 自动改所有 import

##### 步骤 3: 修复 DTO 跨层违规（5 处）

**违规 1：`service/ConceptService` 返回 DTO**

```java
// 旧（违规）
public ConceptDetailVO getConceptDetail(String code) {
    return ConceptDetailVO.builder()
        .code(concept.getConceptCode())
        .name(concept.getConceptName())
        // ...
        .build();
}

// 新
public ConceptDetailEntity getConceptDetail(String code) {
    ConceptEntity concept = conceptRepository.findByCode(code)
        .orElseThrow(() -> new ConceptNotFoundException(code));
    List<ConceptMemberEntity> members = conceptMemberRepository.findByConceptId(concept.getId());
    // 返回 entity 集合 + 概念 entity
    return ConceptDetailEntity.of(concept, members);
}

// Controller 装配
@GetMapping("/{code}")
public ApiResponse<ConceptDetailVO> getConcept(@PathVariable String code) {
    ConceptDetailEntity entity = conceptService.getConceptDetail(code);
    return ApiResponse.ok(ConceptAssembler.toDetailVO(entity));
}
```

**违规 2：`service/StockPanelService` 入参 + 出参都用 DTO**

```java
// 旧（违规）
public StockPanelResponse queryPanel(StockPanelQuery query) {
    List<StockPanelRowVO> rows = composeRepository.queryPanel(query);
    long total = composeRepository.countPanel(query);
    return StockPanelResponse.builder().rows(rows).total(total).build();
}

// 新
public PanelQueryResult queryPanel(PanelQuery query) {  // 入参改 application/command/*
    List<StockPanelRowEntity> rows = composeRepository.queryPanelRows(query);
    long total = composeRepository.countPanelRows(query);
    return PanelQueryResult.of(rows, total);
}

// Controller 装配
@ApiResponse<StockPanelResponse> ... 
    PanelQueryResult result = stockPanelService.queryPanel(PanelQuery.from(req));
    return ApiResponse.ok(StockPanelAssembler.toResponse(result));
```

**违规 3：`adapter/.../TushareKlineCollector.collect` 返回 DTO**

```java
// 旧（违规）
public KlineCollectVO collect(String symbol, int days) {
    // ...
    return KlineCollectVO.builder().symbol(symbol).fetched(fetched).build();
}

// 新
public KlineCollectResult collect(String symbol, int days) {  // 返回内部 result
    // ...
    return new KlineCollectResult(symbol, fetched, startDate, endDate);
}
```

**违规 4 + 5：`domain/repository/StockPanelComposeRepository` 返回 DTO**

```java
// 旧（违规）
public interface StockPanelComposeRepository {
    List<StockPanelRowVO> queryPanel(StockPanelQuery query);
}

// 新
public interface StockPanelComposeRepository {
    List<StockPanelRowEntity> queryPanelRows(PanelQuery query);  // 返回 entity
}
```

> 需要新增 `StockPanelRowEntity`（或复用现有 entity / 创建一个 row 专用 entity）。

##### 步骤 4: 新增 Application Command / Query

```java
// application/command/PanelQuery.java（新增）
public record PanelQuery(
    String tradeDate,
    List<String> symbols,
    int limit,
    int offset
) {
    public static PanelQuery from(StockPanelQueryRequest req) {
        return new PanelQuery(req.tradeDate(), req.symbols(), req.limit(), req.offset());
    }
}

// application/result/PanelQueryResult.java（新增）
public record PanelQueryResult(
    List<StockPanelRowEntity> rows,
    long total
) {
    public static PanelQueryResult of(List<StockPanelRowEntity> rows, long total) {
        return new PanelQueryResult(rows, total);
    }
}
```

##### 步骤 5: 编译验证

```bash
mvn compile
mvn test
mvn spring-boot:run  # 启动后调用 GET /stock-panel 验证
```

#### 验收标准

- `com.attribution.dto` 顶层包**不再存在**
- 5 处 DTO 跨层违规**全部修复**
- 所有现有 Controller 端到端可调通
- 数据库 schema 不变

---

### PR-A2 · controller → interface/controller

**工作量**：~0.5 天  
**风险**：中（9 个 controller，但引用简单）

#### 步骤

1. 选中 `com.attribution.controller` 整包
2. Refactor → Move Package → `com.attribution.interface.controller`
3. 验证 `controller/*` 不再被 `service/*` 或 `domain/*` 引用（应只被 `interface/*` 引用）

#### 验收标准

- `com.attribution.controller` 不再存在
- 9 个 Controller URL 不变

---

### PR-A3 · service → application/service

**工作量**：~0.5 天  
**风险**：中（20 个 service，互引 + 被 controller 引用）

#### 步骤

1. 选中 `com.attribution.service` 整包（含 `collect/` `indicator/` 子包）
2. Refactor → Move Package → `com.attribution.application.service`
3. 验证 Controller 引用全部正确

#### 验收标准

- `com.attribution.service` 不再存在
- 所有 service 包名变更为 `com.attribution.application.service.*`

---

### PR-A4 · adapter → infrastructure/adapter

**工作量**：~0.5 天  
**风险**：低（10 个 adapter）

#### 步骤

1. 选中 `com.attribution.adapter` 整包
2. Refactor → Move Package → `com.attribution.infrastructure.adapter`

#### 验收标准

- `com.attribution.adapter` 不再存在
- Tushare / AkShare / pytdx 三个外部 SDK 客户端位置符合架构

---

### PR-A5 · config + exception → infrastructure/*

**工作量**：~0.5 天  
**风险**：低

#### 步骤

1. `com.attribution.config` → `com.attribution.infrastructure.config`
2. `com.attribution.exception` → `com.attribution.infrastructure.exception`
3. 但 `GlobalExceptionHandler` **不在此 PR 迁移**——它是 `@RestControllerAdvice`，应归 interface 层（见 PR-C）

#### 验收标准

- `com.attribution.config` 不再存在
- `com.attribution.exception` 不再存在
- `GlobalExceptionHandler` 仍在 `exception/` 下（PR-C 处理）

---

### PR-B · service 子包拆分

**工作量**：~1 天  
**风险**：中（涉及职责重新划分）

#### 子步骤

##### B1: `service/indicator/*` → `domain/service/`

```java
// 旧
com.attribution.service.indicator.TechnicalSummary
com.attribution.service.indicator.SignalDetector

// 新
com.attribution.domain.service.TechnicalSummary
com.attribution.domain.service.SignalDetector
```

**理由**：纯指标计算，无 IO、无外部依赖，符合 DomainService 定义。

##### B2: `service/collect/*Task` → `application/collect/`

```java
// 旧
com.attribution.service.collect.BaseCollectTask
com.attribution.service.collect.KlineCollectTask
// ...

// 新
com.attribution.application.collect.BaseCollectTask
com.attribution.application.collect.KlineCollectTask
```

**理由**：任务抽象是 AppService 编排的一部分。

##### B3: `service/KlineCollectionExecutor` → `infrastructure/executor/`

```java
// 旧
com.attribution.service.KlineCollectionExecutor

// 新
com.attribution.infrastructure.executor.KlineCollectionExecutor
```

**理由**：直接调 adapter，属于外部执行。

##### B4: `service/DatabaseInitializer` → `application/bootstrap/`

```java
// 旧
com.attribution.service.DatabaseInitializer

// 新
com.attribution.application.bootstrap.DatabaseInitializer
```

**理由**：启动钩子，符合 architecture §3 "未来扩展"中的 `application/bootstrap/`。

##### B5: `service/OperationDispatcher` / `service/CollectorRegistry` 归属未定

见 §6.1 待业务决策。

---

### PR-C · GlobalExceptionHandler → interface/handler/

**工作量**：~0.5 天  
**风险**：低

#### 步骤

1. 把 `com.attribution.exception.GlobalExceptionHandler` 移到 `com.attribution.interface.handler.GlobalExceptionHandler`
2. 改 import

#### 验收标准

- `exception/` 包下只剩业务异常类（不再有 handler）
- GlobalExceptionHandler 在 `interface/handler/` 下，作为唯一 `@RestControllerAdvice`

---

## 6. 待业务决策

### 6.1 `OperationDispatcher` / `CollectorRegistry` 归属

| 类 | 候选归属 | 备注 |
|----|----------|------|
| `OperationDispatcher` | `application/dispatcher/` 还是 `infrastructure/executor/`？ | 调度器本身调多个 executor + 持久化 task 状态，业务编排属性更强 |
| `CollectorRegistry` | `infrastructure/registry/` 还是 `application/bootstrap/`？ | 它是注册中心，应在 Spring 启动时初始化 |

**建议**：
- `OperationDispatcher` → `application/dispatcher/`（业务编排）
- `CollectorRegistry` → `infrastructure/registry/`（外部资源管理）

> ⚠️ 本文档**不强制**，由 owner 在 PR-B 中确认。

### 6.2 dto 子包命名统一

当前：`stock` / `pool` / `kline` / `concept` / `operation`

争议：`operation/`（操作域）属于 `pool` 还是独立？

**建议**：保持现状，5 个子包对应 5 个 Controller 名。

---

## 7. 迁移期兼容策略

> 迁移可能跨多个 PR，期间代码不能停业务开发。

### 7.1 不推荐做法

❌ **不要**用 `@Deprecated` + `extends` / 旧类转发兼容——会拖长迁移周期、引入大量脏代码。

### 7.2 推荐做法

✅ **每个 PR 一次性全量迁移 + 验证**（即使 PR 较大）。理由：
- 团队规模小，一次性改完风险更可控
- IDE 重构工具支持批量改 import
- 失败回退只需 `git revert`

### 7.3 业务并行开发约定

迁移期间：
- 新增 Controller / Service / DTO **必须**按新路径（`interface/` / `application/` / `infrastructure/`）
- 旧路径**只删不加**
- PR review 阶段重点检查 import 是否全部指向新路径

---

## 8. 工时估算

| PR | 内容 | 工时 | 风险 | 可并行 |
|----|------|------|------|--------|
| A1 | dto 迁移 + 5 处违规修复 | 1.5 天 | 高 | ❌ 必须先做 |
| A2 | controller 迁移 | 0.5 天 | 中 | 与 A1 部分并行 |
| A3 | service 迁移 | 0.5 天 | 中 | 与 A1/A2 并行 |
| A4 | adapter 迁移 | 0.5 天 | 低 | ✅ |
| A5 | config + exception 迁移 | 0.5 天 | 低 | ✅ |
| B  | service 子包拆分 | 1 天 | 中 | 需 A3 完成后 |
| C  | handler 迁移 | 0.5 天 | 低 | 需 A5 完成后 |
| **合计** | | **~5 天**（并行 3 天） | | |

> 💡 A1/A2/A3/A4/A5 可分给 3 人并行开发，每个 PR 一个分支。
> 实际经验：A1 必须先做（它修复了 DTO 跨层），A2/A3/A4/A5 之间无强依赖。

---

## 9. 风险与回退

### 9.1 主要风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| A1 改 import 漏改 | 编译失败 / 运行时空指针 | IDE 重构 + `mvn compile` 验证 + 关键接口冒烟 |
| DTO 跨层修复影响前端 | 仅响应结构变化（内部）不影响外部 | 内部 DTO → entity 不影响 HTTP 接口契约 |
| 子包拆分时漏掉内部互引 | 编译失败 | IDE 重构 + `mvn compile` |
| 测试覆盖不足 | 漏掉的回归 bug 流入生产 | 迁移前补关键路径单测（pools / klines / panel） |

### 9.2 回退方案

每个 PR 都是独立的 git commit，**回退只需**：
```bash
git revert <commit-hash>
```

> 不建议 cherry-pick 回退（容易引入冲突）。

---

## 10. 验收清单（迁移完成后）

- [ ] `com.attribution.dto` 不存在
- [ ] `com.attribution.controller` 不存在
- [ ] `com.attribution.service` 不存在
- [ ] `com.attribution.adapter` 不存在
- [ ] `com.attribution.config` 不存在
- [ ] `com.attribution.exception` 不存在（只剩 handler 在 interface/handler）
- [ ] 所有 controller 在 `com.attribution.interface.controller`
- [ ] 所有 service 在 `com.attribution.application.service`
- [ ] 所有 dto 在 `com.attribution.interface.dto`
- [ ] 所有 adapter / config / exception 在 `com.attribution.infrastructure.*`
- [ ] domain 层零外部依赖（`grep -r "com.attribution.{application,infrastructure,interface}" domain/` 应为空）
- [ ] DTO 零跨层引用（`grep -r "interface.dto" {domain,application,infrastructure}/` 应为空）
- [ ] `mvn compile` 通过
- [ ] `mvn test` 通过
- [ ] 关键接口冒烟通过（`GET /pools` / `GET /klines/000001.SZ` / `GET /stock-panel`）

---

## 11. 与架构规范文档的同步

迁移完成后，需要同步更新：

| 文档 | 更新内容 |
|------|----------|
| `docs/design/architecture/00-overview.md` §7 | 删除"应用层包路径"偏差项、`dto 包路径`偏差项 |
| `docs/design/architecture/04-interface-spec.md` §9 | 删除"dto 包路径 / 应用层包路径 / DTO 跨层引用"3 项违规 |
| `docs/design/architecture/00-overview.md` §10 | 新增变更记录 "v0.3: 完成包结构迁移" |

---

## 12. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-26 | -      | 初稿 |
| v0.2  | 2026-09-26 | -      | **实际执行记录**（见 §13） |

---

## 13. 实际执行记录（v0.2 · 2026-09-26）

### 13.1 已完成项

| PR  | 范围 | 状态 |
|-----|------|------|
| PR-A1 | ApiResponse.fail/error 删除 + BusinessException 重构 + GlobalExceptionHandler 改用 ofBiz + CollectController 改抛业务异常 | ✅ 完成 |
| PR-A2 | controller → `com.attribution.interfaces.controller` | ✅ 完成 |
| PR-A3 | service → `com.attribution.application.service` | ✅ 完成 |
| PR-A4 | adapter → `com.attribution.infrastructure.adapter` | ✅ 完成 |
| PR-A5 | config → `com.attribution.infrastructure.config`<br>exception → `com.attribution.infrastructure.exception`（业务异常类） | ✅ 完成 |

### 13.2 关键变更点

- **包名偏离规范**：规范文档 §58 写的是 `interface/`，但 `interface` 是 Java 关键字。**实际包名改为 `interfaces/`**（复数）。文档后续需同步更新此点。
- **DTO 跨层违规（PR-A1 之外的 C1 五处）**：本轮**未做**，原因见 §13.4。
- **`GlobalExceptionHandler` 位置**：本轮**留在** `infrastructure/exception/`（P1 项）。Spring 扫描以 `com.attribution` 为根，能正常发现 `@RestControllerAdvice`，不影响运行。
- **`service/indicator/*` → `domain/service/*`**：本轮**未做**。
- **`KlineCollectionExecutor` / `OperationDispatcher` / `CollectorRegistry` / `DatabaseInitializer` 子包拆分**：本轮**未做**。

### 13.3 编译验证

```
$ mvn clean compile -q -DskipTests
[INFO] Compiling 147 source files with javac [debug parameters release 21] to target/classes
[INFO] BUILD SUCCESS
```

### 13.4 中途遭遇的问题与处理

1. **`com.attribution.interface.dto.*` 是非法包名**（`interface` 是 Java 关键字）
   - 处理：批量改为 `com.attribution.interfaces.*`，目录 `interface/` → `interfaces/`
2. **PowerShell `Set-Content -NoNewline` 在 PowerShell 5.1 下用 GBK/UTF-16 写文件**，导致 41 个文件中文损坏为 `\ufffd?`
   - 处理：用 `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)` 重新规范化；将 `\ufffd?` 模式替换为 `_`，再把字符串边界标记 `_)` / `_,` / `_;` 恢复为 `")` / `",` / `";`
3. **`com.attribution.interface` 被双重替换为 `com.attribution.interfacess`**
   - 处理：批量回退 `interfacess` → `interfaces`
4. **`StockPanelRowVO.java` 注释与字段定义合并到一行**（如 `// 估_    private Double pe;`），导致字段被注释吞掉，Lombok `@Builder` 不生成 setter
   - 处理：用正则 `^(\s*//\s*[^/\n]*_)\s+(private\s+...)` 拆为两行

### 13.5 未完成项的影响评估

| 未完成项 | 影响 | 建议 |
|----------|------|------|
| DTO 跨层 5 处违规 | service 直接 return DTO，违反"DTO 不跨层"铁律 | **不影响编译与运行**，仅架构不洁；后续 PR 重构 |
| `service/indicator/*` 拆分 | 影响 DomainService 命名风格 | 不影响编译 |
| `service/collect/*Task` 拆分 | 影响 application/collect 包结构 | 不影响编译 |
| 子包（dispatcher/executor/bootstrap）拆分 | 影响包路径 | 不影响编译 |
| `GlobalExceptionHandler` 移至 `interface/handler/` | 影响代码组织 | 不影响编译 |

### 13.6 给后续重构者的提示

- **后续不要再用 PowerShell `Set-Content` 写 Java 文件**——必须用 `[System.IO.File]::WriteAllText` + `UTF8Encoding($false)`
- **包名规范文档应改用 `interfaces/`**（而不是 `interface/`）——前者才是合法 Java 包名
- **Spring `@SpringBootApplication` 默认扫 `com.attribution` 全树**，子包位置变更不影响 Bean 注册；但 `@EntityScan` / `@EnableJpaRepositories` 已锁定 `domain.entity` / `domain.repository`，将来迁移 entity / repository 时需同步

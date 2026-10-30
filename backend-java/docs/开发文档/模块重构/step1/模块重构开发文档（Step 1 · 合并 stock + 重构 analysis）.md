# 模块重构开发文档（Step 1 · market+concept 合并为 stock，user 重构为 analysis）

> 状态：**方案设计，暂不改代码**
> 日期：2026-10-30
> 适用范围：`backend-java` 全部 Maven 模块
> 数据库依据：本文档同目录 `attribution-2026-10-30_200118-dump.sql`（业务库）+ `raw_data-2026-10-30_200122-dump.sql`（采集库）
> 配套文档：`../../../工程索引.md`（当前工程索引）、`../../../规范文档/多库分工与数据源规范.md`、`../../../规范文档/纵向分层规范/*`

---

## 0. 一句话结论

> 把「股票信息 + 概念板块 + 行情看板」合并为 **`attribution-stock`**；
> 把「操作池 + 池级操作」从 `attribution-user` 迁出并扩展为 **`attribution-analysis`**（操作池 + 监控 + 预警 + 归因）。
> 依赖方向保持**单向无环**：`app → analysis → stock → collector-client → common`，`app → auth → common`。
> **本 Step 不动代码、不动表结构、不改前端 API 契约。**

---

## 1. 背景：为什么要重划

### 1.1 现状的三个问题

| # | 问题 | 证据 |
|---|---|---|
| **P1** | **模块名与内容不符** | `attribution-user` 里**没有任何 user 相关代码**，全部是 `PoolController` / `PoolService`（自选池 + 操作池）；`attribution-concept` 只占 39 文件，而 `attribution-market` 占 133 文件，两者同属「股票数据展示」却分成两个 Maven 模块 |
| **P2** | **跨模块直接调 Mapper**（违反规范） | `attribution-market` 的 `StockInfoServiceImpl` 直接注入 `StockPoolMembershipQueryMapper` 查 `stock_pool_members`（`user` 模块的表）；`attribution-concept` 里又抄了一份 `ConceptPoolMembershipQueryMapper`——**同一段逻辑两份实现** |
| **P3** | **采集代理错位** | `CollectProxyController`（`/api/collect/**`）与 `CollectLogController` 住在 `attribution-market`，但它们跟「股票行情」毫无关系，属于采集基础设施 |

### 1.2 目标形态

```
backend-java/
├─ pom.xml                       # parent
├─ attribution-common/           # 无业务依赖：ApiResponse / PageResult / 异常 / WebConfig / TopN
├─ attribution-collector-client/ # Feign 调 collector-python：Client + Fallback + 目录缓存
├─ attribution-auth/             # 登录 / JWT / 账户 / RBAC（sys_* 5 张表）
├─ attribution-stock/            # ★ 股票信息 + 概念 + 大盘 + 行情（raw_data 库只读）
├─ attribution-analysis/         # ★ 操作池 + 监控 + 预警 + 归因（attribution 库读写）
└─ attribution-app/              # 启动类 + application.yml + MyBatis-Plus 配置（唯一 fat jar）
```

**模块数：7 → 6**（`market` + `concept` 合并为 `stock`；`user` 重构为 `analysis`）。

### 1.3 职责定位一句话

| 模块 | 一句话 | 写库 | 读库 |
|---|---|---|---|
| `attribution-stock` | **股票及概念的市场数据展示**（客观、全局唯一） | ❌ 不写 | `raw_data`（全部）+ `attribution`（**不读池表**） |
| `attribution-analysis` | **围绕操作池的监控 / 预警 / 归因**（主观、按用户） | ✅ `attribution` | `attribution` + `raw_data`（经 stock 的 Service） |
| `attribution-auth` | **身份与权限** | ✅ `attribution`（`sys_*`） | `attribution` |

---

## 2. 目标依赖图

```text
                    ┌──────────────────┐
                    │ attribution-app  │  启动 / 装配 / 配置
                    └────────┬─────────┘
             ┌───────────────┼───────────────┬──────────────┐
             ▼               ▼               ▼              ▼
    ┌─────────────┐  ┌────────────┐  ┌─────────────┐  ┌──────────────┐
    │ attribution-│  │ attribution│  │ attribution-│  │ attribution- │
    │   analysis  │  │   stock    │  │    auth     │  │  collector-  │
    └──────┬──────┘  └─────┬──────┘  └──────┬──────┘  │   client     │
           │               │                │         └──────┬───────┘
           └──────────────▶│                │                │
              只调 Service  └────────────────┴────────────────┘
                                             ▼
                                      attribution-common
```

**边的定义**（每条边只能单向）：

| 边 | 内容 | 依据 |
|---|---|---|
| `analysis → stock` | 池成员查股票名/行业；监控预警读行情；归因读四数据面 | 复用现有 `user → market` 边，**不新增依赖方向** |
| `stock → collector-client` | 概念实时行情、分钟 K 透传 collector | 现状已有 |
| `analysis → collector-client` | 建池后触发 K 线采集 | 现状已有（`user`） |
| `auth → common` | 独立，无业务依赖 | 现状已有 |
| `common` | **不依赖任何业务模块**，不持有 Mapper | 保持 |

### 2.1 铁律

1. **禁止 Maven 循环依赖**（`stock ↔ analysis` 绝对不允许同时存在）。
2. **禁止跨模块调 Mapper**——只调 Service 接口（《Service层规范》§2.4）。
3. **`stock` 不认识"池"**——`stock` 模块内**零** `stock_pool_*` 表引用。
4. **`stock` 不写任何库**——采集域只读（符合《多库分工与数据源规范》§2.1 铁律 3）。
5. 新增模块 → 手工在 `AttributionApp.@MapperScan` 加包名。

---

## 3. 目标模块详细设计

### 3.1 `attribution-stock`

**包名**：`com.attribution.stock`
**Java 包分层**（**合并的是 Maven 模块，Java 包仍分子域**，显著降低迁移风险）：

```
com.attribution.stock/
├─ controller/
│  ├─ stock/     StockController, KlineController, MinuteKlineController,
│  │             PanelController, StockAnalysisController
│  ├─ concept/   ConceptQueryController, ConceptBoardController, ConceptQuoteController
│  └─ board/     DataBoardController
├─ service/      StockInfoService, KlineService, DataBoardService, ConceptService
├─ service/impl/
├─ mapper/       ← 25 个 market Mapper + 4 个 concept Mapper（统一 @DS("raw")）
├─ entity/       ← 29 个采集表 PO
├─ dto/  vo/  converter/
└─ util/         IndicatorUtil（技术指标算法）
```

**为什么不分子包**：现状 `market.vo.ConceptBriefVO` 与 `concept.vo.ConceptBriefVO` **同名**（还有 `ConceptSnapshotVO`、`PoolMembershipVO`）——合并后若平铺会编译冲突。分子包可自然避开，见 §7.1。

**保留的对外 API（URL 全部不变）**：

| 前缀 | Controller | 端点数 |
|---|---|---|
| `/api/stocks/**` | `StockController` + `StockAnalysisController` | 8 |
| `/api/klines/**` | `KlineController` | 8 |
| `/api/minute-klines/**` | `MinuteKlineController` | 1 |
| `/api/stock-panel/**` | `PanelController` | 1 |
| `/api/data-board/**` | `DataBoardController` | 20 |
| `/api/concepts/**` | 3 个 Concept Controller | 12 |

**移出 `stock` 的东西**：

| 迁出项 | 去向 | 理由 |
|---|---|---|
| `CollectProxyController`（`/api/collect/**`） | → `attribution-analysis` 或独立 `attribution-collect-proxy` | P3：与股票行情无关 |
| `CollectLogController` + `CollectLogService` + `CollectLogPO` + `CollectLogMapper` + `CollectLogVO` + `CollectLogConverter` | → 同上 | 采集日志属采集域 |
| `StockPoolMembershipQueryMapper` + `StockPoolMembershipRow` + 其 XML | → 删除（见 §3.4） | P2：消除跨模块调 Mapper |
| `PoolMembershipVO`（market 侧） | → 删除 | 同上 |

### 3.2 `attribution-analysis`

**包名**：`com.attribution.analysis`
**来源**：`attribution-user` 整体迁入 + 新增监控/预警/归因子域。

```
com.attribution.analysis/
├─ controller/
│  ├─ pool/       PoolController（现有，URL 不变）
│  ├─ monitor/    MonitorRuleController     ← 新增
│  ├─ alert/      AlertController           ← 新增
│  └─ attribution/AttributionController    ← 新增
├─ service/  service/impl/
├─ mapper/  entity/  dto/  vo/  converter/
└─ config/         PoolTaskExecutorConfig（现有）
```

**现有能力平移**（`com.attribution.user.*` → `com.attribution.analysis.pool.*`）：

| 原类 | 新类 |
|---|---|
| `PoolController` | `controller/pool/PoolController` |
| `PoolService` / `PoolServiceImpl` | `service/pool/PoolService` / `service/pool/impl/PoolServiceImpl` |
| `PoolConverter` | `converter/pool/PoolConverter` |
| `StockPoolPO` / `PoolMemberPO` / `PoolOperationPO` | `entity/pool/*PO` |
| `StockPoolMapper` / `PoolMemberMapper` / `PoolOperationMapper` | `mapper/pool/*Mapper` |
| `PoolCreateRequest` … `PoolQuery` | `dto/pool/*` |
| `PoolVO` / `PoolDetailVO` / `PoolMemberVO` / `PoolOperationVO` … | `vo/pool/*` |
| `PoolTaskExecutorConfig` | `config/PoolTaskExecutorConfig` |

**新增子域（后续 Step，本 Step 只留骨架与表设计）**：

| 子域 | 职责 | 依赖 |
|---|---|---|
| `monitor` | 监控规则 CRUD（对池成员设置阈值/条件） | `stock`（读行情） |
| `alert` | 预警记录（触发记录、去重、通知） | `monitor` + `stock` |
| `attribution` | 归因分析（复用 `DataBoardService.analysis` 的算法，但**只针对池内股票**） | `stock` |

> ⚠️ **归因分析当前只有壳**：`StockAnalysisController` → `DataBoardServiceImpl.analysis(symbol, days)` 是**单股票**的。重构成"池级归因"是**新功能**，不属于本次搬迁范围，本次**保持原样平移到 `stock`**（它本质是行情数据的聚合）。

### 3.3 `attribution-auth` —— 保持不变

登录 / 注册 / JWT / refresh / 验证码 / 忘记密码 / 用户管理 / 角色 / 权限，共 5 张 `sys_*` 表。**本次零改动**（仅 pom 依赖顺序可能调整）。

### 3.4 ⚠️ 必须同时解决的 P2：`stock → analysis` 反向依赖

**现状**（`market` 直接查 `user` 的表）：

```text
attribution-market/.../mapper/StockPoolMembershipQueryMapper.java  → 查 stock_pool_members + stock_pools
attribution-concept/.../mapper/ConceptPoolMembershipQueryMapper.java → 同样的 SQL，另一份
```

**重划后若原样搬运**：`stock → analysis`（读池）+ `analysis → stock`（读股票） = **Maven 循环依赖，直接构建失败**。

**决策：本 Step 采用「前端二次查询」，删除后端 `with_pools` 内嵌。**

| 项 | 处理 |
|---|---|
| 后端删除 | `StockPoolMembershipQueryMapper` + `StockPoolMembershipRow` + `StockPoolMembershipQueryMapper.xml`；`ConceptPoolMembershipQueryMapper` + `ConceptPoolMembershipRow` + 其 XML |
| 后端改 | `StockInfoServiceImpl` 去掉 `stockPoolMembershipQueryMapper` 注入与 `poolMapBySymbol()`；`ConceptServiceImpl` 同理；`StockInfoVO.pools` / `ConceptMemberItemVO.pools` 字段去掉；`StockPanelQuery.withPools` / `ConceptMemberQuery.withPools` 去掉 |
| 前端改 | 股票列表页 / 概念成分股页自行合并池信息（`GET /api/pools/by-symbol/{symbol}` 已在 `poolStore.findPoolsBySymbol` 封装） |
| URL 影响 | **无 URL 变更**，只是响应体少一个 `pools` 字段 |

> 📌 **备选方案（不推荐）**：保留 `with_pools`，把 `StockPoolMembershipQueryMapper` 放进 `attribution-common`。违背 common「无业务依赖、不持有 Mapper」的定位。
> 📌 **备选方案 2**：让 `stock` 依赖 `analysis`。直接造成循环，且违背"客观数据不被主观数据引用"的分层原则。

> 🔴 **关联待决项**：`stock_pools.owner_id` 字段**存在但从未被赋值**（`PoolServiceImpl.create()` 未设，`list()` 也未按 owner 过滤）→ **当前所有用户共享同一批池**。
> 若后续改为 per-user 池，`with_pools` 内嵌**必然泄露他人池名**，删除它是必需的前置。本 Step 先删除，隔离逻辑留到后续 Step。

---

## 4. 数据库归属（基于 2026-10-30 dump）

### 4.1 `attribution` 库（业务库，10 张表）

| 表 | 归属模块 | 数据源 | 说明 |
|---|---|---|---|
| `sys_users` | `auth` | `biz` | 用户 |
| `sys_roles` | `auth` | `biz` | 角色 |
| `sys_permissions` | `auth` | `biz` | 权限 |
| `sys_user_roles` | `auth` | `biz` | 用户-角色 |
| `sys_role_permissions` | `auth` | `biz` | 角色-权限 |
| `stock_pools` | `analysis` | `biz` | 操作池 |
| `stock_pool_members` | `analysis` | `biz` | 池成员 |
| `pool_operations` | `analysis` | `biz` | 池级操作 |
| `collect_logs` | `analysis`（或独立采集模块） | `biz` | 采集日志（Collector 写，Java 只读） |
| `collect_logs_legacy_20261029` | — | — | 🗑️ 历史遗留，建议 drop |

### 4.2 `raw_data` 库（采集库，32 张表，Java 全部只读）

| facet | 表 | 归属模块 | 现有 Mapper |
|---|---|---|---|
| tech | `tech_daily` | `stock` | `TechKlineMapper` |
| tech | `tech_adj_factor` | `stock` | `AdjFactorMapper` |
| tech | `tech_suspend_d` | `stock` | `SuspendMapper` |
| tech | `tech_namechange` | `stock` | `NameChangeMapper` |
| tech | `tech_trade_cal` | `stock` | `CalendarMapper` |
| capital | `capital_moneyflow` | `stock` | `MoneyflowMapper` |
| capital | `capital_moneyflow_hsgt` | `stock` | `MoneyflowHsgtMapper` |
| capital | `capital_margin` | `stock` | `MarginMapper` |
| capital | `capital_margin_detail` | `stock` | `MarginDetailMapper` |
| capital | `capital_top_list` | `stock` | `TopListMapper` |
| capital | `capital_top_inst` | `stock` | `TopInstMapper` |
| capital | `capital_block_trade` | `stock` | `BlockTradeMapper` |
| capital | `capital_hsgt_top10` | `stock` | `HsgtTop10Mapper` |
| capital | `capital_limit_list_d` | `stock` | `LimitListMapper` |
| capital | `capital_stk_holdernumber` | `stock` | `HolderNumMapper` |
| fundamental | `fundamental_stock_basic` | `stock` | `StockInfoMapper` |
| fundamental | `fundamental_daily_basic` | `stock` | `DailyBasicMapper` |
| fundamental | `fundamental_income` | `stock` | `FinReportMapper` |
| fundamental | `fundamental_dividend` | `stock` | `DividendMapper` |
| fundamental | `fundamental_top10_holders` | `stock` | `Top10HolderMapper` |
| fundamental | `fundamental_top10_floatholders` | `stock` | `Top10FloatMapper` |
| fundamental | `fundamental_index_member` | `stock` | `IndexMemberMapper` |
| fundamental | `fundamental_market_daily` | `stock` | `MarketDailyMapper` |
| fundamental | `fundamental_sector_daily` | `stock` | `SectorDailyMapper` |
| fundamental | `fundamental_concept` | `stock` | `ConceptMapper` |
| fundamental | `fundamental_concept_member` | `stock` | `ConceptMemberMapper` |
| fundamental | `fundamental_concept_index` | `stock` | `ConceptIndexMapper` |
| fundamental | `fundamental_concept_snapshot` | `stock` | `ConceptSnapshotMapper` |
| news | `news_article` | `stock` | `NewsMapper` |
| — | `fundamental_index_daily` | ⚠️ **无 Mapper** | dump 存在但代码未用（与 `fundamental_market_daily` 结构对齐） |
| — | `fundamental_stock_concept` | ⚠️ **无 Mapper** | 历史遗留，当前 collector 不写该表（见《采集能力清单》§） |

**表数校验**：Java 侧 29 个 `@DS("raw")` Mapper ↔ dump 中 30 张采集表（`fundamental_index_daily` / `fundamental_stock_concept` 无 Mapper）。
业务库 5 + 3 = 8 个 `@DS` 缺省 Mapper（`sys_*` 5 + `stock_pool_*` 2 + `pool_operations` 1）+ `CollectLogMapper` 1 = 9。

### 4.3 新增表建议（`analysis` 模块，后续 Step）

> ⚠️ **本 Step 不建表**，仅登记设计。

| 表 | 库 | 用途 | 关键列 |
|---|---|---|---|
| `monitor_rules` | `attribution` | 监控规则 | `id, pool_id, symbol, rule_type, threshold, window, enabled, created_at` |
| `alert_records` | `attribution` | 预警记录 | `id, rule_id, pool_id, symbol, level, message, triggered_at, status` |
| `attribution_reports` | `attribution` | 归因分析结果 | `id, pool_id, symbol, range_start, range_end, result_json, created_at` |
| `analysis_tasks` | `attribution` | 分析任务（异步） | `id, pool_id, task_type, status, progress, result_summary, created_at` |

**建议统一 `owner_id`**（关联 `sys_users.id`），与 `stock_pools.owner_id` 语义一致。

---

## 5. 文件级迁移映射表

### 5.1 `attribution-market` → `attribution-stock`（133 文件）

| 原路径（Maven 模块 / Java 包） | 新路径 | 备注 |
|---|---|---|
| `attribution-market/.../com/attribution/market/**` | `attribution-stock/.../com/attribution/stock/**` | 包名替换 `market` → `stock` |
| `attribution-market/.../market/controller/{Stock,Kline,MinuteKline,Panel,StockAnalysis}Controller.java` | `.../stock/controller/stock/*` | 子包隔离 |
| `attribution-market/.../market/controller/DataBoardController.java` | `.../stock/controller/board/DataBoardController.java` | |
| `attribution-market/.../market/controller/CollectProxyController.java` | ➡️ **移出** | → `attribution-analysis`（见 §3.1） |
| `attribution-market/.../market/controller/CollectLogController.java` | ➡️ **移出** | 同上 |
| `attribution-market/.../market/entity/*.java`（25 个 PO） | `.../stock/entity/*.java` | 表名不变，**`@DS` 在 Mapper 上，PO 不动** |
| `attribution-market/.../market/mapper/*.java`（25 个） | `.../stock/mapper/*.java` | `@DS("raw")` 保持 |
| `attribution-market/.../market/mapper/StockPoolMembershipQueryMapper.java` | 🗑️ **删除** | P2（§3.4） |
| `attribution-market/.../market/mapper/row/StockPoolMembershipRow.java` | 🗑️ **删除** | 同上 |
| `attribution-market/.../market/util/IndicatorUtil.java` | `.../stock/util/IndicatorUtil.java` | 不变 |
| `attribution-market/.../market/vo/*`（含 `PoolMembershipVO`） | `.../stock/vo/*` | `PoolMembershipVO` 🗑️ 删除 |
| `attribution-market/src/main/resources/mapper/StockInfoMapper.xml` | `attribution-stock/src/main/resources/mapper/StockInfoMapper.xml` | namespace 需改 |
| `attribution-market/src/main/resources/mapper/StockPoolMembershipQueryMapper.xml` | 🗑️ **删除** | |

### 5.2 `attribution-concept` → `attribution-stock`（39 文件）

| 原路径 | 新路径 | 备注 |
|---|---|---|
| `attribution-concept/.../com/attribution/concept/**` | `attribution-stock/.../com/attribution/stock/concept/**` | 包名 `concept` → `stock.concept` |
| `.../concept/controller/*` | `.../stock/controller/concept/*` | |
| `.../concept/service/ConceptService.java` | `.../stock/service/concept/ConceptService.java` | |
| `.../concept/service/impl/ConceptServiceImpl.java` | `.../stock/service/concept/impl/ConceptServiceImpl.java` | |
| `.../concept/mapper/{Concept,ConceptMember,ConceptIndex,ConceptSnapshot}Mapper.java` | `.../stock/mapper/concept/*Mapper.java` | `@DS("raw")` 保持 |
| `.../concept/mapper/ConceptPoolMembershipQueryMapper.java` | 🗑️ **删除** | P2 |
| `.../concept/mapper/row/ConceptPoolMembershipRow.java` | 🗑️ **删除** | 同上 |
| `.../concept/entity/*.java`（4 PO） | `.../stock/entity/concept/*PO.java` | |
| `.../concept/vo/*.java` | `.../stock/vo/concept/*VO.java` | 含 `PoolMembershipVO` 🗑️ |
| `.../concept/converter/ConceptConverter.java` | `.../stock/converter/concept/ConceptConverter.java` | |
| `attribution-concept/src/main/resources/mapper/{ConceptMapper,ConceptMemberMapper}.xml` | `attribution-stock/src/main/resources/mapper/concept/*.xml` | namespace 需改 |

> 📌 **XML 位置约定**：`mybatis-plus.mapper-locations: classpath*:/mapper/**/*.xml` 是**递归**通配，XML 放在 `mapper/concept/` 下**可被扫描到**。但 namespace 必须与 Mapper 接口全限定名一致。

### 5.3 `attribution-user` → `attribution-analysis`（25 文件）

| 原路径 | 新路径 |
|---|---|
| `attribution-user/.../com/attribution/user/controller/PoolController.java` | `attribution-analysis/.../com/attribution/analysis/controller/pool/PoolController.java` |
| `.../user/service/PoolService.java` | `.../analysis/service/pool/PoolService.java` |
| `.../user/service/impl/PoolServiceImpl.java` | `.../analysis/service/pool/impl/PoolServiceImpl.java` |
| `.../user/converter/PoolConverter.java` | `.../analysis/converter/pool/PoolConverter.java` |
| `.../user/entity/*.java`（3 PO） | `.../analysis/entity/pool/*PO.java` |
| `.../user/mapper/*.java`（3 Mapper） | `.../analysis/mapper/pool/*Mapper.java` |
| `.../user/dto/*.java`（6） | `.../analysis/dto/pool/*` |
| `.../user/vo/*.java`（8） | `.../analysis/vo/pool/*` |
| `.../user/config/PoolTaskExecutorConfig.java` | `.../analysis/config/PoolTaskExecutorConfig.java` |
| `attribution-user/src/main/resources/mapper/PoolMemberMapper.xml` | `attribution-analysis/src/main/resources/mapper/pool/PoolMemberMapper.xml` |

> ⚠️ `PoolServiceImpl` 注入 `com.attribution.market.service.StockInfoService` → 改为 `com.attribution.stock.service.stock.StockInfoService`。
> ⚠️ `PoolServiceImpl` 注入 `com.attribution.market.vo.StockBriefVO` → 改为 `com.attribution.stock.vo.stock.StockBriefVO`。
> ⚠️ `StockBriefVO` 被 `analysis` 依赖 → **`StockBriefVO` 必须放在 `stock` 的公共 vo 包**（不能放子包，否则 analysis 要 import 子包路径，可接受但不够干净；建议 `com.attribution.stock.vo.StockBriefVO`）。

### 5.4 POM 改动

**`backend-java/pom.xml`**（parent）：

```xml
<modules>
  <module>attribution-common</module>
  <module>attribution-collector-client</module>
  <module>attribution-stock</module>      <!-- 原 attribution-market -->
  <module>attribution-analysis</module>   <!-- 原 attribution-user -->
  <module>attribution-auth</module>
  <module>attribution-app</module>
</modules>

<dependencyManagement>
  ...
  <dependency><groupId>com.attribution</groupId><artifactId>attribution-stock</artifactId><version>${project.version}</version></dependency>
  <dependency><groupId>com.attribution</groupId><artifactId>attribution-analysis</artifactId><version>${project.version}</version></dependency>
  ...
</dependencyManagement>
```

**`attribution-stock/pom.xml`**（原 market）：

```xml
<artifactId>attribution-stock</artifactId>
<dependencies>
  <dependency>attribution-common</dependency>
  <dependency>attribution-collector-client</dependency>
  <dependency>mybatis-plus-spring-boot3-starter</dependency>
  <dependency>dynamic-datasource-spring-boot3-starter</dependency>  <!-- ★ 必须保留：@DS("raw") 需要编译期可见 -->
  <dependency>lombok (optional)</dependency>
</dependencies>
```

> ⚠️ **`dynamic-datasource` 依赖必须跟着 Mapper 走**。原 market + concept 各引一份，合并后只需一份。**不能只放 app**——`app → stock`，依赖方向反了，stock 编译期拿不到 `@DS` 类。

**`attribution-analysis/pom.xml`**（原 user）：

```xml
<artifactId>attribution-analysis</artifactId>
<dependencies>
  <dependency>attribution-common</dependency>
  <dependency>attribution-collector-client</dependency>
  <dependency>attribution-stock</dependency>          <!-- ★ 新增（原 user 依赖 market） -->
  <dependency>mybatis-plus-spring-boot3-starter</dependency>
  <dependency>lombok (optional)</dependency>
</dependencies>
```

> `attribution-analysis` **不需要** `dynamic-datasource`——它的 Mapper 全在业务库（不标 `@DS`）。

**`attribution-app/pom.xml`**：

```xml
<dependency>attribution-stock</dependency>      <!-- 原 attribution-market + attribution-concept -->
<dependency>attribution-analysis</dependency>   <!-- 原 attribution-user -->
<dependency>attribution-auth</dependency>
<dependency>attribution-common</dependency>
<dependency>attribution-collector-client</dependency>
```

> 🔴 **`attribution-concept` 的依赖从 app 里删掉**——它不再是独立模块。

### 5.5 `AttributionApp` 启动类

```java
@MapperScan({
    "com.attribution.stock.mapper",        // ★ 原 market.mapper + concept.mapper
    "com.attribution.analysis.mapper",     // ★ 原 user.mapper
    "com.attribution.auth.mapper"
})
@EnableFeignClients("com.attribution.collector.client")
```

> ⚠️ `com.attribution.stock.mapper` 的**递归扫描**会覆盖 `stock.mapper.concept` 子包（MyBatis-Plus 默认递归）。若担心歧义，可显式列出两个包。

---

## 6. 实施步骤（Step 1 拆分建议）

> 📌 原则：**每一步独立提交 + 独立编译通过**，便于回滚。

| 步 | 动作 | 验证 |
|---|---|---|
| **1** | 新建 `attribution-stock` 模块骨架（pom + 目录），`attribution-market` / `attribution-concept` **暂不动** | `mvn -pl attribution-stock -am compile` 通过 |
| **2** | 迁移 `attribution-market` → `attribution-stock`：改包名 `market`→`stock`，移 `Collect*` 相关到 `attribution-analysis` | 编译通过 |
| **3** | 迁移 `attribution-concept` → `attribution-stock`：`com.attribution.concept` → `com.attribution.stock.concept`，**处理 3 组同名 VO**（§7.1） | 编译通过 |
| **4** | 合并 XML：namespace 改全限定名；`mapper-locations` 递归扫描确认生效 | `mvn package` + 启动不报 "Invalid bound statement" |
| **5** | **删除 `with_pools`**（§3.4）：删 2 Mapper + 2 Row + 2 XML，改 2 个 ServiceImpl、2 个 VO、2 个 Query | 编译通过；`/api/stock-panel/`、`/api/concepts/concept-board/members` 响应体无 `pools` |
| **6** | 迁移 `attribution-user` → `attribution-analysis`：包名 `user`→`analysis.pool`，改 `StockInfoService` / `StockBriefVO` 引用 | 编译通过 |
| **7** | 更新 parent pom `<modules>` / `dependencyManagement`，删 `attribution-market` / `attribution-concept` / `attribution-user` 目录 | `mvn clean package` 通过 |
| **8** | 更新 `AttributionApp.@MapperScan` + `app/pom.xml` | 启动成功，`/actuator/health` = UP |
| **9** | **前端适配**（`with_pools` 移除）：`StockInfoList.vue`、`ConceptMembersList.vue`、`stock-info/api.ts`、`concept-board/api.ts` | 前端构建通过，列表页池标签不报错 |
| **10** | 更新 `docs/工程索引.md` + `docs/规范文档/拆分方案.md` | — |

### 6.1 回归检查清单

**后端启动**
- [ ] `mvn clean package` 全绿
- [ ] 应用启动无 `Invalid bound statement (not found)`（XML namespace 错配的典型症状）
- [ ] `GET /actuator/health` = UP
- [ ] 日志无 `can not find datasource`（`strict: true` 下漏标 `@DS` 的信号）

**双数据源**
- [ ] `GET /api/stock-panel/?page=1` → 打到 `raw_data` 的 `fundamental_stock_basic`
- [ ] `GET /api/data-board/tech/kline/{symbol}` → `raw_data.tech_daily`
- [ ] `GET /api/klines/{symbol}` → `raw_data.tech_daily`
- [ ] `GET /api/concepts/` → `raw_data.fundamental_concept`
- [ ] `GET /api/pools` → `attribution.stock_pools`
- [ ] `GET /api/users/` → `attribution.sys_users`
- [ ] `GET /api/collect/logs` → `attribution.collect_logs`

**业务功能**
- [ ] 股票列表分页 / 筛选 / 排序正常
- [ ] K 线图表 + 17 个指标列正常（warmup 120 根逻辑未被破坏）
- [ ] 概念板块看板 + 成分股 + 概念 K 线正常
- [ ] 数据看板四个面（tech/capital/fundamental/overview）正常
- [ ] 自选池 CRUD + 加成员 + 备注 + 反向查询正常
- [ ] 池级 K 线采集操作（建任务 → 轮询进度 → 取消）正常
- [ ] 采集代理 `/api/collect/services` `/api/collect/query/{name}` `/api/collect/tasks/**` 正常
- [ ] 登录 / 注册 / 刷新 token / RBAC 正常

**前端**
- [ ] 股票列表页「所属池」标签（改前端二次查询后）
- [ ] 概念成分股「所属池」标签
- [ ] 「加入操作池」弹窗（`AddToPoolDialog.vue`）
- [ ] 操作池列表 / 详情 / 成员管理

---

## 7. 已知冲突点与处理

### 7.1 ⚠️ 三组同名 VO（编译冲突）

| 类名 | `market` 侧 | `concept` 侧 | 处理 |
|---|---|---|---|
| `ConceptBriefVO` | `market.vo.ConceptBriefVO` | `concept.vo.ConceptBriefVO` | 分子包：`stock.vo.concept.ConceptBriefVO` vs `stock.vo.ConceptBriefVO`（或统一到 `stock.vo.concept`） |
| `ConceptSnapshotVO` | `market.vo.ConceptSnapshotVO` | `concept.vo.ConceptSnapshotVO` | 同上 |
| `PoolMembershipVO` | `market.vo.PoolMembershipVO` | `concept.vo.PoolMembershipVO` | **两边的都删除**（§3.4） |

> 📌 `StockInfoMapper` 内嵌类 `ConceptBriefRow`（`market.mapper.StockInfoMapper.ConceptBriefRow`）与 `ConceptMapper.ConceptMemberRow` 也是内嵌 Row，需一并检查命名。

### 7.2 `StockBriefVO` 的归属

`StockBriefVO` 被 `analysis`（池成员列表）依赖 → **必须留在 `stock` 的公共 vo 包**（`com.attribution.stock.vo.StockBriefVO`），不能放 `stock.vo.stock` 深子包（虽然 Java 允许，但会让 `analysis` 依赖路径别扭）。

### 7.3 `@DS` 依赖落位

`dynamic-datasource-spring-boot3-starter` **必须**在 `attribution-stock` 的 pom 里（`@DS` 注解在 stock 的 Mapper 上）。`attribution-analysis` 不需要。

### 7.4 `CollectProxyController` 的最终归属（待决）

| 选项 | 优点 | 缺点 |
|---|---|---|
| **A. 放 `attribution-analysis`** | 不新增模块 | 语义上"采集代理"不属于"分析" |
| **B. 放 `attribution-app`** | app 是装配层，代理本就是"对外门面" | app 里出现业务逻辑，违反「app 只放 3 样」约定 |
| **C. 新建 `attribution-collect-proxy`** | 语义最准 | 多一个模块（7 个） |

> 🗓️ **本 Step 先放 `attribution-analysis`**（选项 A，零新增模块），后续 Step 再评估是否独立。

### 7.5 `analysis` 的 `owner_id` 隔离（后续 Step）

`stock_pools.owner_id` 现存未用 → 池是全局的。监控/预警一旦上线，**必须**先做 owner 隔离，否则 A 用户能收到 B 用户池的预警。本 Step 不做。

---

## 8. 风险登记表

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| R1 | **Maven 循环依赖**（`stock ↔ analysis`） | 构建失败 | §3.4 删除 `with_pools`，`analysis → stock` 单向 |
| R2 | **XML namespace 未同步** | 启动报 `Invalid bound statement` | §6 步 4 专项验证 |
| R3 | **29 个 `@DS("raw")` 迁移时漏标** | `strict: true` 下启动即报错（好事） | 迁移后逐个 grep 核对数量 = 29 |
| R4 | **`dynamic-datasource` 依赖没跟着走** | 编译期找不到 `@DS` 类 | §7.3 |
| R5 | **3 组同名 VO 编译冲突** | 编译失败 | §7.1 分子包 |
| R6 | **`with_pools` 移除后前端报错** | 列表页池标签丢失 | §6 步 9 前端同步改 |
| R7 | **`StockBriefVO` 放错包** | `analysis` 依赖路径别扭 / 循环 | §7.2 |
| R8 | **大范围包名替换遗漏 import** | 编译失败 | 用 IDE 全局替换 + 编译迭代 |
| R9 | **`collect_logs` 归属未定** | 采集日志无处安放 | §3.1 暂放 `analysis`，后续独立 |
| R10 | **重构与双数据源/其他开发并行冲突** | 合并冲突 | 本 Step 单独分支，独占 `backend-java` |

---

## 9. 不在本次范围

| 项 | 理由 |
|---|---|
| 池的 per-user 隔离（`owner_id`） | 涉及数据迁移 + 全量查询加过滤，单独 Step |
| 监控/预警/归因**功能实现** | 本 Step 只出模块骨架与表设计，功能另开 Step |
| 表结构变更（新建 `monitor_rules` 等） | 本 Step 不建表（§4.3 仅登记设计） |
| `with_pools` 的前端替代方案最终选型 | §3.4 已给推荐，但前端实现细节另议 |
| `fundamental_index_daily` / `fundamental_stock_concept` 的处置（无 Mapper） | 与模块重划无关，另开整理 Step |
| `collect_logs_legacy_20261029` 表 drop | 单独 SQL 变更 |
| `attribution-scheduler` 相关 | 已下线，不涉及 |

---

## 10. 文档与代码同步清单

| 文件 | 改动 |
|---|---|
| `docs/工程索引.md` | §3 模块地图、§7.2 表映射、§9 速查表全部更新 |
| `docs/规范文档/拆分方案.md` | §2.1 parent pom、§3.2~3.4 模块归属、§5 依赖规则 更新 |
| `docs/规范文档/多库分工与数据源规范.md` | §2.2 Mapper 清单（模块名变更） |
| `docs/规范文档/纵向分层规范/Mapper层规范.md` | §2 `@MapperScan` 包名示例 |
| `docs/规范文档/横切技术规范/基础设施规范.md` | 如涉及模块清单 |
| `docs/开发文档/采集模块/采集模块现状文档*.md` | 采集代理归属（`market` → `analysis`） |

---

## 附录 A：目标目录结构（最终形态）

```text
backend-java/
├─ pom.xml
├─ attribution-common/
│  └─ com/attribution/common/{config,exception,mybatis,response}/
├─ attribution-collector-client/
│  └─ com/attribution/collector/client/{CollectorClient,CollectorService,CollectorFallback,CollectorCatalogCache,CollectRequest}
├─ attribution-auth/                              ← 不变
│  └─ com/attribution/auth/{controller,converter,dto,entity,mapper,service,vo}
├─ attribution-stock/                             ← 原 market + concept
│  └─ com/attribution/stock/
│     ├─ controller/
│     │  ├─ stock/     StockController, KlineController, MinuteKlineController,
│     │  │             PanelController, StockAnalysisController
│     │  ├─ concept/   ConceptQueryController, ConceptBoardController, ConceptQuoteController
│     │  └─ board/     DataBoardController
│     ├─ service/
│     │  ├─ stock/     StockInfoService, KlineService, DataBoardService
│     │  └─ concept/   ConceptService
│     ├─ service/impl/{stock,concept}/
│     ├─ mapper/
│     │  ├─ stock/     25 个采集表 Mapper（@DS("raw")）
│     │  └─ concept/   4 个采集表 Mapper（@DS("raw")）
│     ├─ mapper/row/
│     ├─ entity/{stock,concept}/
│     ├─ dto/{stock,concept,board}/
│     ├─ vo/{stock,concept,board}/
│     ├─ converter/{stock,concept}/
│     └─ util/IndicatorUtil
│  └─ resources/mapper/{stock,concept}/
├─ attribution-analysis/                          ← 原 user + 新增子域
│  └─ com/attribution/analysis/
│     ├─ controller/{pool,monitor,alert,attribution}/
│     ├─ service/{pool,monitor,alert,attribution}/
│     ├─ service/impl/{pool,monitor,alert,attribution}/
│     ├─ mapper/{pool,monitor,alert,attribution}/
│     ├─ entity/{pool,monitor,alert,attribution}/
│     ├─ dto/{pool,monitor,alert,attribution}/
│     ├─ vo/{pool,monitor,alert,attribution}/
│     ├─ converter/pool/
│     └─ config/PoolTaskExecutorConfig
│  └─ resources/mapper/pool/
├─ attribution-app/
│  ├─ src/main/java/com/attribution/AttributionApp.java
│  ├─ src/main/java/com/attribution/app/config/MybatisPlusConfig.java
│  └─ src/main/resources/application.yml
└─ docs/
```

## 附录 B：代码量对比

| 模块 | 现状（文件 / 行） | 目标（预估） |
|---|---|---|
| `attribution-common` | 6 / 224 | 不变 |
| `attribution-collector-client` | 5 / 338 | 不变 |
| `attribution-auth` | 38 / 1105 | 不变 |
| `attribution-market` | 133 / 4744 | — |
| `attribution-concept` | 39 / 1590 | — |
| **→ `attribution-stock`** | — | **~168 / ~6100**（减 2 Mapper + 2 Row + 2 XML ≈ 166 / ~6050） |
| `attribution-user` | 25 / 1059 | — |
| **→ `attribution-analysis`** | — | **~25 / ~1059**（Step 1）+ 新增子域（后续） |
| `attribution-app` | 2 / 47 | 不变 |

## 附录 C：URL 契约对照（Step 1 前后完全不变）

| 前缀 | 归属（前后一致） |
|---|---|
| `/api/auth/**`、`/api/v1/auth/**`、`/api/users/**`、`/api/roles/**`、`/api/permissions/**` | `auth` |
| `/api/stocks/**`、`/api/klines/**`、`/api/minute-klines/**`、`/api/stock-panel/**`、`/api/data-board/**`、`/api/concepts/**` | `market+concept` → `stock` |
| `/api/pools/**`、`/api/operations/**` | `user` → `analysis` |
| `/api/collect/**` | `market` → `analysis`（暂定，§7.4） |

> ✅ **前端零改动**（唯一例外：`with_pools` 移除导致的响应体字段变化，§3.4）。

# 股票信息模块开发文档（Step 1 · 双数据源落地 + 表名对齐）

> **状态**：🔴 **待实施** —— 本文档是**改造方案**，代码**尚未修改**，供检查确认后再动手。
>
> **适用范围**：`backend-java`（全部 7 个 Maven 模块）。
>
> **依据文档**：
> - [`../../规范文档/多库分工与数据源规范.md`](../../规范文档/多库分工与数据源规范.md) —— 双库 / 双数据源 / `@DS` 落地方案（本文的**主依据**）
> - [`../../规范文档/纵向分层规范/Mapper层规范.md`](../../规范文档/纵向分层规范/Mapper层规范.md) —— Mapper / XML / Row 规范
> - [`../../规范文档/纵向分层规范/POJO规范.md`](../../规范文档/纵向分层规范/POJO规范.md) —— PO / VO 字段类型规范
> - [`../../规范文档/横切技术规范/基础设施规范.md`](../../规范文档/横切技术规范/基础设施规范.md) —— 连接池 / 配置管理规范
> - [`../../工程索引.md`](../../工程索引.md) —— 模块地图 / 依赖方向 / 现状清单
> - [`../raw_data-2026-10-30_180351-dump.sql`](../raw_data-2026-10-30_180351-dump.sql) / [`../attribution-2026-10-30_180347-dump.sql`](../attribution-2026-10-30_180347-dump.sql) —— **远端数据库权威结构**（2026-10-30 18:03 导出）
>
> **触发问题**：前端「股票信息」页（`frontend/src/views/stock-info`）列表与筛选下拉全部 500，错误为
> `relation "fundamental_stock_basic" does not exist`。

---

## 0. 一句话结论

> **代码把「表名」这一层改对了（38 个 PO 的 `@TableName` 与 raw_data dump 逐张核对无误），但「数据源路由」这一层整个没做** —— 没有 `dynamic-datasource` 依赖、没有双数据源配置、29 个采集表 Mapper 一个 `@DS("raw")` 都没标，于是所有采集表 SQL 全部打到 `attribution` 库 → 「表不存在」。
>
> 本轮落地：**① 双数据源 + `@DS("raw")`（29 个 Mapper）② 拆分 2 个跨库 Mapper ③ 修正 4 个 XML 里的旧表名 ④ 修正 6 处 PO 字段类型错配**。
> **不动数据库**（表名 / 列名已经对齐，不需要 RENAME，不需要迁移脚本）。

---

## 1. 现状盘点

### 1.1 两库实际结构（2026-10-30 dump）

| 库 | 表 |
|---|---|
| `attribution`（业务库） | `collect_logs` · `collect_logs_legacy_20261029` · `pool_operations` · `stock_pool_members` · `stock_pools` · `sys_users` · `sys_roles` · `sys_permissions` · `sys_role_permissions` · `sys_user_roles` |
| `raw_data`（采集库） | `capital_*` 9 张 · `fundamental_*` 15 张 · `tech_*` 5 张 · `news_article` · `fundamental_stock_concept` |

> **业务库里一张采集表都没有** —— 这就是本次 500 的直接原因。

### 1.2 🔴 三层落地状态总览

| 层 | 规范要求 | 实际 | 判定 |
|---|---|---|---|
| **① 依赖** | root pom `dependencyManagement` + app pom 引入 `dynamic-datasource-spring-boot3-starter` | 两个 pom 里 `dynamic` **零命中** | 🔴 未做 |
| **② 配置** | `application.yml` 配 `spring.datasource.dynamic`（`biz` / `raw`）+ `strict: true` | 仍是单条 `spring.datasource.url` 指向 `attribution` | 🔴 未做 |
| **③ 路由** | 29 个采集表 Mapper 标 `@DS("raw")` | 全仓库 `@DS(` **零命中**（只在 md 文档里出现） | 🔴 未做 |
| **④ 拆分** | 拆分 `StockInfoMapper` / `ConceptMemberMapper` 两个混合库 Mapper | 仍混着跨库方法 | 🔴 未做 |
| **⑤ 表名** | 38 个 PO 的 `@TableName` 与真实表一致 | ✅ **全部一致**（本次逐张核对，见 §1.3） | 🟢 已完成 |

> 📌 **一句话**：规范 §3 的四步（依赖 → 配置 → `@DS` → 拆分）**一步都没走**，只有「表名对齐」那一步被提前做完了。
> 结果是：表名改对了，数据源还指错地方 → 报错从「表名不对」变成了「表在另一个库」，**症状变了但问题没解决**。

### 1.3 ✅ PO `@TableName` 全量核对结果（38 个，与 dump 逐张比对）

| 模块 | PO | `@TableName` | raw_data 实际 | 判定 |
|---|---|---|---|---|
| market | `StockInfoPO` | `fundamental_stock_basic` | `fundamental_stock_basic` | ✅ |
| market | `TechKlinePO` | `tech_daily` | `tech_daily` | ✅ |
| market | `AdjFactorPO` | `tech_adj_factor` | `tech_adj_factor` | ✅ |
| market | `SuspendPO` | `tech_suspend_d` | `tech_suspend_d` | ✅ |
| market | `NameChangePO` | `tech_namechange` | `tech_namechange` | ✅ |
| market | `CalendarPO` | `tech_trade_cal` | `tech_trade_cal` | ✅ |
| market | `MoneyflowPO` | `capital_moneyflow` | `capital_moneyflow` | ✅ |
| market | `MoneyflowHsgtPO` | `capital_moneyflow_hsgt` | `capital_moneyflow_hsgt` | ✅ |
| market | `MarginPO` | `capital_margin` | `capital_margin` | ✅ |
| market | `MarginDetailPO` | `capital_margin_detail` | `capital_margin_detail` | ✅ |
| market | `TopListPO` | `capital_top_list` | `capital_top_list` | ✅ |
| market | `TopInstPO` | `capital_top_inst` | `capital_top_inst` | ✅ |
| market | `BlockTradePO` | `capital_block_trade` | `capital_block_trade` | ✅ |
| market | `HsgtTop10PO` | `capital_hsgt_top10` | `capital_hsgt_top10` | ✅ |
| market | `LimitListPO` | `capital_limit_list_d` | `capital_limit_list_d` | ✅ |
| market | `HolderNumPO` | `capital_stk_holdernumber` | `capital_stk_holdernumber` | ✅ |
| market | `DailyBasicPO` | `fundamental_daily_basic` | `fundamental_daily_basic` | ✅ |
| market | `FinReportPO` | `fundamental_income` | `fundamental_income` | ✅ |
| market | `DividendPO` | `fundamental_dividend` | `fundamental_dividend` | ✅ |
| market | `Top10HolderPO` | `fundamental_top10_holders` | `fundamental_top10_holders` | ✅ |
| market | `Top10FloatPO` | `fundamental_top10_floatholders` | `fundamental_top10_floatholders` | ✅ |
| market | `IndexMemberPO` | `fundamental_index_member` | `fundamental_index_member` | ✅ |
| market | `MarketDailyPO` | `fundamental_market_daily` | `fundamental_market_daily` | ✅ |
| market | `SectorDailyPO` | `fundamental_sector_daily` | `fundamental_sector_daily` | ✅ |
| market | `NewsPO` | `news_article` | `news_article` | ✅ |
| market | `CollectLogPO` | `collect_logs` | `collect_logs`（attribution 库） | ✅ |
| concept | `ConceptPO` | `fundamental_concept` | `fundamental_concept` | ✅ |
| concept | `ConceptMemberPO` | `fundamental_concept_member` | `fundamental_concept_member` | ✅ |
| concept | `ConceptIndexPO` | `fundamental_concept_index` | `fundamental_concept_index` | ✅ |
| concept | `ConceptSnapshotPO` | `fundamental_concept_snapshot` | `fundamental_concept_snapshot` | ✅ |
| user | `StockPoolPO` | `stock_pools` | `stock_pools`（attribution 库） | ✅ |
| user | `PoolMemberPO` | `stock_pool_members` | `stock_pool_members`（attribution 库） | ✅ |
| user | `PoolOperationPO` | `pool_operations` | `pool_operations`（attribution 库） | ✅ |
| auth | `UserPO` | `sys_users` | `sys_users`（attribution 库） | ✅ |
| auth | `UserRolePO` | `sys_user_roles` | `sys_user_roles`（attribution 库） | ✅ |
| auth | `RolePO` | `sys_roles` | `sys_roles`（attribution 库） | ✅ |
| auth | `RolePermissionPO` | `sys_role_permissions` | `sys_role_permissions`（attribution 库） | ✅ |
| auth | `PermissionPO` | `sys_permissions` | `sys_permissions`（attribution 库） | ✅ |

> ✅ **结论**：PO 层无需任何表名修改。**问题 100% 在数据源路由层。**

### 1.4 🔴 混合库 Mapper（违反「一个 Mapper = 一个库」）

| Mapper | Base 表（库） | 违规方法 | 方法实际访问的库 |
|---|---|---|---|
| `StockInfoMapper`（market） | `fundamental_stock_basic`（**raw**） | `selectPoolMemberships` / `selectPoolMembershipsBySymbol` | **attribution**（`stock_pool_members` + `stock_pools`） |
| `ConceptMemberMapper`（concept） | `fundamental_concept_member`（**raw**） | `selectPoolMemberships` | **attribution**（`stock_pool_members` + `stock_pools`） |

> ⚠️ `@DS` 是**接口级**注解，一个接口无法同时指定两个数据源 → 必须拆。
> 拆完后 `StockInfoMapper` 全部方法都在 raw 库、`ConceptMemberMapper` 全部方法都在 raw 库，**不会再有跨库 SQL**。

### 1.5 🔴 XML 里的旧表名（与真实表不一致，7 处）

| 文件 | 行 | 当前 SQL | raw_data 实际表名 |
|---|---|---|---|
| `StockInfoMapper.xml` | 70 | `FROM tech_kline_daily` | `tech_daily` |
| `StockInfoMapper.xml` | 75 | `FROM tech_kline_daily` | `tech_daily` |
| `StockInfoMapper.xml` | 80 | `FROM tech_kline_daily` | `tech_daily` |
| `StockInfoMapper.xml` | 94 | `FROM tech_kline_daily` | `tech_daily` |
| `StockInfoMapper.xml` | 115 | `FROM fundamental_report r` | `fundamental_income` |
| `StockInfoMapper.xml` | 117 | `FROM fundamental_report` | `fundamental_income` |
| `ConceptMapper.xml` | 54 | `LEFT JOIN fundamental_stock_info s` | `fundamental_stock_basic` |

> 📌 这些错误**现在被同一个症状盖住了**（连错库 → 表不存在）。配好数据源后会以同样的 `relation does not exist` 冒出来，**必须同批修**。

### 1.6 🔴 PO 字段类型错配（配好数据源后必炸）

| PO / VO | 字段 | 当前类型 | 表实际类型 | 后果 |
|---|---|---|---|---|
| `SuspendPO` | `suspendTiming` | `LocalDate` | `varchar(32)` | 🔴 **查询直接 500**（PG 无法把 varchar 转 date） |
| `SuspendEventVO` | `suspendTiming` | `LocalDate` | （同上，透传 PO） | 🔴 同上 |
| `ConceptSnapshotPO` | `capturedAt` | `LocalDateTime` | `timestamptz` | 🔴 **查询直接 500**（PG 驱动拒绝 TIMESTAMPTZ → LocalDateTime） |
| `ConceptIndexPO` | `capturedAt` | `LocalDateTime` | `timestamptz` | 🔴 同上 |
| `NewsPO` | `sentiment` | `BigDecimal` | `varchar(16)` | 🟡 转换异常 |
| `NewsPO` | `symbols` | `String` | `varchar(10)[]`（数组） | 🟡 需 typeHandler 或改类型 |
| `NewsPO` | `id` | `Integer` | `bigint` | 🟡 溢出风险 |

> 📌 `CollectLogPO` 已经用对了（`OffsetDateTime` + `JacksonTypeHandler`），本次是**把同样的正确姿势补到其余两张表**。
> 参考 `docs/工程索引.md` §8.5「时间类型」：`collect_logs` 用 `OffsetDateTime`，`sys_users` 用 `LocalDateTime`，**别混改**。

### 1.7 🟡 死代码 / 缺失映射

| 项 | 情况 | 建议 |
|---|---|---|
| `StockInfoMapper.countKline` / `selectMinKlineDate` / `selectMaxKlineDate` | XML + 接口都有，但 **Service 层零调用**（已被 `selectStockStats` CTE 取代） | 🟡 删除（顺带解决 `Mapper层规范 §2.5`「日期类型转换应在 SQL 层完成」的遗留违规） |
| `StockInfoPO` 缺 `fullname` / `enname` / `cnspell` / `curr_type` | 表里有这 4 列，前端 `StockInfo` 类型也声明了 `enname` / `cnspell`，但后端没映射 → 前端永远拿不到 | 🟡 补 PO 字段 + VO 字段 |
| `Top10FloatPO` 缺 `hold_float_ratio` | 表里有该列，PO 无 | 🟢 补（不影响读，写时会漏） |
| `ConceptSnapshotPO` 缺 `p_change` / `trade_date` | 表里有这两列 | 🟢 补 |

### 1.8 🟡 Java 写采集表（违反双库铁律 3）

`StockController` 暴露了 3 个**写**接口，操作的是 `fundamental_stock_basic`（raw_data 库，Collector 独占写入）：

| 接口 | 方法 | 目标表 | 库 |
|---|---|---|---|
| `POST /api/stocks/` | `upsert` | `fundamental_stock_basic` | **raw_data** ❌ |
| `PATCH /api/stocks/{symbol}` | `patch` | `fundamental_stock_basic` | **raw_data** ❌ |
| `DELETE /api/stocks/{symbol}` | `delete` | `fundamental_stock_basic` | **raw_data** ❌ |

> 🔴 违反 `多库分工与数据源规范.md` §2.1 铁律 3「Java 不写任何采集数据」+ §5「Java 只读 raw_data」。
>
> ✅ **前端实际未使用这 3 个接口**：`StockInfoList.vue` 只调 `POST /stocks/sync`（触发 collector 采集）；
> `api.ts` 里的 `deleteStock` 定义了但无任何调用点。
>
> → **建议直接删除这 3 个接口**（见 §5.2 D-10），而不是给它们加 `@DS("raw")`。

---

## 2. 目标与非目标

### 2.1 目标

| # | 目标 | 验收标准 |
|---|---|---|
| G1 | **引入 `dynamic-datasource`**，配 `biz` / `raw` 双数据源 | `application.yml` 出现 `spring.datasource.dynamic`，两个 URL 分别指向 `attribution` / `raw_data` |
| G2 | **`strict: true` 开启** | 漏标 `@DS("raw")` 的 Mapper 首次调用报「can not find datasource」而不是静默连错库 |
| G3 | **29 个采集表 Mapper 标 `@DS("raw")`** | 全部查询打到 raw_data 库 |
| G4 | **拆分 2 个混合库 Mapper** | 无任何 Mapper 同时访问两个库 |
| G5 | **修正 7 处 XML 旧表名** | 4 个 XML 中所有表名 = dump 真实表名 |
| G6 | **修正 7 处 PO / VO 字段类型错配** | 时间列 `OffsetDateTime`、字符串列不声明为日期/数值 |
| G7 | **补齐 PO 缺失映射** | 前端 `enname` / `cnspell` 能拿到值 |
| G8 | **Java 不写采集表** | 删除 `POST /stocks/` `PATCH` `DELETE` 三个写接口 |
| G9 | **规范文档同步** | `工程索引.md` / `多库分工与数据源规范.md` / `基础设施规范.md` / `Mapper层规范.md` 的现状表与待办表同步更新 |

### 2.2 非目标（本期不做）

| # | 不做 | 理由 |
|---|---|---|
| N1 | **不改数据库**（不 RENAME、不 ALTER、不建库） | 表名 / 列名已完全对齐，无需任何迁移脚本 |
| N2 | 不改 `collector-python` | Collector 侧已全部改用 `raw_session_factory`，且 ORM 表名与 dump 一致 |
| N3 | 不改前端 | 前端接口契约未变；`enname` / `cnspell` 是**补齐**而非新增契约 |
| N4 | 不引入 `postgres_fdw` / `dblink` | 规范 §1.3 已明确否决 |
| N5 | 不做 `TableNameConsistencyTest` / `TableNameValidator` | 属 `工程索引.md` §11 待办 #4，独立任务；本期靠人工核对 + §7 验收脚本 |
| N6 | 不改 `PoolServiceImpl` 的 `user → market` 依赖 | 属规范 §3.4 选项 A 的解耦重构，与本次双库改造无关，独立任务 |

---

## 3. 方案设计

### 3.1 依赖落位

> ⚠️ **对规范 §3.1 的修正**：规范写的是「加到 `attribution-app/pom.xml`」——
> **这是错的**。`@DS` 注解（`com.baomidou.dynamic.datasource.annotation.DS`）要用在
> `attribution-market` / `attribution-concept` 的 Mapper 接口上，
> 而这两个模块**编译期看不到 app 的依赖**（依赖方向是 `app → market`），会直接编译失败。

**采纳方案：加到实际使用 `@DS` 的两个模块**（app 通过 `app → market/concept` 传递拿到 starter，Spring Boot 自动配置生效）：

```xml
<!-- backend-java/attribution-market/pom.xml -->
<dependency><groupId>com.baomidou</groupId><artifactId>dynamic-datasource-spring-boot3-starter</artifactId></dependency>

<!-- backend-java/attribution-concept/pom.xml -->
<dependency><groupId>com.baomidou</groupId><artifactId>dynamic-datasource-spring-boot3-starter</artifactId></dependency>
```

版本由 root pom 的 `dependencyManagement` 统一管理：

```xml
<!-- backend-java/pom.xml → <properties> -->
<dynamic-datasource.version>4.3.1</dynamic-datasource.version>

<!-- backend-java/pom.xml → <dependencyManagement> -->
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>dynamic-datasource-spring-boot3-starter</artifactId>
    <version>${dynamic-datasource.version}</version>
</dependency>
```

> 📌 **为什么不加到 `attribution-common`**：common 是「无业务依赖」的工具层
> （`ApiResponse` / `PageResult` / `TopN` / 异常 / `WebConfig`），给它挂 ORM starter 会破坏分层定位；
> 且 `user` / `auth` 的 Mapper **不需要** `@DS`（全是业务库表），加过去是无效依赖。

> 📌 **版本依据**：`4.3.1` 对应 Spring Boot 3.2.x（规范 §3.1 已核准该版本）。
> 落地时先跑 `mvn dependency:tree -pl attribution-app -am` 确认无冲突。

### 3.2 数据源配置

```yaml
# backend-java/attribution-app/src/main/resources/application.yml
spring:
  datasource:
    dynamic:
      primary: biz          # ★ 默认 = 业务库 attribution
      strict: true          # ★★ 漏标 @DS("raw") 立即报错，不静默连错库
      datasource:
        biz:
          url: ${SPRING_DATASOURCE_BIZ_URL:jdbc:postgresql://localhost:5432/attribution}
          username: ${DB_USERNAME:postgres}
          password: ${DB_PASSWORD:password}
          driver-class-name: org.postgresql.Driver
        raw:
          url: ${SPRING_DATASOURCE_RAW_URL:jdbc:postgresql://localhost:5432/raw_data}
          username: ${DB_USERNAME:postgres}
          password: ${DB_PASSWORD:password}
          driver-class-name: org.postgresql.Driver
      hikari:
        max-pool-size: 10
        minimum-idle: 2
        connection-timeout: 30000
        idle-timeout: 600000
        max-lifetime: 1800000
        leak-detection-threshold: 60000
```

> 🔴 **旧配置必须删除**：原 `spring.datasource.url` / `.username` / `.password` / `.hikari` 整段
> （`application.yml` 第 15–35 行）与 `dynamic` 段**冲突**，两者共存时 `dynamic-datasource`
> 行为不确定（规范 §3.2 已警示）。

**`.env` 键名调整**（`backend-java/.env` 与 `backend-java/.env.example` 同步）：

```diff
-SPRING_DATASOURCE_URL=jdbc:postgresql://8.148.204.54:5432/attribution
-SPRING_DATASOURCE_USERNAME=zhouch
-SPRING_DATASOURCE_PASSWORD=zhouchenhui
+DB_HOST=8.148.204.54
+DB_PORT=5432
+DB_USERNAME=zhouch
+DB_PASSWORD=zhouchenhui
+SPRING_DATASOURCE_BIZ_URL=jdbc:postgresql://8.148.204.54:5432/attribution
+SPRING_DATASOURCE_RAW_URL=jdbc:postgresql://8.148.204.54:5432/raw_data
```

> 📌 **命名统一**（规范 §3.10）：`SPRING_DATASOURCE_BIZ_URL` / `SPRING_DATASOURCE_RAW_URL` / `DB_USERNAME` / `DB_PASSWORD`。
> 两库**同 host 同 owner 同密码**，用户名密码只配一份（避免三处不一致 —— 这正是 `基础设施规范.md` §7.2 说的「同一语义只在一处配置」）。

> 📌 **`.env.example` 的 compose 场景**：`docker-compose.yml` 的 `postgres` 服务只建了 `attribution` 一个库
> （`POSTGRES_DB: ${POSTGRES_DB:-attribution}`），**没有 `raw_data`**。
> compose 部署前必须在 `postgres/initdb/01-init.sql` 增加 `CREATE DATABASE raw_data;`
> （规范 §4.8 已列此待办，列为本轮 **P1** 遗留项，见 §8）。

### 3.3 `@DS("raw")` 标注清单（29 个）

> 📌 规范 §3.4 规则 1：**标在 Mapper 接口上，不标 Service**（`@DS` 是接口级注解，标 Service 会因 AOP 代理织入顺序不确定而连错库）。

**market 模块 — 25 个**（除 `CollectLogMapper` 外全部）：

`StockInfoMapper` · `TechKlineMapper` · `AdjFactorMapper` · `SuspendMapper` · `NameChangeMapper` ·
`CalendarMapper` · `MoneyflowMapper` · `MoneyflowHsgtMapper` · `MarginMapper` · `MarginDetailMapper` ·
`TopListMapper` · `TopInstMapper` · `BlockTradeMapper` · `HsgtTop10Mapper` · `LimitListMapper` ·
`HolderNumMapper` · `DailyBasicMapper` · `FinReportMapper` · `DividendMapper` · `Top10HolderMapper` ·
`Top10FloatMapper` · `IndexMemberMapper` · `MarketDailyMapper` · `SectorDailyMapper` · `NewsMapper`

**concept 模块 — 4 个（全部）**：
`ConceptMapper` · `ConceptMemberMapper` · `ConceptIndexMapper` · `ConceptSnapshotMapper`

**不标（默认 `biz`）**：
market `CollectLogMapper`（`collect_logs` 在业务库）· user `StockPoolMapper` / `PoolMemberMapper` / `PoolOperationMapper` · auth `UserMapper` / `UserRoleMapper` / `RoleMapper` / `RolePermissionMapper` / `PermissionMapper`

```java
@Mapper
@DS("raw")
public interface TechKlineMapper extends BaseMapper<TechKlinePO> {}
```

### 3.4 拆分混合库 Mapper

#### 3.4.1 归属决策（关键分歧点，需确认）

规范 §3.4 给了两个选项，本项目**两个都走不通**，需要调整：

| 候选落位 | market 需要它 | concept 需要它 | 结论 |
|---|---|---|---|
| `attribution-user`（规范推荐语义归属） | ❌ `market → user` 与现有 `user → market` **循环依赖** → Maven 构建失败 | ❌ `concept → user` 可行 | ❌ 排除 |
| `attribution-market`（规范选项 B） | ✅ 零依赖 | ❌ 需 `concept → market`，**违反 `工程索引.md` §3 铁律 3**「禁止 concept 反向依赖 market」 | ⚠️ 只能给 market 用 |
| `attribution-common` | ❌ common 不该有 Mapper（规范 §3.4 明确） | ❌ 同 | ❌ 排除 |
| **各模块自建（本文采纳）** | ✅ market 内自建 | ✅ concept 内自建 | ✅ **无循环、无跨模块调 Mapper** |

**采纳：market 与 concept 各建一个自己的 `PoolMembershipQueryMapper`。**

- 两者都**不标 `@DS`** → 走默认 `biz` 库 → 查 `stock_pool_members` + `stock_pools`。
- 两者都在**自己模块内**被自己的 Service 调用 → 不违反「跨模块只调 Service 接口」铁律。
- 重复的是 2 个小 Mapper（各 2 个方法），换来的是**依赖方向零变化**、**Maven 构建零风险**。

> 📌 命名冲突规避：两个模块各自的 `com.attribution.{market,concept}.mapper.PoolMembershipQueryMapper`，
> 包名不同，**不存在冲突**。

#### 3.4.2 Row 独立成文件

规范 §2.4.1 / §5.2 要求 Row 独立成 `mapper/row/XxxRow.java`，**不要**写成 Mapper 接口内部类
（现有 `StockInfoMapper.PoolMembershipRow` / `ConceptMemberMapper.PoolMembershipRow` 违反此条）。
新建的两个 Mapper 按规范落地：

```
attribution-market/src/main/java/com/attribution/market/mapper/PoolMembershipQueryMapper.java
attribution-market/src/main/java/com/attribution/market/mapper/row/PoolMembershipRow.java
attribution-market/src/main/resources/mapper/PoolMembershipQueryMapper.xml

attribution-concept/src/main/java/com/attribution/concept/mapper/PoolMembershipQueryMapper.java
attribution-concept/src/main/java/com/attribution/concept/mapper/row/PoolMembershipRow.java
attribution-concept/src/main/resources/mapper/PoolMembershipQueryMapper.xml
```

> ⚠️ **`resultType` 必须写独立类的全限定名**（`...mapper.row.PoolMembershipRow`），
> 不是接口内部类的 `$` 写法。

#### 3.4.3 拆分后的调用点

| 调用点 | 现状 | 改后 |
|---|---|---|
| `StockInfoServiceImpl.poolMapBySymbol` | `stockInfoMapper.selectPoolMemberships(symbols)` | `poolMembershipQueryMapper.selectPoolMemberships(symbols)` |
| `ConceptServiceImpl.members` | `conceptMemberMapper.selectPoolMemberships(symbols)` | `poolMembershipQueryMapper.selectPoolMemberships(symbols)` |

> 📌 `StockInfoMapper.selectPoolMembershipsBySymbol` —— 全仓库**零调用**（只有接口 + XML 定义），
> 与 §1.7 的三个 K 线方法同属死代码，**一并删除**（不再迁到新 Mapper）。

#### 3.4.4 拆分后各 Mapper 的库归属

| Mapper | 库 | 涉及表 |
|---|---|---|
| `StockInfoMapper` | **raw** | `fundamental_stock_basic` · `fundamental_concept_member` · `fundamental_concept` · `fundamental_daily_basic` · `fundamental_income` · `tech_daily` |
| `ConceptMapper` | **raw** | `fundamental_concept` · `fundamental_concept_member` · `fundamental_stock_basic` · `fundamental_daily_basic` |
| `ConceptMemberMapper` | **raw** | `fundamental_concept_member` |
| `PoolMembershipQueryMapper`（market） | **biz** | `stock_pool_members` · `stock_pools` |
| `PoolMembershipQueryMapper`（concept） | **biz** | `stock_pool_members` · `stock_pools` |

> ✅ 拆分后**没有一个 Mapper 跨库**。

### 3.5 XML 表名修正

| 文件 | 修正 |
|---|---|
| `StockInfoMapper.xml` | `tech_kline_daily` → `tech_daily`（4 处）；`fundamental_report` → `fundamental_income`（2 处） |
| `ConceptMapper.xml` | `fundamental_stock_info` → `fundamental_stock_basic`（1 处） |
| `PoolMembershipQueryMapper.xml`（×2，新建） | 表名 `stock_pool_members` / `stock_pools` — 已是业务库真实表名，不改 |
| `PoolMemberMapper.xml` | 表名已正确，不改 |
| `ConceptMemberMapper.xml` | 迁出 `selectPoolMemberships` 后**文件变空 → 整个删除** |

> ⚠️ **`selectStockStats` CTE 里的 `latest_report` 改表名后需复核语义**：
> `fundamental_income` 的 `report_type='1'` = 合并报表、`end_date` = 报告期、`revenue` / `n_income` 均为 `double precision` ——
> 与原 `fundamental_report` 的列语义一致，**只改表名即可，SQL 逻辑不动**。

> ⚠️ **`tech_daily` 的日期列名是 `date`（不是 `trade_date`）** —— 现有 XML 用的就是 `date`，无需改。

### 3.6 PO / VO 字段类型修正

| 文件 | 字段 | 现状 | 改为 | 依据 |
|---|---|---|---|---|
| `SuspendPO` | `suspendTiming` | `LocalDate` | `String` | 表 `varchar(32)`；语义是「S=停牌 / R=复牌」**代码**，不是日期 |
| `SuspendEventVO` | `suspendTiming` | `LocalDate` | `String` | 透传 PO |
| `ConceptSnapshotPO` | `capturedAt` | `LocalDateTime` | `OffsetDateTime` | 表 `timestamptz` |
| `ConceptIndexPO` | `capturedAt` | `LocalDateTime` | `OffsetDateTime` | 表 `timestamptz` |
| `NewsPO` | `id` | `Integer` | `Long` | 表 `bigint` |
| `NewsPO` | `sentiment` | `BigDecimal` | `String` | 表 `varchar(16)` |
| `NewsPO` | `symbols` | `String` | `String` + `@TableField(typeHandler = …)` 或改 `List<String>` | 表 `varchar(10)[]` 数组 |

**同时补齐缺失字段**：

| PO | 补 | 依据 |
|---|---|---|
| `StockInfoPO` | `fullname` / `enname` / `cnspell` / `currType` | 表有这 4 列；前端 `StockInfo` 类型已声明 `enname` / `cnspell` |
| `StockInfoVO` | `enname` / `cnspell` | 与前端 `api.ts` 对齐（当前是「后端永远不返回、前端永远 undefined」的静默不一致） |
| `Top10FloatPO` | `holdFloatRatio` | 表 `hold_float_ratio` |
| `ConceptSnapshotPO` | `pChange` / `tradeDate` | 表 `p_change` / `trade_date` |

> ⚠️ **`NewsPO.symbols` 是 PG 数组列** —— MyBatis-Plus 的默认 `StringTypeHandler` 处理不了 `varchar[]`。
> 两个选项：
> - **选项 A（推荐，本期）**：`NewsMapper` 当前**全仓库零调用**（`grep` 只有接口自身）→
>   **本轮先不修 `symbols`**，只修 `id` / `sentiment`，并在 PO 上加 `@TableField(exist = false)` 显式排除 `symbols`，
>   避免将来有人一调就 500。
> - **选项 B（后续）**：引入 `ArrayTypeHandler` / 自定义 `TypeHandler` + `@TableName(autoResultMap = true)`。
>
> 📌 **本轮不做 `NewsMapper` 的数据接入** —— `news_article` 采集任务本身还卡在 tushare `news` 权限（见 `DataBoardServiceImpl.overview` 的 `newsVO.setMessage(...)`）。

### 3.7 Java 不写采集表（删除 3 个写接口）

| 待删 | 位置 | 理由 |
|---|---|---|
| `POST /api/stocks/`（`upsert`） | `StockController` + `StockInfoServiceImpl.upsert` | 写 `fundamental_stock_basic`（raw_data 库）→ 违反双库铁律 3；前端未使用 |
| `PATCH /api/stocks/{symbol}`（`patch`） | 同上 + `StockUpdateRequest` | 同上；前端未使用 |
| `DELETE /api/stocks/{symbol}`（`delete`） | 同上 | 同上；前端 `api.ts` 的 `deleteStock` 定义了但**无调用点** |

**保留**：`GET /api/stocks/meta` · `GET /api/stocks/{symbol}` · `POST /api/stocks/sync` · `POST /api/stocks/sync-daily-basic` · `GET /api/stocks/{symbol}/analysis`

> 📌 **同步清理**：`frontend/src/views/stock-info/api.ts` 中的 `deleteStock`（无调用点）可一并删除，避免留下调不通的死接口。
> 其余前端 API 不动。

> 🟡 **备选方案（如需保留人工维护股票信息的能力）**：把「Java 维护股票基础信息」改为写**业务库**的一张新表
> （如 `attribution.stock_profile_override`），再与 raw_data 侧在 Service 层内存 join。
> 这超出本轮范围，列为 §8 遗留项。

---

## 4. 文件改动清单

### 4.1 依赖与配置（6 个文件）

| # | 文件 | 改动 |
|---|---|---|
| D-01 | `backend-java/pom.xml` | `<properties>` 加 `dynamic-datasource.version=4.3.1`；`<dependencyManagement>` 加 `dynamic-datasource-spring-boot3-starter` |
| D-02 | `backend-java/attribution-market/pom.xml` | 加 `dynamic-datasource-spring-boot3-starter` 依赖 |
| D-03 | `backend-java/attribution-concept/pom.xml` | 加 `dynamic-datasource-spring-boot3-starter` 依赖 |
| D-04 | `backend-java/attribution-app/src/main/resources/application.yml` | 删 `spring.datasource.*` 整段；加 `spring.datasource.dynamic.*` |
| D-05 | `backend-java/.env` | `SPRING_DATASOURCE_URL/USERNAME/PASSWORD` → `DB_HOST/DB_PORT/DB_USERNAME/DB_PASSWORD` + `SPRING_DATASOURCE_BIZ_URL` + `SPRING_DATASOURCE_RAW_URL` |
| D-06 | `backend-java/.env.example` | 同 D-05（compose 场景：`postgres` / `raw_data`） |

### 4.2 新建（6 个文件）

| # | 文件 | 内容 |
|---|---|---|
| N-01 | `attribution-market/.../mapper/PoolMembershipQueryMapper.java` | 不标 `@DS`；`selectPoolMemberships(List<String>)` |
| N-02 | `attribution-market/.../mapper/row/PoolMembershipRow.java` | 独立 Row（`symbol` / `poolId` / `name` / `poolType`） |
| N-03 | `attribution-market/src/main/resources/mapper/PoolMembershipQueryMapper.xml` | 迁自 `StockInfoMapper.xml` 的两个 select |
| N-04 | `attribution-concept/.../mapper/PoolMembershipQueryMapper.java` | 同 N-01 |
| N-05 | `attribution-concept/.../mapper/row/PoolMembershipRow.java` | 同 N-02 |
| N-06 | `attribution-concept/src/main/resources/mapper/PoolMembershipQueryMapper.xml` | 迁自 `ConceptMemberMapper.xml` |

### 4.3 修改 — Mapper 接口（33 个文件）

| # | 文件 | 改动 |
|---|---|---|
| M-01 ~ M-25 | market 25 个 Mapper 接口 | 加 `@DS("raw")` + import `com.baomidou.dynamic.datasource.annotation.DS` |
| M-26 ~ M-29 | concept 4 个 Mapper 接口 | 同上 |
| M-30 | `attribution-market/.../mapper/StockInfoMapper.java` | 加 `@DS("raw")`；删 `selectPoolMemberships` / `selectPoolMembershipsBySymbol`；删 `countKline` / `selectMinKlineDate` / `selectMaxKlineDate`（死代码）；删内部类 `PoolMembershipRow` |
| M-31 | `attribution-concept/.../mapper/ConceptMemberMapper.java` | 加 `@DS("raw")`；删 `selectPoolMemberships`；删内部类 `PoolMembershipRow` |
| M-32 | `attribution-market/.../mapper/StockInfoMapper.java` | （同上，M-30 与 M-32 合并计一处） |
| M-33 | `attribution-market/.../entity/StockInfoPO.java` | 补 4 个字段 |

### 4.4 修改 — XML（3 个文件 + 1 个删除）

| # | 文件 | 改动 |
|---|---|---|
| X-01 | `attribution-market/src/main/resources/mapper/StockInfoMapper.xml` | 删 2 个池 select + 3 个 K 线 select；改 6 处表名 |
| X-02 | `attribution-concept/src/main/resources/mapper/ConceptMapper.xml` | 改 1 处表名 |
| X-03 | `attribution-concept/src/main/resources/mapper/ConceptMemberMapper.xml` | **删除文件**（迁空） |
| X-04 | `attribution-user/src/main/resources/mapper/PoolMemberMapper.xml` | 不改 |

### 4.5 修改 — Service / Controller（5 个文件）

| # | 文件 | 改动 |
|---|---|---|
| S-01 | `attribution-market/.../service/impl/StockInfoServiceImpl.java` | 注入 `PoolMembershipQueryMapper`；`poolMapBySymbol` 改调新 Mapper；删 `upsert` / `patch` / `delete` 三个方法 |
| S-02 | `attribution-concept/.../service/impl/ConceptServiceImpl.java` | 注入 `PoolMembershipQueryMapper`；`members` 改调新 Mapper |
| S-03 | `attribution-market/.../controller/StockController.java` | 删 `POST /`、`PATCH /{symbol}`、`DELETE /{symbol}` 三个端点 |
| S-04 | `attribution-market/.../service/StockInfoService.java` | 同步删 3 个方法签名 |
| S-05 | `attribution-market/.../dto/StockUpdateRequest.java` | **删除**（随 `patch` 一起失效） |

### 4.6 修改 — PO / VO（6 个文件）

| # | 文件 | 改动 |
|---|---|---|
| P-01 | `attribution-market/.../entity/SuspendPO.java` | `suspendTiming` → `String` |
| P-02 | `attribution-market/.../vo/SuspendEventVO.java` | `suspendTiming` → `String` |
| P-03 | `attribution-concept/.../entity/ConceptSnapshotPO.java` | `capturedAt` → `OffsetDateTime`；补 `pChange` / `tradeDate` |
| P-04 | `attribution-concept/.../entity/ConceptIndexPO.java` | `capturedAt` → `OffsetDateTime` |
| P-05 | `attribution-market/.../entity/NewsPO.java` | `id` → `Long`；`sentiment` → `String`；`symbols` 加 `@TableField(exist = false)` |
| P-06 | `attribution-market/.../entity/Top10FloatPO.java` | 补 `holdFloatRatio` |
| P-07 | `attribution-market/.../vo/StockInfoVO.java` | 补 `enname` / `cnspell` |
| P-08 | `attribution-market/.../converter/MarketConverter.java` | `toStockInfoVO` 补 `enname` / `cnspell` 映射 |

### 4.7 修改 — 前端（1 个文件）

| # | 文件 | 改动 |
|---|---|---|
| F-01 | `frontend/src/views/stock-info/api.ts` | 删 `deleteStock`（无调用点）；`StockInfo` 类型已含 `enname` / `cnspell`，**不改** |

### 4.8 文档同步（4 个文件，实施完成后）

| # | 文件 | 同步内容 |
|---|---|---|
| DOC-01 | `docs/工程索引.md` | §4 配置表「当前是单数据源」→ 双数据源；§7.1 去掉「🔴 尚未落地」；§7.2 表补「库」列；§11 待办 #1/#2 标记完成 |
| DOC-02 | `docs/规范文档/多库分工与数据源规范.md` | §7.3 待办表 1~7 项标记完成；§3.1 依赖落位修正为「加到 market + concept」（见 §3.1 说明） |
| DOC-03 | `docs/规范文档/横切技术规范/基础设施规范.md` | §9「数据库」行 `spring.datasource.url` → `spring.datasource.dynamic.*`；§2.2 补双池参数说明 |
| DOC-04 | `docs/规范文档/纵向分层规范/Mapper层规范.md` | §8 技术前提「数据库」行同步；§2.1 补「Mapper 需标 `@DS("raw")`（采集表）」规则 |

---

## 5. 实施顺序

```
① pom 依赖（D-01 ~ D-03）              → mvn compile 通过
② application.yml + .env（D-04 ~ D-06） → 启动不报错，两个数据源就位
③ 29 个 Mapper 标 @DS("raw")（M-01 ~ M-29）→ strict:true 下暴露漏标
④ 拆分混合库 Mapper（N-01 ~ N-06 + M-30/M-31 + X-01/X-03 + S-01/S-02）→ 无跨库 Mapper
⑤ XML 旧表名修正（X-01/X-02）            → 所有 SQL 表名 = dump 真实表名
⑥ PO / VO 类型修正（P-01 ~ P-08）          → 消除 varchar→date / timestamptz 转换 500
⑦ 删除 Java 写采集表的 3 个接口（S-03 ~ S-05 + F-01）
⑧ mvn package + 启动 + 接口验收（§7）
⑨ 文档同步（DOC-01 ~ DOC-04）
```

> ⚠️ **② 之后、③ 之前**：此时 `StockInfoMapper` 还混着业务库方法但已标 `@DS("raw")` →
> `selectPoolMemberships` 会打到 raw_data 库 → 报 `relation "stock_pool_members" does not exist`。
> 这是**预期中间态**，第 ④ 步会解决。**不要因为这个报错就回头去关 `strict`。**

---

## 6. 风险与红线

| # | 风险 | 等级 | 应对 |
|---|---|---|---|
| R1 | **漏标 `@DS("raw")`** | 高 | `strict: true` → 立即报「can not find datasource」，指向根因。第 ③ 步单独提交、单独验证 |
| R2 | **误标 `@DS("raw")` 到业务库 Mapper** | 高 | `user` / `auth` / `CollectLogMapper` 一律不标；Code Review 逐个核对 §3.3 清单 |
| R3 | **标 `@DS` 在 Service 上** | 高 | 全部标在 Mapper 接口（规范 §3.4 规则 1） |
| R4 | **两个连接池，总连接数翻倍** | 中 | `biz` / `raw` 各 `max-pool-size: 10`，合计 20 ≤ DB `max_connections`；compose 的 postgres `memory: 512M` 需确认 `max_connections` 默认 100 足够 |
| R5 | **远端 PG 空闲断连**（`8.148.204.54` 是公网地址） | 中 | `pool_pre_ping: true`（dynamic-datasource 默认开启，需在 `application.yml` 显式确认）+ `max-lifetime: 1800000` |
| R6 | **compose 部署缺 `raw_data` 库** | 中 | `postgres/initdb/01-init.sql` 补 `CREATE DATABASE raw_data;`（P1 遗留项，见 §8） |
| R7 | **`@DS` + `@Transactional` 组合** | 低 | 本项目 Java **只读 raw_data**（§3.7 删掉写接口后），**不存在跨库事务**；且跨库场景下 `@DS` 是方法级切换、事务开始时已锁定 —— 一旦将来要写 raw_data，必须拆成两个独立事务 |
| R8 | **删掉 3 个写接口可能影响外部调用方** | 低 | 前端已确认零调用；`grep` 全仓库确认无其他调用点 |
| R9 | **`dynamic-datasource` 与 MyBatis-Plus 3.5.7 版本兼容** | 低 | 4.3.1 对应 Spring Boot 3.2.x（规范 §3.1 已核准）；`mvn dependency:tree` 确认 |
| R10 | **改 PO 字段类型影响前端** | 低 | `suspend_timing` 前端未消费；`captured_at` 前端只当字符串展示（`captured_at: string \| null`） |

### 红线（本轮**不做**）

| # | 红线 |
|---|---|
| X1 | ❌ 不为绕过报错而把 `strict` 关掉 |
| X2 | ❌ 不给业务库 Mapper（`user` / `auth` / `CollectLogMapper`）加 `@DS("raw")` |
| X3 | ❌ 不在 Service 层加 `@DS` |
| X4 | ❌ 不写跨库 JOIN 的 SQL（`stock_pool_members JOIN fundamental_stock_basic`） |
| X5 | ❌ 不新建 `postgres_fdw` 外表 |
| X6 | ❌ 不改数据库表名 / 列名（已对齐，无需迁移） |
| X7 | ❌ 不改 `collector-python` |

---

## 7. 验收标准

### 7.1 编译期

| # | 检查 | 命令 |
|---|---|---|
| A1 | 全部模块编译通过 | `mvn -pl attribution-app -am clean package` |
| A2 | 无 `@DS` 误标 | `grep -rn "@DS" --include=*.java` → 命中 29 个采集 Mapper |
| A3 | 无跨库 Mapper 残留 | `grep -rn "stock_pool" --include=*.xml` → 只出现在 `PoolMembershipQueryMapper.xml` ×2 + `PoolMemberMapper.xml` |
| A4 | XML 表名全部正确 | `grep -rn "tech_kline_daily\|fundamental_report\|fundamental_stock_info" --include=*.xml` → **零命中** |
| A5 | 死代码已清 | `grep -rn "countKline\|selectMinKlineDate\|selectMaxKlineDate\|selectPoolMembershipsBySymbol"` → 零命中 |

### 7.2 运行期接口验收

| # | 接口 | 期望 |
|---|---|---|
| B1 | `GET /api/stocks/meta` | 200，`data.industries` / `markets` / `exchanges` 非空（**这是本次 500 的直接验证点**） |
| B2 | `GET /api/stock-panel/?page=1&page_size=20&with_pools=true&with_concepts=true` | 200，`data.list` 非空，`items[].pools` / `items[].concepts` 已填充 |
| B3 | `GET /api/stocks/000001` | 200，返回 `fundamental_stock_basic` 单行 |
| B4 | `GET /api/stocks/000001/analysis` | 200，K 线与 17 个技术指标正常 |
| B5 | `GET /api/data-board/tech/kline/000001` | 200（覆盖 `tech_daily` + `tech_suspend_d`） |
| B6 | `GET /api/data-board/overview/000001` | 200（覆盖 `fundamental_daily_basic` / `capital_*`） |
| B7 | `GET /api/concepts/` | 200（覆盖 `fundamental_concept`） |
| B8 | `GET /api/concepts/concept-board/members?concept_id=1&with_pools=true` | 200（覆盖 concept 侧拆分后的池查询） |
| B9 | `GET /api/collect/logs` | 200（覆盖 `collect_logs` 走 biz 库） |
| B10 | `GET /api/pools` | 200（覆盖 `stock_pools` 走 biz 库） |

### 7.3 数据库校验脚本

```sql
-- ① 确认表在 raw_data，不在 attribution
SELECT table_schema, table_name FROM information_schema.tables
 WHERE table_name IN ('fundamental_stock_basic','tech_daily','fundamental_income')
 ORDER BY table_schema, table_name;
-- 期望：3 行，全部 table_schema = 'raw_data'

-- ② 确认业务库无采集表
SELECT count(*) FROM information_schema.tables
 WHERE table_schema='attribution' AND (table_name LIKE 'tech_%' OR table_name LIKE 'capital_%'
   OR table_name LIKE 'fundamental_%' OR table_name='news_article');
-- 期望：0

-- ③ 确认 fundamental_stock_basic 有数据（面板列表非空的前提）
SELECT count(*) FROM raw_data.fundamental_stock_basic;
-- 期望：> 0（历史快照为 5,576）

-- ④ 确认 tech_daily 有数据（K 线统计非空的前提）
SELECT count(*) FROM raw_data.tech_daily;
-- 期望：> 0（历史快照为 188,933）
```

### 7.4 前端验收

| # | 检查 |
|---|---|
| C1 | 「股票信息」页列表正常渲染，无 500 toast |
| C2 | 「行业 / 市场 / 交易所」三个下拉有选项 |
| C3 | 行内「所属池」标签正常显示（`with_pools=true`） |
| C4 | 展开行的概念标签正常显示（`with_concepts=true`） |
| C5 | 详情抽屉「数据看板」四个 Tab（技术 / 资金 / 基本面 / 新闻）不报错 |

---

## 8. 遗留项（不在本轮）

| # | 事项 | 优先级 | 说明 |
|---|---|---|---|
| L1 | `postgres/initdb/01-init.sql` 增加 `CREATE DATABASE raw_data;` | **P1** | compose 部署缺第二个库（规范 §4.8 已列） |
| L2 | `TableNameConsistencyTest` 单元测试 | P1 | `工程索引.md` §11 #4；断言每个 `@TableName` 在其 `@DS` 对应库存在 |
| L3 | `TableNameValidator` 启动自检（fail-fast） | P2 | `工程索引.md` §11 #4；规范 §5.1 ① |
| L4 | `PoolServiceImpl` 的 `user → market` 依赖解耦 | P2 | 规范 §3.4 选项 A；解耦后可把池查询 Mapper 统一放 `attribution-user` |
| L5 | `NewsPO.symbols` 数组列 typeHandler | P2 | `NewsMapper` 接入 `news_article` 时必须先解决 |
| L6 | 「Java 维护股票基础信息」的业务库覆写表 | P2 | §3.7 备选方案；需要人工编辑股票信息时再评估 |
| L7 | `PoolOperationPO.params` / `progress` 的 `json` 列 | P3 | 表类型是 `json`，PO 用 `String` —— PG 驱动能返回字符串，**当前可跑**；但建议改 `JacksonTypeHandler` + `Map`（与 `CollectLogPO` 一致） |
| L8 | `PoolServiceImpl` 仍用 `strategy="condition"` | P3 | 已被 `normalizeStrategy` 兼容（`工程索引.md` §11 #5） |

---

## 9. 需要确认的三个点

| # | 问题 | 我的建议 |
|---|---|---|
| Q1 | **混合库 Mapper 的落位**：规范 §3.4 推荐放 `attribution-user`，但那会造成 `market → user` 循环依赖。本文改为「market / concept 各建一个 `PoolMembershipQueryMapper`」 | ✅ 采纳本文方案（依赖方向零变化，构建零风险） |
| Q2 | **删除 Java 写采集表的 3 个接口**（`POST /stocks/` `PATCH` `DELETE`）—— 前端确认零调用 | ✅ 采纳删除。如需保留「人工维护股票信息」，走 §8 L6 的业务库覆写表方案 |
| Q3 | **依赖落位**：规范 §3.1 说加到 `attribution-app/pom.xml`，但那样 market / concept 编译期拿不到 `@DS` 类 | ✅ 采纳本文方案：加到 `attribution-market` + `attribution-concept`，并同步修正规范 §3.1 |

---

## 10. 相关文档

| 文档 | 管什么 |
|---|---|
| [`../../规范文档/多库分工与数据源规范.md`](../../规范文档/多库分工与数据源规范.md) | 双库分工 / `@DS` 标注规则 / 混合库拆分 / 连接池 |
| [`../../规范文档/纵向分层规范/Mapper层规范.md`](../../规范文档/纵向分层规范/Mapper层规范.md) | XML 写法 / Row 定义 / 批量与聚合 / 分页 |
| [`../../规范文档/纵向分层规范/POJO规范.md`](../../规范文档/纵向分层规范/POJO规范.md) | PO / VO 字段类型定义 |
| [`../../规范文档/纵向分层规范/Service层规范.md`](../../规范文档/纵向分层规范/Service层规范.md) | Service 职责 / N+1 / 事务边界 |
| [`../../规范文档/横切技术规范/基础设施规范.md`](../../规范文档/横切技术规范/基础设施规范.md) | 连接池参数 / 配置管理 / 环境变量命名 |
| [`../../工程索引.md`](../../工程索引.md) | 模块地图 / 依赖方向 / 现状清单 / 待办 |
| [`../../开发文档/采集模块/step2/采集模块重构开发文档（元数据瘦身 + 数据库对齐）.md`](../../开发文档/采集模块/step2/采集模块重构开发文档（元数据瘦身 + 数据库对齐）.md) | 上一轮采集侧表名对齐（已完成，本文承续） |

---

> 📌 **本文档只写方案与现状快照，不含「已实施」的结论。**
> 实施完成后请：
> ① 把 §1 的现状快照改写为「实施前」并归档到 `docs/规范文档/审计与整改/`（带日期）；
> ② 同步 §4.8 的 4 份规范 / 索引文档；
> ③ 在本文顶部把状态改为 ✅ 并补「执行记录（日期 + 实际改动）」小节。

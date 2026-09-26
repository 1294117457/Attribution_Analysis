# 6 周迁移计划

## 一、总体节奏

```
Week 1 (Day 1-7)   ████████ 基础设施 + 项目脚手架
Week 2 (Day 8-14)  ████████ 数据模型 + Repository 层
Week 3 (Day 15-21) ████████ 核心服务（操作池 + K线查询）
Week 4 (Day 22-28) ████████ 数据采集流水线
Week 5 (Day 29-35) ████████ 归因分析 + 技术指标计算
Week 6 (Day 36-42) ████████ 集成测试 + 灰度切换 + 验收
```

## 二、详细计划

### Week 1：基础设施 + 项目脚手架

#### 目标
搭建 Java 21 + Spring Boot 3.3 项目结构，跑通"Hello World + DB 连接"。

#### Day 1-2：环境准备
- [ ] 验证 JDK 21 + Maven 3.9 配置（`java --version`, `mvn --version`）
- [ ] 创建 Git 分支 `feat/java-rewrite`
- [ ] 初始化 Maven 项目（`pom.xml` 见 06-deployment.md）
- [ ] 创建包结构（`com.attribution.{controller,service,domain,repository,adapter,config,exception}`）

#### Day 3-4：基础配置
- [ ] `application.yml` / `application-dev.yml` 配置
- [ ] Flyway 迁移脚本（V1__init_schema.sql）
- [ ] PostgreSQL 连接测试
- [ ] SpringDoc OpenAPI 配置
- [ ] 全局异常处理器

#### Day 5-6：通用组件
- [ ] `ApiResponse<T>` 统一响应格式
- [ ] 通用分页 VO（`PageResponse<T>`）
- [ ] Lombok 集成验证
- [ ] WebClient 配置

#### Day 7：里程碑验证
- [ ] **M1 验收**：`GET /api/health` 返回 200
- [ ] **M1 验收**：能连接 PostgreSQL 读取已存在的表
- [ ] **M1 验收**：Swagger UI 在 `/swagger-ui.html` 可访问

---

### Week 2：数据模型 + Repository 层

#### 目标
完成 **23 个 Entity** + **Repository 接口**，跑通批量生成流程。

#### Day 8-9：核心 Entity
- [ ] `TechKlineDailyEntity`（最复杂，28 字段）
- [ ] `StockPoolEntity`, `StockPoolMemberEntity`, `PoolOperationEntity`
- [ ] `StockInfoEntity`, `IndustryEntity`, `MarketEntity`
- [ ] `ConceptEntity`, `ConceptMemberEntity`

#### Day 10-11：批量生成 Entity
- [ ] 财务类（fin_report, fin_daily_basic, fin_top10_*）
- [ ] 资金类（cap_margin, cap_margin_detail, cap_top_list, cap_top_inst, cap_block_trade, cap_moneyflow, cap_holder_num）
- [ ] 基础类（base_adj_factor, base_dividend, base_suspend, base_name_change）
- [ ] 市场类（mkt_calendar, mkt_market_daily, mkt_sector_daily, mkt_index_member）

#### Day 12-13：值对象 + Repository
- [ ] 值对象：`StockCode`, `TradeDate`, `PoolType`
- [ ] Repository 接口：`JpaRepository<>` 自定义方法
- [ ] JSONB 转换器：`MapToJsonConverter`
- [ ] 审计配置：`@EnableJpaAuditing`

#### Day 14：里程碑验证
- [ ] **M2 验收**：所有 Entity 与数据库表结构 100% 对齐
- [ ] **M2 验收**：`mvn compile` 无错误
- [ ] **M2 验收**：能查询一条 K 线记录

---

### Week 3：核心服务（操作池 + K线查询）

#### 目标
完成 **StockPoolService** + **KlineService**，跑通操作池 CRUD + K线查询 API。

#### Day 15-16：DTO 层
- [ ] Pool 相关 DTO：`PoolCreateRequest`, `PoolVO`, `PoolMemberVO`
- [ ] Kline 相关 DTO：`KlineQueryRequest`, `KlineVO`, `KlineCollectVO`
- [ ] 通用响应：`ApiResponse<T>`

#### Day 17-18：Service 层 - StockPool
- [ ] `StockPoolService` 核心方法：
  - `createPool`, `listPools`, `getPool`, `updatePool`, `deletePool`
  - `addMembers`, `removeMembers`, `listMembers`, `updateMemberMemo`
  - `findPoolsBySymbol`
- [ ] 单元测试：每个方法至少 1 个 happy path 测试

#### Day 19-20：Service 层 - Kline
- [ ] `KlineService` 核心方法：
  - `getKlines`, `getKlineByDate`, `getStats`
  - `delete` (单条 + 全部)
- [ ] 单元测试 + 集成测试（TestContainers）

#### Day 21：里程碑验证
- [ ] **M3 验收**：操作池 CRUD E2E 通过
- [ ] **M3 验收**：K线查询 API E2E 通过
- [ ] **M3 验收**：API 响应格式与 Python 版本一致（字段名、嵌套结构）

---

### Week 4：数据采集流水线

#### 目标
完成 **Tushare 数据采集** + **池操作任务调度**，跑通批量采集。

#### Day 22-23：Tushare 采集器
- [ ] `TushareProperties` 配置类
- [ ] `TushareApiClient` HTTP 客户端
- [ ] `TushareResponse` / `TushareData` 响应模型
- [ ] `TushareCollector` 实现 `Collector` 接口

#### Day 24-25：采集策略
- [ ] 增量采集逻辑（计算 start_date）
- [ ] 批量写入（每 500 条一批）
- [ ] 重试机制（指数退避）
- [ ] 限流（RateLimiter）

#### Day 26-27：池操作服务
- [ ] `PoolOperationService`：
  - `createKlineCollectOperation`
  - `listOperations`, `getOperation`, `getOperationProgress`
  - `cancelOperation`
- [ ] Virtual Threads 并发执行
- [ ] 进度更新（每完成一只股票）

#### Day 28：里程碑验证
- [ ] **M4 验收**：单只股票 K 线采集成功
- [ ] **M4 验收**：池批量采集（100 只股票）成功
- [ ] **M4 验收**：采集进度实时更新
- [ ] **M4 验收**：Tushare 限流生效

---

### Week 5：归因分析 + 技术指标计算

#### 目标
完成 **StockAnalysisService** + **技术指标计算**，跑通归因分析 API。

#### Day 29-30：技术指标计算
- [ ] MA (5/10/20/60)、EMA (12/26)
- [ ] MACD (DIF/DEA/BAR)
- [ ] RSI (6/12/24)
- [ ] KDJ (K/D/J)
- [ ] BOLL (UP/MID/DN)

#### Day 31-32：技术形态检测
- [ ] `SignalDetector`：
  - MA 多头排列
  - 金叉/死叉
  - MACD 红/绿柱
  - RSI 超买/超卖
  - KDJ 顶/底背离
  - BOLL 突破/支撑

#### Day 33-34：归因分析服务
- [ ] `StockAnalysisService.build(symbol, days)`
- [ ] DTO：`StockAnalysisVO`, `TechnicalSummaryVO`, `KlineWithIndicatorVO`
- [ ] 单元测试：与 Python 版本输出对照

#### Day 35：里程碑验证
- [ ] **M5 验收**：股票分析 API 返回结果与 Python 版本一致
- [ ] **M5 验收**：技术指标计算误差 < 0.01%

---

### Week 6：集成测试 + 灰度切换 + 验收

#### 目标
E2E 测试覆盖 + 灰度上线 + 数据一致性验证。

#### Day 36-37：集成测试
- [ ] TestContainers PostgreSQL 集成测试
- [ ] API E2E 测试（MockMvc）
- [ ] 数据一致性测试（Python vs Java 同一查询结果对比）
- [ ] 性能基准测试（吞吐量、延迟）

#### Day 38-39：灰度部署
- [ ] Docker 镜像构建
- [ ] Nginx 反向代理配置（20% 流量切到 Java）
- [ ] 监控指标对比（响应时间、错误率、QPS）
- [ ] 日志告警设置

#### Day 40-41：全量切换
- [ ] 流量切到 100% Java
- [ ] Python 版本停机（保留 2 周用于回滚）
- [ ] 数据库索引重建（如有需要）
- [ ] 文档更新（部署手册、运维手册）

#### Day 42：项目收尾
- [ ] **M6 验收**：所有核心功能 Java 版本与 Python 版本行为一致
- [ ] **M6 验收**：7 天稳定性测试（线上无 P0 故障）
- [ ] **M6 验收**：文档完整（架构、API、部署）
- [ ] 代码 review + Git 合并到 main 分支

---

## 三、里程碑验收标准

| 里程碑 | 周 | 验收标准 |
|---|---|---|
| **M1** 基础设施 | Week 1 | Hello World + DB 连接 + Swagger |
| **M2** 数据模型 | Week 2 | 23 个 Entity + Repository 完整 |
| **M3** 核心服务 | Week 3 | 池 CRUD + K线查询 E2E 通过 |
| **M4** 数据采集 | Week 4 | 单只 + 批量采集成功 |
| **M5** 归因分析 | Week 5 | 技术指标误差 < 0.01% |
| **M6** 集成验收 | Week 6 | 7 天稳定 + 全量切换 |

## 四、风险与对策

### 4.1 高风险项

| 风险 | 影响 | 对策 |
|---|---|---|
| **Tushare API 兼容** | M4 可能延期 | 第 1 周就开始研究 Tushare API 文档；用 Mock 服务先做单元测试 |
| **Virtual Threads 行为差异** | 性能不达预期 | Week 1 跑一个简单的并发基准测试，提前发现问题 |
| **技术指标计算精度** | M5 数据不一致 | 用 Python 跑测试数据导出，Java 单元测试对比 |
| **数据库迁移** | 数据丢失 | Flyway 严格审查；保留 Python 版本 2 周用于回滚 |

### 4.2 中风险项

| 风险 | 影响 | 对策 |
|---|---|---|
| Lombok 团队不熟悉 | 编码效率低 | Week 1 提供 Lombok 速成文档 |
| Spring Data JPA 复杂查询 | M3 延期 | Week 2 先用 @Query JPQL 验证复杂查询可行性 |
| 现有数据库已有数据 | 迁移兼容性 | Flyway baseline-on-migrate = true |

### 4.3 低风险项

| 风险 | 影响 | 对策 |
|---|---|---|
| 前端联调 | 不影响 | API 字段保持与 Python 版本一致 |
| Docker 镜像构建 | 时间成本 | Week 6 前提前验证镜像构建流程 |

## 五、资源估算

### 5.1 人力

| 角色 | 周数 | 任务 |
|---|---|---|
| 后端开发（主） | 6 周全程 | 主体开发 |
| 后端开发（辅） | Week 4-6 | 数据采集 + 测试辅助 |
| DBA | Week 2 + Week 6 | Flyway 迁移审查 + 索引优化 |
| 测试 | Week 6 | E2E 测试 |

### 5.2 时间投入

| 阶段 | 工时（人天） |
|---|---|
| Week 1 基础设施 | 5 |
| Week 2 数据模型 | 7 |
| Week 3 核心服务 | 8 |
| Week 4 数据采集 | 10 |
| Week 5 归因分析 | 7 |
| Week 6 集成验收 | 8 |
| **总计** | **45 人天** |

## 六、停止条件

### 6.1 重构完成的标志

满足以下**全部**条件：

- [ ] 所有 26 个 API 端点实现
- [ ] 23 个 Entity + Repository 完整
- [ ] 数据采集（Tushare）E2E 通过
- [ ] 技术指标计算与 Python 版本一致
- [ ] 集成测试覆盖率 > 80%
- [ ] 线上 7 天无 P0 故障

### 6.2 不做（Scope Boundaries）

以下事项**不在**本次重构范围内：

- ❌ 前端重构（Vue/React）
- ❌ AI/RAG 功能
- ❌ 缓存层（Redis）
- ❌ 性能深度优化
- ❌ 100% Python 边界 case 覆盖

## 七、回滚计划

### 7.1 触发条件

- 灰度期间 Java 版本错误率 > 5%
- Java 版本响应时间 > Python 版本 2 倍
- 数据一致性测试发现不可修复的差异

### 7.2 回滚步骤

```bash
# 1. Nginx 流量切回 Python
vim /etc/nginx/conf.d/attribution.conf
# upstream 改为 python_backend

nginx -s reload

# 2. Java 服务停机（保留镜像用于回滚）
docker-compose stop app

# 3. 通知相关方
```

### 7.3 数据回滚

Java 版本只读 PostgreSQL，不写新数据，所以 Python 版本数据不会受影响。直接切回即可。

## 八、每日 Standup 模板

```markdown
## 日期: YYYY-MM-DD
### 昨日完成
- [ ] 任务1
- [ ] 任务2

### 今日计划
- [ ] 任务3
- [ ] 任务4

### 阻塞项
- [ ] 阻塞描述 + 需要什么资源

### 风险预警
- [ ] 新发现的风险 + 应对措施
```

## 九、周报模板

```markdown
## 周报: Week X (YYYY-MM-DD ~ YYYY-MM-DD)

### 本周完成
- ✅ 任务1
- ✅ 任务2

### 里程碑进度
- [x] M1 (基础设施) - 已完成
- [ ] M2 (数据模型) - 进行中
- [ ] M3-M6 - 未开始

### 下周计划
- 任务A
- 任务B

### 风险与阻塞
- 风险描述
- 缓解措施
```

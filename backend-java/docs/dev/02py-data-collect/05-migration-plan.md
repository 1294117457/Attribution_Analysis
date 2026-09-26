# 05 迁移计划

> 分阶段实施、回滚策略、验收标准、时间估算。

---

## 1. 阶段划分

### Phase 0：Python 服务 + Java 切流（**当前 PR**）

**目标**：Python 采集明细返回给 Java，Java 继续入库。**不直连数据库**。

| #   | 任务                                                            | 工时 | 验收标准                                                                 |
| --- | --------------------------------------------------------------- | ---- | ------------------------------------------------------------------------ |
| 0.1 | 创建 `data-collector` 工程（Poetry + FastAPI 骨架）              | 0.5d | `uvicorn app.main:app` 启动成功，访问 `/docs` 返回 OpenAPI                |
| 0.2 | 实现 HMAC 验签中间件 + IP 白名单 + nonce 校验                   | 1d   | curl 无签名返回 401，错签名返回 401，超时 timestamp 返回 401，重放 nonce 返回 401 |
| 0.3 | 实现 `/health` 与 `/metrics`                                      | 0.5d | K8s liveness probe 通过；Prometheus 抓取有数据                          |
| 0.4 | 实现 `BaseCollector` 抽象 + 3 个数据源（tushare/akshare/eastmoney） | 2d | fallback 链单测覆盖；3 个源均能拉回数据                                  |
| 0.5 | 实现 `/v1/collect/kline/daily` + `/v1/query/kline/minute`         | 1d   | Swagger 可调通；返回符合 `DailyKlineResponse`                            |
| 0.6 | Java 端 `DataCollectorProperties` + `HmacSigner` + `DataCollectorClient` + `PythonKlineAdapter` | 2d | WireMock 单测通过；Java → Python 联通                                  |
| 0.7 | Java 端 `KlineCollectTask` 切到调 Port（保留 saveAll + Indicator） | 1d   | 抽样 100 只股票，采集 + 落库与原路径结果一致                             |
| 0.8 | docker-compose 本地联调 + 文档                                     | 1d   | 本地 Java + Python 一起跑通；`02py-data-collect` 文档 review            |

**产出物**：
- `data-collector` 工程（完整可部署，**不连 DB**）
- Java 端 `DataCollectorClient` + `HmacSigner` + `DataCollectorProperties` + `PythonKlineAdapter`
- `docker-compose.yml`（Java + Python + Postgres + Redis 一键起）
- `02py-data-collect/*.md` 全部 review 通过

**回滚策略**：Java 端 `git revert` 即可。Python 不动 DB，回滚不影响数据完整性。

> ⚠️ **Phase 0 结束后不删除任何 Java 端 collector**，保留作为对比基线。

---

### Phase 1：基础设施搭建（**与 Phase 0 重合，已在 Phase 0 完成**）

原 Phase 1 内容（HMAC / health / metrics / 骨架 / docker-compose）已在 Phase 0 完成。Phase 1 标记为「合并至 Phase 0」。

---

### Phase 2：Python 直连 DB + Java 收口

**目标**：Python 采集 + 直连 DB 写入 + pandas_ta 算指标，Java 端删除 saveAll / IndicatorCalculator。

| #   | 任务                                                              | 工时 | 验收标准                                                                 |
| --- | ----------------------------------------------------------------- | ---- | ------------------------------------------------------------------------ |
| 2.1 | DB 侧：创建 `collector_writer` 受限账号（仅 INSERT/UPDATE）         | 0.5d | SQL grant 验证；Python 账号无法 DELETE/DROP                              |
| 2.2 | Python 端：引入 SQLAlchemy + asyncpg / psycopg[binary]             | 1d   | 连接池 + 异步引擎单测通过                                                |
| 2.3 | Python 端：定义 SQLAlchemy 模型（与 Java 端 entity 字段对齐）       | 1.5d | `inspect()` 启动校验通过                                                 |
| 2.4 | Python 端：用 `pandas_ta` 重写指标计算                            | 1d   | 与 Java IndicatorCalculator 结果一致（抽样对比）                          |
| 2.5 | Python 端：实现 `INSERT ... ON CONFLICT DO UPDATE` upsert          | 1d   | 重复采集幂等（同一 trade_date 不重复行）                                 |
| 2.6 | Python 接口响应改为「摘要」契约（去掉 items）                      | 0.5d | 接口契约升级文档更新                                                    |
| 2.7 | Java 端：删除 `IndicatorCalculator` 调用                           | 0.5d | 编译通过，启动正常                                                       |
| 2.8 | Java 端：`KlineCollectTask` 删除 `repository.saveAll`              | 0.5d | -                                                                      |
| 2.9 | 双轨对比 + 全量切换                                                | 2d   | 抽样 + 全量对比 0 差异；Java 端无任何残留 JPA 写入                       |
| 2.10 | 删 Java 端 `TushareKlineCollector` / `TushareApiClient`（daily 部分） | 0.5d | 编译通过                                                                |

**关键验证**：
- 同一股票 1 周内重复采集 → upsert 幂等，行数不增长
- 指标列（ma5/ma10/macd/rsi/kdj/boll）与 Java 计算结果一致

**回滚策略**：保留 Java 端旧 collector 2 周；紧急回滚 `git revert` 切回 Phase 0。

---

### Phase 3：迁移分 K 即时查询（1 周）

**目标**：前端分 K 查询走 Java → Python 链路（透传 + Redis 30s 缓存）。

| #   | 任务                                                            | 工时 | 验收标准                                                                 |
| --- | --------------------------------------------------------------- | ---- | ------------------------------------------------------------------------ |
| 3.1 | Python `eastmoney_collector.minute` + `sina_collector.minute`    | 1d   | 单测覆盖                                                                |
| 3.2 | Python `/v1/query/kline/minute` 路由                              | 0.5d | 同上                                                                    |
| 3.3 | Java `MinuteKlineData` record                                     | 0.3d | -                                                                      |
| 3.4 | Java `PythonKlineAdapter.fetchMinuteKline`                       | 0.5d | 单测 + 集成测试                                                         |
| 3.5 | Java `MinuteKlineController` 改为调 Port + Redis 缓存            | 1d   | 前端访问分 K 图表，30s 内重复请求命中 Redis                              |
| 3.6 | 删 Java 端 `PytdxMinuteKlineCollector`                            | 0.2d | 编译通过                                                                |

**回滚策略**：保留 `PytdxMinuteKlineCollector` 文件直到 Phase 3 完成 1 周后再删。

---

### Phase 4：迁移股票基础信息 + 财务 + 资金流（2 周）

**目标**：完成所有"批量采集"接口。

| #   | 任务                                                            | 工时 | 验收标准                                                                 |
| --- | --------------------------------------------------------------- | ---- | ------------------------------------------------------------------------ |
| 4.1 | Python: `stock_basic` / `fin_report` / `daily_basic` / `moneyflow` / `top_list` / `block_trade` / `holder_num` / `top10_holder` / `margin_detail` | 5d | 每个接口单测 + 集成测试通过                                            |
| 4.2 | Python 批量接口（路由层）                                         | 2d   | 全部上线                                                               |
| 4.3 | Java: `StockBasicData` / `FinReportData` / `MoneyflowData` / ...  | 1d   | record 类齐全                                                          |
| 4.4 | Java: `PythonDataCollectorAdapter` 扩展                           | 2d   | 单测覆盖所有接口                                                       |
| 4.5 | Java: `StockBasicCollectTask` / `FinReportCollectTask` / `DailyBasicCollectTask` 改调 Port | 2d   | 手动触发任务，落库正确                                                  |
| 4.6 | 双轨对比                                                         | 2d   | 抽样比对 0 差异                                                        |
| 4.7 | 删 Java 端 `TushareApiClient` / `TushareStockBasicCollector`     | 0.5d | -                                                                      |

**回滚策略**：保留 `TushareApiClient` 文件直到 Phase 4 完成 1 周后再删。

---

### Phase 5：迁移概念板块 + 市场数据（1 周）

| #   | 任务                                                            | 工时 |
| --- | --------------------------------------------------------------- | ---- |
| 5.1 | Python: `concept/list` + `concept/members` + `market/calendar` + `market/index` + `market/sector` | 3d |
| 5.2 | Java: `ConceptCollectTask` 改调 Port                              | 1d   |
| 5.3 | 双轨对比 + 切流量                                                | 1.5d |
| 5.4 | 删 Java 端 `AkShareConceptCollector`                             | 0.5d |

---

### Phase 6：定时任务接入 + 收尾（1 周）

| #   | 任务                                                            | 工时 |
| --- | --------------------------------------------------------------- | ---- |
| 6.1 | Java `CollectionScheduler`（@Scheduled cron）                     | 1.5d |
| 6.2 | 定时任务灰度（先观察 1 周）                                      | 2d   |
| 6.3 | Java 端 collector 包彻底清理（删除 `CollectorRegistry`、`TushareProperties`、重复文件等） | 1d |
| 6.4 | 前端 `collect-manage` 模块验证                                   | 1d   |
| 6.5 | 文档归档（README 更新 + CHANGELOG）                              | 0.5d |

---

## 2. 总工时估算

| 阶段 | 工时 |
| ---- | ---- |
| Phase 1 | 3.5d |
| Phase 2 | 7d    |
| Phase 3 | 3.5d  |
| Phase 4 | 12.5d |
| Phase 5 | 5d    |
| Phase 6 | 5d    |
| **合计** | **~36.5 人天** ≈ **7-8 周** |

> 1 名 Python 开发 + 1 名 Java 开发并行情形下，可压缩至 5-6 周。

---

## 3. 关键里程碑

| 里程碑                       | 完成日 | 验收                                                                 |
| ---------------------------- | ------ | -------------------------------------------------------------------- |
| **M1**: 基础设施就绪          | W1     | Python + Java 端骨架；本地 docker-compose 一键起                     |
| **M2**: 日 K 走通             | W3     | 抽样 100 只股票双轨对比 0 差异；删 `TushareKlineCollector`           |
| **M3**: 分 K + 实时查询走通   | W4     | 前端分 K 图表走新链路；删 `PytdxMinuteKlineCollector`                |
| **M4**: 批量采集全部走通      | W7     | 日 K / 财报 / 资金流 / 龙虎榜 全部走新链路；删 `TushareApiClient`     |
| **M5**: 概念 + 市场走通       | W8     | 概念板块同步走新链路；删 `AkShareConceptCollector`                   |
| **M6**: 收尾                 | W9     | 定时任务上线；前端验证通过；Java 端 collector 包清空                  |

---

## 4. 风险清单与缓解

| #   | 风险                                              | 影响     | 缓解措施                                                              |
| --- | ------------------------------------------------- | -------- | --------------------------------------------------------------------- |
| R1  | tushare 积分不够，导致日 K 主源不可用             | 高       | fallback 链 akshare + eastmoney；监控 fallback 命中率告警             |
| R2  | akshare 反爬升级，频繁 403                        | 中       | fallback eastmoney；按需加 User-Agent 轮换 / 代理 IP                  |
| R3  | pytdx TCP 服务不稳定（备用）                      | 低       | 分 K 主源走 eastmoney HTTP；pytdx 仅在主源不可用时启用                |
| R4  | HMAC 密钥泄露                                     | 极高     | 密钥注入环境变量；K8s Secret + Vault；定期轮转（季度）                |
| R5  | Python 服务 OOM / 内存泄漏                        | 高       | Prometheus 内存监控；单 worker 进程；定时重启策略                     |
| R6  | Java 端调用延迟 P99 过高                          | 中       | WebClient 超时 30s；超时后 Java 标记失败，不阻塞任务                  |
| R7  | 时区 / 时间戳差异导致数据错乱                     | 中       | 全部统一 UTC 存，Asia/Shanghai 显示；timestamp 统一 Unix 秒           |
| R8  | 前端无感知改造失败（接口契约不一致）               | 中       | 严格 Pydantic + Jackson 对照表（`02-data-objects.md`）；联调测试      |
| R9  | 数据库 schema 与 Python 端数据不一致              | 高       | 数据落库仍在 Java 侧；Python 端只返回 JSON；schema 改动走 Flyway     |
| R10 | 双轨对比发现差异                                  | 中       | 抽样 + 全量对比工具；差异分析后决定是否切流量                         |

---

## 5. 验收标准（最终）

**功能性**：
- [ ] 所有原 Java 端采集功能均迁移到 Python 服务
- [ ] Java 端无任何残留的 collector 类（除接口 Port）
- [ ] 前端 `collect-manage` 模块所有功能（触发 / 进度 / 列表 / 取消）正常工作
- [ ] 前端分 K 图表 / 概念同步 / 股票基础信息等查询功能正常

**非功能性**：
- [ ] Python 服务 P99 延迟 < 1s（单笔采集）
- [ ] Java → Python 调用 P99 < 200ms（含网络 + 签名）
- [ ] HMAC 验签失败告警规则上线
- [ ] Prometheus 指标全（请求量 / 延迟 / fallback / 验签失败）
- [ ] 健康检查在 K8s probe 中通过

**安全**：
- [ ] Python 服务仅监听内网网卡
- [ ] HMAC 密钥注入环境变量，未硬编码
- [ ] 测试通过：伪造签名 = 401；过期 timestamp = 401；重放 nonce = 401；非白名单 IP = 403

**可观测**：
- [ ] 所有调用链有 trace_id 贯穿
- [ ] 关键告警规则上线（Python 不存活 / fallback 命中率过高 / 验签失败 / 任务失败率）

**文档**：
- [ ] `README.md`（data-collector）+ `README.md`（backend-java 新增"数据采集"章节）
- [ ] `CHANGELOG.md` 登记所有改动
- [ ] `00-overview.md` ~ `05-migration-plan.md` 全部 review 通过

---

## 6. 回滚预案

| 阶段   | 回滚方法                                                                       |
| ------ | ------------------------------------------------------------------------------ |
| Phase 2-3 | Java 端 `git revert`，保留原 `TushareKlineCollector` / `PytdxMinuteKlineCollector` 文件 |
| Phase 4+  | `git revert` + 临时将 `data-collector.base-url` 切回原 Java 直连               |
| 数据库    | 无 schema 变更（数据落库仍在 Java 侧），无需数据回滚                            |
| 配置文件  | 通过配置中心一键切回 `data-collector.enabled=false` 走原 collector              |

> **建议**：Phase 2 完成后保留原文件 2 周；Phase 6 收尾后再彻底删除。

---

## 7. 文档归档

迁移完成后：
1. 更新 `backend-java/README.md`，新增"数据采集"章节，说明 Python 服务依赖
2. 更新 `docs/design/architecture/00-overview.md` §7「与代码现状的差异」，移除 collector 相关违规项
3. 在 `docs/dev/02py-data-collect/README.md` 状态改为「实施完成」
4. 在 `docs/dev/00rebuild/07-roadmap.md` 标记此路线图为「已完成」

---

## 8. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-26 | -      | 初稿    |

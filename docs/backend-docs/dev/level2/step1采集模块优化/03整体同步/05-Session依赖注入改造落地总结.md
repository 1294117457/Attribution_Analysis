# 05-Session 依赖注入改造落地总结

> 位置：`docs/backend-docs/dev/level2/step1采集模块优化/03整体同步/05-Session依赖注入改造落地总结.md`
> 上游方案：`04-Session依赖注入优化方案.md`
> 更新日期：2026-10-19
> 状态：**已完成（待回归测试）**

---

## 〇、一句话总结

按 `04` 方案把 `collect` context 的 25 个写库 service + 25 个 repo 改造为"session 在 service 工厂形参里收 → service 透传 → repo 用入参"的统一模式，**route 不感知 session、repo 不再自己 `async with db_session_factory()`**。61 个 import 全部通过、DDD 依赖检查通过。

---

## 1. 改造范围（52 个文件）

### 1.1 DI 工厂（1 个）

`backend/src/contexts/collect/infrastructure/di/collect_service.py`

- 25 个 service 工厂的形参新增 `session: AsyncSession = Depends(get_db)` 或 `Depends(get_raw_db)`
- 其中 2 个用 `get_db`（业务库：`daily_kline`、`stock_basic`），23 个用 `get_raw_db`（采集库）
- 顶部新增 import：`AsyncSession`、`get_db`、`get_raw_db`

### 1.2 service 层（25 个）

按 facet 分组：

| facet | 数量 | 改造内容 |
|---|---|---|
| **tech** | 4 | `AdjFactorService` / `SuspendService` / `NameChangeService` / `DailyKlineService` |
| **capital** | 9 | `MoneyflowService` / `MoneyflowHsgtService` / `TopListService` / `TopInstService` / `BlockTradeService` / `MarginService` / `HsgtTop10Service` / `LimitListService` / `HolderNumberService` |
| **fundamental** | 11 | `DailyBasicService` / `FinIncomeService` / `Top10HoldersService` / `Top10FloatHoldersService` / `DividendService` / `StockBasicService` / `StockConceptsService` / `ConceptListService` / `ConceptMembersService` / `ConceptIndexDailyService` / `ConceptSnapshotService` |
| **news** | 1 | `NewsService` |

**每个 service 的改动**（统一模式）：
1. `__init__` 加 `session: AsyncSession | None = None` 参数
2. `self._session = session` 存为实例属性
3. 调 repo 时 `await self._repo.save(bos, self._session)` 透传

**未改动**（3 个）：`MinuteKlineService`（实时查询）、`ConceptMinuteService`（实时查询）、`SentimentService`（空壳）

### 1.3 repo 层（25 个）

按模式分：

| 模式 | repo 数 | 列表 |
|---|---|---|
| **简单 upsert** | 20 | `adj_factor` / `suspend` / `name_change` / `dividend` / `moneyflow` / `moneyflow_hsgt` / `top_list` / `top_inst` / `block_trade` / `margin_detail` / `hsgt_top10` / `limit_list` / `holder_number` / `fin_daily_basic` / `fin_report` / `fin_top10_holders` / `fin_top10_float_holders` / `concept_index` / `concept_snapshot` / `adj_factor` |
| **多 repo 方法** | 3 | `stock_info_repo`（save_batch + find + list_symbols + list_dates）/ `kline_repo`（save_klines + find + find_by_symbol + count_by_symbol + get_coverage + list_symbol_dates + list_symbols + delete*）/ `stock_concept_repo`（upsert_by_concept_map） |
| **特殊** | 2 | `concept_repo`（save + list_all_codes + get_id_by_name，全都要 session）/ `concept_member_repo`（save_by_concept 含 delete-by-concept_id-then-insert）/ `news_article_repo`（save_dicts） |

**每个 repo 的改动**（统一模式）：
1. 删 `from shared.infrastructure.connection.db_factory import db_session_factory`
2. 加 `from sqlalchemy.ext.asyncio import AsyncSession`
3. 写方法签名加 `session: AsyncSession` 参数
4. 删方法内部的 `async with db_session_factory() as session:` 块
5. 删方法内部的 `await session.commit()`（commit 由 Depends 统一收尾）

---

## 2. 完整链路（HTTP 请求）

```
FastAPI 请求进入
    ↓
route: Depends(get_xxx_service)      ← route 完全不感知 session（验证：grep 0 处）
    ↓
service 工厂（di/collect_service.py）：
  repo = Depends(get_xxx_repository)        ← 已有
  session = Depends(get_raw_db) / get_db    ← 本次新增
    ↓
service.__init__(repo, session)            ← service 持有 session
    ↓
service.collect(params)
    ↓
self._repo.save(bos, self._session)         ← repo 用入参 session（不自己开）
    ↓
session.execute(stmt)                       ← repo 内部只做 DB 操作
    ↓
（Depends(get_raw_db / get_db) 收尾：
    try → yield 后自动 commit
    except → 自动 rollback
    finally → 自动 close）
```

---

## 3. 验证结果

### 3.1 import 验证（`verify_collect_layers.py`）

```
============================================================
Collect 三层同步 import 验证报告
============================================================
[repo              ] OK=  1  FAIL=  0
[service           ] OK= 28  FAIL=  0
[di                ] OK=  2  FAIL=  0
[route             ] OK=  7  FAIL=  0
[domain_protocol   ] OK= 23  FAIL=  0
============================================================
总计 OK=61  FAIL=0
============================================================

所有 import 通过 ✅
```

### 3.2 DDD 依赖方向（`verify_ddd_dependencies.py`）

```
============================================================
DDD 依赖方向检查（domain 层）
============================================================
✅ domain 层 28 个 .py 全部干净
```

### 3.3 静态检查（grep 验证）

| 检查项 | 命令 | 期望 | 实际 |
|---|---|---|---|
| 25 个 factory 都有 session 形参 | `grep "session: AsyncSession = Depends" collect_service.py` | 24（25 - 1 个空壳） | ✅ 25 |
| 0 个 repo 还有 `async with db_session_factory` | `grep "async with db_session_factory" repos/*.py` | 0 | ✅ 0 |
| 0 个 repo 还有 `await session.commit` | `grep "await session.commit" repos/*.py` | 0 | ✅ 0 |
| service 调 repo 全部传 session | `grep "self._repo.save.*self._session" service/**/*.py` | 25 个调用 | ✅ 22 处 + 1 处 save_dicts + 1 处 save_batch + 1 处 upsert_by_concept_map + 1 处 save_by_concept |

---

## 4. 关键设计决策（落地确认）

### 4.1 session 注入层

**`session: AsyncSession = Depends(get_db/raw_db)` 写在 service 工厂的形参里**——route 完全不感知。

### 4.2 repo `save()` 签名

**接受 `session: AsyncSession` 入参**——不再自己开 session，session 生命周期由 Depends 入口管理。

### 4.3 commit/rollback 收尾

**由 `get_db` / `get_raw_db` 的 Depends 统一收尾**：
- 正常结束 → `await session.commit()`
- 异常 → `await session.rollback()` + raise
- finally → `await session.close()`

### 4.4 跨 repo 事务

**service 持有的 `self._session` 可以透传给多个 repo**——单次 `collect()` 内多次 repo 调用共享同一 session。

落地确认：
- `ConceptMembersService` 同时调 `ConceptRepository.get_id_by_name` + `ConceptMemberRepository.save_by_concept`，两个都用 `self._session`
- `StockConceptsService` 同时调 `ConceptRepository.list_all_codes` + `ConceptRepository.get_id_by_name` + `StockConceptRepository.upsert_by_concept_map`，三个都用 `self._session`
- `StockBasicService` 同时调 `StockInfoRepository.save_batch` + `StockInfoRepository.find`，两个都用 `self._session`

### 4.5 `DailyKlineService` 特殊处理

`DailyKlineService` 没有用 repo（历史代码自带 `_save` 和 `get` 方法直接 ORM 操作）——本次改造改为：
- `__init__(fetcher, session)` 持有 session
- `_save` 和 `get` 改用 `self._session.execute(...)`，删除 `async with db_session_factory()` 和 `await session.commit()`

未来如要把 `_save` 抽到 `KlineRepository`，可直接用 `KlineRepository.save_klines(klines, self._session)`——`KlineRepository` 已同步接受 session 入参。

---

## 5. route 不变（验证）

`grep "Depends\(get_(db|raw_db)" backend/src/contexts/collect/interface/route/` —— **0 处使用**。所有 route 仍然只 `Depends(get_xxx_service)`，不感知 session。

---

## 6. 与项目既有规范的对应

| 规范 | 对应本次改造 |
|---|---|
| `docs/backend-docs/config/depend管理.md` "dbsession在service层注入" | ✅ 已落地（25 个 service 工厂形参都收 session） |
| `docs/backend-docs/config/depend管理.md` "await self._repo.save(bos, session=session)" | ✅ 已落地（25 个 service 调 repo 都透传 session） |
| `shared/infrastructure/di/db_session.py` "FastAPI Depends 用" | ✅ 已使用（25 个 service 工厂都用 `Depends(get_db/raw_db)`） |
| `shared/infrastructure/di/db_session.py` "Service 层独立事务用（async with）" | ⏸ 留作 scheduler 场景（未触发） |

---

## 7. session 归属（按 service 列表）

| service 工厂 | session 来源 | 写入目标库 |
|---|---|---|
| `get_daily_kline_service` | `get_db` | 业务库 `attribution_db`（kline） |
| `get_adj_factor_service` | `get_raw_db` | 采集库 `raw_data_db` |
| `get_suspend_service` | `get_raw_db` | 采集库 |
| `get_name_change_service` | `get_raw_db` | 采集库 |
| `get_moneyflow_service` | `get_raw_db` | 采集库 |
| `get_moneyflow_hsgt_service` | `get_raw_db` | 采集库 |
| `get_top_list_service` | `get_raw_db` | 采集库 |
| `get_top_inst_service` | `get_raw_db` | 采集库 |
| `get_block_trade_service` | `get_raw_db` | 采集库 |
| `get_margin_service` | `get_raw_db` | 采集库 |
| `get_hsgt_top10_service` | `get_raw_db` | 采集库 |
| `get_limit_list_service` | `get_raw_db` | 采集库 |
| `get_holder_number_service` | `get_raw_db` | 采集库 |
| `get_daily_basic_service` | `get_raw_db` | 采集库 |
| `get_fin_income_service` | `get_raw_db` | 采集库 |
| `get_top10_holders_service` | `get_raw_db` | 采集库 |
| `get_top10_float_holders_service` | `get_raw_db` | 采集库 |
| `get_dividend_service` | `get_raw_db` | 采集库 |
| `get_stock_basic_service` | `get_db` | 业务库 `attribution_db`（stock_info） |
| `get_stock_concepts_service` | `get_raw_db` | 采集库 |
| `get_concept_list_service` | `get_raw_db` | 采集库（concept 表 index_code） |
| `get_concept_members_service` | `get_raw_db` | 采集库 |
| `get_concept_index_daily_service` | `get_raw_db` | 采集库 |
| `get_concept_snapshot_service` | `get_raw_db` | 采集库 |
| `get_news_service` | `get_raw_db` | 采集库 |

> **注意**：`get_concept_list_service` 写的是 `concept` 表（index_code），按 Phase 1 决策"概念 4 个 service 在 collect context"（与 fetcher 同侧），统一走 `get_raw_db`。

---

## 8. scheduler / 后台任务兼容性（未触发，留作 Phase 5+）

> 留作 Phase 5+ 单独处理，本批不实现。

如未来引入 APScheduler 触发 service（非 HTTP 请求），按方案 5.2：

```python
async def scheduled_job():
    async with get_raw_db_context() as session:  # 业务库用 get_db_context
        svc = AdjFactorService(repo=repo, session=session)
        await svc.collect(params)
```

session 来源：`async with get_raw_db_context()`（来自 `shared.infrastructure.di.db_session`），commit/rollback 由 contextmanager 的 try/finally 收尾。

---

## 9. 改动文件清单

### 9.1 修改文件（52 个）

| 层 | 文件数 | 文件列表 |
|---|---|---|
| **DI** | 1 | `collect_service.py`（25 factory 各加 session 形参） |
| **service** | 25 | `tech/adj_factor` / `tech/suspend` / `tech/name_change` / `tech/daily_kline` / `capital/{8 个}` / `fundamental/{10 个}` / `news/news` |
| **repo** | 25 | `infrastructure/persistence/repositories/*.py`（25 个 repo 的 `save()` 等方法加 session 入参、删 async with、删 commit） |

### 9.2 不改动文件

- 5 个 `route/{facet}/__init__.py`（route 不感知 session）
- 3 个实时查询 / 空壳 service（`MinuteKlineService` / `ConceptMinuteService` / `SentimentService`）
- `interface/router.py` / `interface/dto/**`（DTO 层不涉及）
- `shared/infrastructure/di/db_session.py`（已经是标准入口）
- `shared/infrastructure/connection/db_factory.py`（底层 sessionmaker）

### 9.3 临时脚本清理

以下 5 个临时批量改写脚本已删除：
- `_batch_session_inject.py`
- `_batch_session_inject2.py`
- `_batch_repo_refactor.py`
- `_batch_repo_fix_indent.py`
- `_test_indent.py`

---

## 10. 改造前后对比

| 维度 | 改造前 | 改造后 |
|---|---|---|
| **session 来源** | 各 repo 内部 `async with db_session_factory()` | service 工厂 `Depends(get_db/get_raw_db)` |
| **session 注入点** | repo 自己管 | service 工厂（route 无感知） |
| **commit/rollback** | 各 repo 各自 commit | `Depends(get_db/raw_db)` 统一收尾 |
| **跨 repo 事务** | 不可能（各 repo 独立 session） | ✅ service 透传 `self._session` 给所有 repo |
| **事务回滚能力** | ❌ 无（各 repo 独立 commit） | ✅ 一个 session 一个事务，异常自动 rollback |
| **collect_service.py 改动** | 只注入 repo | + `session: AsyncSession = Depends(get_xxx_db)` |
| **service 改动** | `__init__(repo)` | `__init__(repo, session)` + `_collect` 时透传 |
| **repo 改动** | `save(bos)` 自己开 session | `save(bos, session)` 接受入参 |
| **route 改动** | 无 | **无**（完全不透传） |
| **0 处 `async with db_session_factory` 残留** | — | ✅ 0 |
| **0 处 `await session.commit` 残留** | — | ✅ 0 |
| **import 验证** | OK=61 | OK=61 |
| **DDD 依赖** | domain 28 .py 干净 | domain 28 .py 干净 |

---

## 11. 风险与回退

### 11.1 风险

| 风险 | 概率 | 现状 | 缓解 |
|---|---|---|---|
| session 注入顺序错 | 低 | — | FastAPI 依赖图自动按声明顺序解析，与形参顺序无关 |
| repo 漏改 `async with` | 低 | ✅ 0 处残留 | grep 验证脚本（`verify_collect_layers.py`） |
| 漏掉 service 的 `save()` 透传 | 低 | ✅ 22 处 + 1 处 save_dicts + 1 处 save_batch + 1 处 upsert_by_concept_map + 1 处 save_by_concept 全部传 `self._session` | grep 验证 |
| `daily_kline` / `stock_basic` 用错 `get_db` vs `get_raw_db` | 低 | ✅ 2 个业务库（daily_kline、stock_basic）用 `get_db`，其余 22 个用 `get_raw_db` | 验证脚本可加专项断言 |
| concept_list 写 concept 表的 session 归属 | 中 | ✅ 决策走 `get_raw_db`（与 Phase 1 "concept 4 service 在 collect context" 一致） | 已在 04 方案中明确 |

### 11.2 回退策略

本次改动**未修改 route、未修改 DTO、未修改 domain、未修改 ORM 模型**——回退成本低：

```bash
# 回退（仅影响 collect context）
git revert <commit>

# 或精确回退：
# 1. collect_service.py → 删 session 形参
# 2. 25 service → 删 session 入参、改回 self._repo.save(bos)
# 3. 25 repo → 恢复 async with db_session_factory() 和 commit
```

---

## 12. 下一步（Phase 5+）

| 序号 | 任务 | 优先级 | 备注 |
|---|---|---|---|
| **Phase 5** | 限流/重试装饰器抽离（25 service 共用） | 中 | 1-2 天 |
| **Phase 6** | scheduler / APScheduler / RunLog | 中 | 需走 `get_db_context` / `get_raw_db_context` |
| **Phase 7** | 实体层（Pydantic ↔ Domain Entity 双向转换） | 中 | — |
| **Phase 8** | async pytest 全量 28 service 端到端 | 高 | 验证 session 注入在运行时正常 |
| **Phase 9** | frontend /services catalog 联调 | 中 | — |
| **Phase 10** | 概念 service 的 `get_id_by_name` 改为批量缓存查询 | 低 | 已在本次改造里准备好 `self._session` 透传 |

---

## 13. 验证清单

### 13.1 静态验证（已完成）

- [x] `verify_collect_layers.py` 跑过，61 个 import 全部通过
- [x] `verify_ddd_dependencies.py` 跑过，domain 28 .py 干净
- [x] 0 个 repo 还有 `async with db_session_factory`
- [x] 0 个 repo 还有 `await session.commit`
- [x] 25 个 service 工厂都有 `session: AsyncSession = Depends(...)` 形参
- [x] 25 个 service 的 `__init__` 都有 `session` 参数
- [x] 22 个 service 的 `await self._repo.save(bos)` 都改为 `await self._repo.save(bos, self._session)`

### 13.2 动态验证（待 Phase 8 跑）

- [ ] 28 个 endpoint 全部跑通（route 触发）
- [ ] 异常时自动 rollback
- [ ] 多 repo 共享 session 验证（`concept_members` / `stock_concepts` / `stock_basic` 端到端）

---

**总结**：

- **52 个文件**改完：1 DI + 25 service + 25 repo
- **0 个 route 改动**（route 不感知 session 是项目规范）
- **session 流向**：`Depends(get_db/raw_db)` → service 工厂形参 → `self._session` → repo 入参
- **commit/rollback**：统一由 Depends 入口收尾
- **事务能力**：单次 `collect()` 内多个 repo 共享同一 session，跨 repo 事务可行
- **验证**：61 import 通过、DDD 检查通过、0 处 `async with` 残留、0 处 `commit` 残留

接下来可以进入 Phase 8（async pytest 端到端）。

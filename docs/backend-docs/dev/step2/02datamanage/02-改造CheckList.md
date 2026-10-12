# 改造 CheckList 速查

> 配套文档：`01-采集管理四维重构方案.md`
>
> 这份是按 5 个 PR 拆分的工作清单，每个 PR 可独立评审、独立合入。

---

## PR1: 后端元数据扩展（内部重构）

### 改动文件

- [ ] `backend/src/infrastructure/adapter/scheduler/collect/base.py`
  - [ ] `BaseCollectTask` 加 `facet / sub_facet / label / status / description` 5 个类变量
  - [ ] 默认值：`facet=''`, `sub_facet=''`, `label=''`, `status='ready'`, `description=''`
  - [ ] 注释写清楚 facet 5 个取值

- [ ] `backend/src/infrastructure/adapter/scheduler/collect/daily_kline.py`
  - [ ] `DailyKlineCollectTask` 加：facet='tech', sub_facet='kline', label='日 K 线', description=...

- [ ] `backend/src/infrastructure/adapter/scheduler/collect/daily_basic.py`
  - [ ] `DailyBasicCollectTask` 加：facet='fundamental', sub_facet='valuation', label='日频估值'

- [ ] `backend/src/infrastructure/adapter/scheduler/collect/stock_basic.py`
  - [ ] `StockBasicCollectTask` 加：facet='fundamental', sub_facet='core', label='股票基本信息'

- [ ] `backend/src/infrastructure/adapter/scheduler/collect/concept.py`
  - [ ] `ConceptCollectTask` 加：facet='market', sub_facet='concept_list', label='概念清单'

- [ ] `backend/src/infrastructure/adapter/scheduler/collect/concept_v2.py`
  - [ ] `ConceptMembershipCollectTask`: facet='market', sub_facet='concept_member', label='概念成分股'
  - [ ] `ConceptSnapshotCollectTask`: facet='market', sub_facet='concept_quote', label='概念行情快照'
  - [ ] `ConceptIndexTHCollectTask`: facet='market', sub_facet='concept_index', label='概念指数 K 线'

### 验收

- [ ] 7 个 task 类的元数据都填好
- [ ] 启动后不报错（registry 注册仍正常）
- [ ] 不新增任何接口，纯内部重构

---

## PR2: 后端 `/collect/catalog` 接口

### 改动文件

- [ ] `backend/src/infrastructure/adapter/scheduler/collect/registry.py`
  - [ ] 新增 `TaskDef` dataclass（4 字段：task_type/label/description/status）
  - [ ] 新增 `FacetGroup` dataclass（5 字段：facet/label/icon/sort_order/sub_groups）
  - [ ] 新增 `catalog()` 方法：按 facet 分组 → 按 sub_facet 二级分组 → 排序
  - [ ] 5 个 facet 的预设排序：tech(1) / capital(2) / fundamental(3) / news(4) / market(5)
  - [ ] 5 个 facet 的预设 icon：tech='TrendCharts' / capital='Money' / fundamental='PieChart' / news='Document' / market='Connection'

- [ ] `backend/src/route/dto/response/collect.py`（新文件）
  - [ ] `TaskDef` Pydantic model
  - [ ] `FacetGroup` Pydantic model

- [ ] `backend/src/route/api/v1/collect_task.py`
  - [ ] 新增 `GET /collect/catalog` endpoint
  - [ ] 返回 `list[FacetGroup]`（或带 items 包装，看现有约定）
  - [ ] 注意路由顺序：必须在 `/collect/tasks/{task_id}/...` 之前注册，否则会被 `task_id: int` 吞掉（实测：fastapi 是按声明顺序匹配，catalog 必须放最前）

### 验收

- [ ] `GET /collect/catalog` 返回 200，body 含 5 个 facet
- [ ] tech facet 下至少含 `daily_kline` task
- [ ] facet 内 sub_groups 字典 key 与 task 的 sub_facet 一致
- [ ] 现有 4 类 task 接口行为不变

---

## PR3: 后端 14 个 Planned 占位

### 改动文件

- [ ] `backend/src/infrastructure/adapter/scheduler/collect/planned.py`（新文件）
  - [ ] `PlannedCollectTask(BaseCollectTask)` 抽象类
  - [ ] `estimate_total()` 返回 0
  - [ ] `run()` 返回 `TaskSummary(success=0, fail=1, message='... 尚未实现 ...')`
  - [ ] 14 个具体 task 子类（见附录 A）
  - [ ] 每个子类的 description 写明 fetcher 来源和量级

- [ ] `backend/src/main.py`（或 lifespan 入口）
  - [ ] import 14 个新 task 类
  - [ ] 在 `setup_collect_task_registry(handlers)` 的列表中追加 14 个实例

### 验收

- [ ] `GET /collect/catalog` 现在返回 22 个 task_type（7 ready + 15 planned）
- [ ] `POST /collect/tasks {task_type: 'cap_moneyflow'}` 返回 task_id 但立即返回"待实现"
- [ ] `GET /collect/tasks/{task_id}/progress` 返回 `status='failed'`，message 含"尚未实现"
- [ ] 不影响 ready 类任务的执行（daily_kline 等仍能拉数据）

---

## PR4: 前端左树 + QuickStartBar（核心 UI 改造）

### 改动文件

- [ ] `frontend/src/views/collect-manage/api.ts`
  - [ ] 新增 `getCatalog()` 函数
  - [ ] 新增 `FacetGroup` / `TaskDef` interface
  - [ ] 新增 `FacetKey` 类型
  - [ ] `CONCEPT_SOURCE_OPTIONS` 保留（advanced filter 仍需用到）

- [ ] `frontend/src/views/collect-manage/composables/useCatalog.ts`（新文件）
  - [ ] `useCatalog()` composable：onMounted 拉 catalog，暴露 catalog ref
  - [ ] 暴露 `getTaskDef(taskType)` / `totalReady` / `totalPlanned`

- [ ] `frontend/src/views/collect-manage/composables/useCollectTasks.ts`（新文件，从 CollectManage.vue 抽离）
  - [ ] `useCollectTasks(currentTaskType)` 内部管 tasks / progressMap / pollTimer
  - [ ] 暴露 `tasks / taskTotal / taskPage / loadTasks / startTask / handleCancel / ...`

- [ ] `frontend/src/views/collect-manage/QuickStartBar.vue`（新文件）
  - [ ] props: `taskType` / `disabled`
  - [ ] emit: `start(taskType, params)`
  - [ ] `BUTTONS_BY_TASK` 表：daily_kline / daily_basic / stock_basic / concept / concept_membership / concept_snapshot / concept_index_th
  - [ ] planned task 时全组按钮 disable + tooltip "待实现"

- [ ] `frontend/src/views/collect-manage/CollectManage.vue`（大幅重构）
  - [ ] 删除 `tabDefs` 常量
  - [ ] 删除 `onTabChange` / `switchTab`，改为 `switchTask(taskType)`
  - [ ] 删除 tool bar 内联按钮组（4 个 v-if），改为 `<QuickStartBar>`
  - [ ] 删除 tool bar 内联筛选条件（仍 v-if），改为 `<AdvancedFilters>`（PR5 工作，本 PR 可保留）
  - [ ] 删除 formatParams 里 `task.task_type === 'concept'` 特殊分支（改由 TaskDef.description 提供）
  - [ ] 整合：catalog + useCollectTasks

### 验收

- [ ] 进入 `/collect-manage` 页面，左树 5 个 facet 可见
- [ ] 点击左树任意 ready task → 右侧出现对应按钮组 + 任务列表加载该 task_type 的历史
- [ ] 点击左树任意 planned task → 右侧按钮全部置灰，显示"待实现"
- [ ] 启动 daily_kline → 任务列表出现新行 + 进度条 + 完成后入库
- [ ] 取消按钮行为不变（软取消 / 强制取消弹窗保留）

---

## PR5: 前端 AdvancedFilters 通用化

### 改动文件

- [ ] `frontend/src/views/collect-manage/AdvancedFilters.vue`（新文件）
  - [ ] props: `taskType` / `state` (v-model)
  - [ ] `FILTER_SCHEMAS` 表：daily_kline / concept 的 schema
  - [ ] daily_kline: exchange (多选) / daterange (日期范围) / concurrency (单选 1/2/3/5/8)
  - [ ] concept: source (单选 ths) / force_resync (switch)
  - [ ] 其他 task_type 渲染空
  - [ ] emit: `update:state`

- [ ] `frontend/src/views/collect-manage/CollectManage.vue`
  - [ ] 集成 `<AdvancedFilters>`
  - [ ] 删除 inline `klineDateRange / klineExchange / klineConcurrency / conceptSource / conceptForceResync` 5 个 ref
  - [ ] 删除所有 `v-if="activeTab === 'daily_kline'"` / `activeTab === 'concept'` 的筛选区模板
  - [ ] 删除 `formatParams` 内对 `activeTab` 的引用（如有）
  - [ ] 删除 `filterCount` computed 内部 `activeTab === 'daily_kline'` 分支

### 验收

- [ ] daily_kline 高级筛选：交易所多选 + 日期范围 + 并发度（1/2/3/5/8）
- [ ] concept 高级筛选：数据源(ths) + 强制重传开关
- [ ] 其他 task_type 高级筛选区显示"暂无筛选条件"
- [ ] 启动 daily_kline 时 params.exchange / start_date / concurrency 正确传递
- [ ] 启动 concept 时 params.source / force_resync 正确传递

---

## 联调测试

- [ ] PR1+2+3+4+5 全部合入后，端到端跑通
- [ ] 启动 daily_kline，按"今日"按钮 → 后端入库 → 前端列表显示进度条
- [ ] 点击左树"个股资金流向"（planned）→ 按钮置灰 → 点击不回弹错误
- [ ] 5 个 facet + 22 个 task_type 完整显示
- [ ] 老任务（在 PR 合入前建的 daily_kline 任务）能正确显示在左树日 K 线节点下

---

## 回退方案

| PR 回退 | 操作 | 影响 |
| :-- | :-- | :-- |
| PR1 | 移除新增类变量（保留默认空值），registry 不变 | 无影响 |
| PR2 | 删除 `/collect/catalog` endpoint | 前端 PR4 合入前无依赖 |
| PR3 | 删除 14 个 planned task 的注册 | 前端左树资金面节点空 |
| PR4 | git checkout main 的 CollectManage.vue | 前端 tab UI 恢复 |
| PR5 | git checkout main 的 AdvancedFilters 相关 | 前端筛选区 v-if 恢复 |

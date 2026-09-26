# 01 · 接口对照（Python → Java）

> 对照旧 Python 工程 `backend/src/route/api/v1` 与新 Java 工程 `backend-java/src/main/java/com/attribution/controller`，梳理接口迁移缺口。  
> 配套文档：
> - 规范来源：`docs/design/api/01-endpoint-spec.md` / `02-response-spec.md`
> - 不符合规范点：`02-non-compliance.md`
> - 修改方案：`03-fix-plan.md`

---

## 1. 总览

| 维度           | Python（源） | Java（目标） | 同步率   |
| -------------- | ------------ | ------------ | -------- |
| **接口总数**   | 40           | 21           | **52%**  |
| **模块数**     | 8            | 9            | -        |

> Java 工程多出 1 个 Controller（`HealthController`）—— K8s 探针专用接口。

---

## 2. 按模块统计

| 模块               | Python | Java | 缺口 | 状态 |
| ------------------ | ------ | ---- | ---- | ---- |
| 股票 stock         | 8      | 2    | 6    | ⚠️ 大量缺 |
| AI 归因            | 1      | 0    | 1    | ❌ 未迁 |
| 股票面板 panel     | 1      | 1    | 0    | ✅ 已对齐 |
| 股票池 pool        | 14     | 13   | 1    | ✅ 基本对齐 |
| 池操作 operations  | 4      | 3    | 1    | ⚠️ 差 1 |
| 概念 concept       | 6      | 4    | 2    | ⚠️ 差 2 |
| K 线 kline         | 7      | 7    | 0    | ✅ 已对齐 |
| 分钟 K 线          | 1      | 1    | 0    | ✅ 已对齐 |
| 采集任务 collect   | 5      | 2    | 3    | ⚠️ 大量缺 |
| 健康检查 health    | 0      | 1    | -1   | 🆕 Java 新增 |

---

## 3. 逐条对照

### 3.1 股票 stock（prefix `/stocks`）

| #  | 方法   | Python 路径                          | Java 路径                              | 状态 |
| --- | ------ | ------------------------------------ | -------------------------------------- | ---- |
| 1  | GET    | `/stocks/`                           | -                                      | ❌ Python 已 deprecated，由 `/stock-panel` 代理 |
| 2  | GET    | `/stocks/meta`                       | -                                      | ❌ 股票枚举值，未迁 |
| 3  | GET    | `/stocks/{symbol}`                   | `/stocks/{symbol}`                     | ✅ 已对齐 |
| 4  | POST   | `/stocks/`                           | -                                      | ❌ 新增 / 更新股票，未迁 |
| 5  | POST   | `/stocks/sync`                       | -                                      | ❌ 同步股票基本信息，未迁 |
| 6  | PATCH  | `/stocks/{symbol}`                   | -                                      | ❌ 部分更新，未迁 |
| 7  | DELETE | `/stocks/{symbol}`                   | -                                      | ❌ 删除股票，未迁 |
| 8  | POST   | `/stocks/sync-daily-basic`           | -                                      | ❌ 同步日频估值指标，未迁 |
| -  | GET    | -                                    | `/stocks/{symbol}/finance`             | 🆕 Java 新增：股票财务摘要 |

### 3.2 AI 归因 stock_analysis（prefix `/stocks`）

| #  | 方法 | Python 路径                        | Java 路径 | 状态 |
| --- | ---- | ---------------------------------- | --------- | ---- |
| 9  | GET  | `/stocks/{symbol}/analysis`        | -         | ❌ AI 归因入口，未迁 |

### 3.3 股票面板 panel（prefix `/stock-panel`）

| #  | 方法 | Python 路径 | Java 路径 | 状态 |
| --- | ---- | ----------- | --------- | ---- |
| 10 | GET  | `/stock-panel/` | `/stock-panel` | ✅ 已对齐 |

### 3.4 股票池 pool（prefix `/pools` + `/operations`）

| #  | 方法   | Python 路径                                | Java 路径                                     | 状态 |
| --- | ------ | ------------------------------------------ | --------------------------------------------- | ---- |
| 11 | POST   | `/pools`                                   | `/pools`                                      | ✅ 已对齐 |
| 12 | GET    | `/pools`                                   | `/pools`                                      | ✅ 已对齐 |
| 13 | GET    | `/pools/{pool_id}`                         | `/pools/{poolId}`                             | ✅ 已对齐 |
| 14 | PATCH  | `/pools/{pool_id}`                         | `/pools/{poolId}`                             | ✅ 已对齐 |
| 15 | DELETE | `/pools/{pool_id}`                         | `/pools/{poolId}`                             | ✅ 已对齐 |
| 16 | POST   | `/pools/{pool_id}/members`                 | `/pools/{poolId}/members`                     | ✅ 已对齐 |
| 17 | DELETE | `/pools/{pool_id}/members`                 | `/pools/{poolId}/members`                     | ✅ 已对齐 |
| 18 | GET    | `/pools/{pool_id}/members`                 | `/pools/{poolId}/members`                     | ✅ 已对齐 |
| 19 | PATCH  | `/pools/{pool_id}/members/{symbol}`        | `/pools/{poolId}/members/{symbol}`            | ✅ 已对齐 |
| 20 | DELETE | `/pools/{pool_id}/members/{symbol}`        | `/pools/{poolId}/members/{symbol}`            | ✅ 已对齐 |
| 21 | GET    | `/pools/by-symbol/{symbol}`                | `/pools/by-symbol/{symbol}`                   | ✅ 已对齐 |
| 22 | POST   | `/pools/{pool_id}/operations`              | `/pools/{poolId}/operations`                  | ✅ 已对齐 |
| 23 | GET    | `/pools/{pool_id}/operations`              | `/pools/{poolId}/operations`                  | ✅ 已对齐 |
| 24 | GET    | `/operations/{op_id}`                      | `/operations/{opId}`                          | ✅ 已对齐 |
| 25 | GET    | `/operations/{op_id}/progress`             | `/operations/{opId}/progress`                 | ✅ 已对齐 |
| 26 | POST   | `/operations/{op_id}/cancel`               | -                                             | ❌ 取消操作，未迁 |

### 3.5 概念 concept（prefix `/concepts`）

| #  | 方法 | Python 路径                          | Java 路径                          | 状态 |
| --- | ---- | ------------------------------------ | ---------------------------------- | ---- |
| 27 | GET  | `/concepts/`                         | `/concepts`                        | ✅ 已对齐 |
| 28 | GET  | `/concepts/by-symbol/{symbol}`       | `/concepts/stock/{symbol}`         | ⚠️ **路径措辞不同**（详见 §4.1） |
| 29 | GET  | `/concepts/tab-by-symbol/{symbol}`   | -                                  | ❌ 概念 Tab 按类型分组，未迁 |
| 30 | GET  | `/concepts/{name}`                   | `/concepts/{code}`                 | ⚠️ **id 命名不同**（详见 §4.2） |
| 31 | POST | `/concepts/sync`                     | -                                  | ❌ 触发概念同步，未迁 |
| 32 | GET  | `/concepts/sync/status`              | `/concepts/sync/status`            | ✅ 已对齐 |

### 3.6 K 线 kline（prefix `/klines`）

| #  | 方法   | Python 路径                          | Java 路径                                | 状态 |
| --- | ------ | ------------------------------------ | ---------------------------------------- | ---- |
| 33 | GET    | `/klines/{symbol}`                   | `/klines/{symbol}`                       | ✅ 已对齐 |
| 34 | GET    | `/klines/{symbol}/stats`             | `/klines/{symbol}/stats`                 | ✅ 已对齐 |
| 35 | GET    | `/klines/{symbol}/{trade_date}`      | `/klines/{symbol}/{tradeDate}`           | ⚠️ **参数命名风格不同**（详见 §4.3） |
| 36 | POST   | `/klines/collect`                    | `/klines/collect`                        | ✅ 已对齐 |
| 37 | POST   | `/klines/collect/batch`              | `/klines/collect/batch`                  | ✅ 已对齐 |
| 38 | DELETE | `/klines/{symbol}`                   | `/klines/{symbol}`                       | ✅ 已对齐 |
| 39 | DELETE | `/klines/{symbol}/{trade_date}`      | `/klines/{symbol}/{tradeDate}`           | ⚠️ 同 35 |

### 3.7 分钟 K 线 minute-kline（prefix `/minute-klines`）

| #  | 方法 | Python 路径                  | Java 路径                    | 状态 |
| --- | ---- | ---------------------------- | ---------------------------- | ---- |
| 40 | GET  | `/minute-klines/{symbol}`    | `/minute-klines/{symbol}`    | ✅ 已对齐 |

### 3.8 采集任务 collect（prefix `/collect`）

| #  | 方法 | Python 路径                          | Java 路径                          | 状态 |
| --- | ---- | ------------------------------------ | ---------------------------------- | ---- |
| 41 | POST | `/collect/tasks`                     | `/collect`                         | ⚠️ **路径风格不同**（详见 §4.4） |
| 42 | GET  | `/collect/tasks`                     | -                                  | ❌ 任务列表，未迁 |
| 43 | GET  | `/collect/tasks/{task_id}`           | -                                  | ❌ 任务详情，未迁 |
| 44 | GET  | `/collect/tasks/{task_id}/progress`  | `/collect/{taskId}/progress`       | ⚠️ 路径风格不同（同 41） |
| 45 | POST | `/collect/tasks/{task_id}/cancel`    | -                                  | ❌ 取消任务，未迁 |

### 3.9 健康检查 health

| #  | 方法 | Python 路径 | Java 路径 | 状态 |
| --- | ---- | ----------- | --------- | ---- |
| -  | GET  | -           | `/health` | 🆕 Java 新增：K8s 探针专用 |

---

## 4. 路径不一致说明

### 4.1 概念反向查询路径措辞

```
Python:  GET /concepts/by-symbol/{symbol}
Java:    GET /concepts/stock/{symbol}
```

**含义相同**（按股票查所属概念），但**路径措辞不同**。

### 4.2 概念 id 命名

```
Python:  GET /concepts/{name}     ← 用 "name"
Java:    GET /concepts/{code}     ← 用 "code"
```

**建议统一用 `code`**（更准确，概念名称可能重复）。

### 4.3 K 线日期参数命名

```
Python:  GET /klines/{symbol}/{trade_date}    ← snake_case
Java:    GET /klines/{symbol}/{tradeDate}     ← camelCase
```

仅占位符命名风格差异，**实际路径表达式不同**（一个用 `_`，一个用驼峰）。

### 4.4 采集任务路径风格

```
Python:  POST /collect/tasks
         GET  /collect/tasks/{task_id}/progress
         POST /collect/tasks/{task_id}/cancel

Java:    POST /collect
         GET  /collect/{taskId}/progress
         (cancel 暂未迁)
```

Python 把任务当**复数子资源** `tasks`，Java 直接用**根路径 `/collect`**（任务本身就是 `/collect` 模块的主表）。

---

## 5. 同步率汇总

| 维度        | 数量 |
| ----------- | ---- |
| 完全对齐    | 19 |
| 部分对齐    | 7   |
| Java 新增   | 2   |
| Python 独有 | 14  |
| 缺口合计    | **14（35%）** |

---

## 6. 缺口分布（按优先级）

### 6.1 P0（核心功能阻塞）

```
POST   /collect                                            # 已有（路径风格不同）
GET    /collect/tasks                                      # 任务列表 ❌
GET    /collect/tasks/{taskId}                             # 任务详情 ❌
POST   /collect/tasks/{taskId}/cancel                      # 取消任务 ❌
```

### 6.2 P1（数据同步）

```
POST   /stocks/sync                                        # 同步股票基本信息 ❌
POST   /stocks/sync-daily-basic                            # 同步日频估值指标 ❌
POST   /concepts/sync                                      # 触发概念同步 ❌
```

### 6.3 P2（管理功能）

```
POST   /stocks/                                            # 新增 / 更新股票 ❌
PATCH  /stocks/{symbol}                                    # 部分更新 ❌
DELETE /stocks/{symbol}                                    # 删除 ❌
POST   /operations/{opId}/cancel                           # 取消池操作 ❌
```

### 6.4 P3（增强）

```
GET    /stocks/                                            # 列表（已 deprecated，由 panel 代理）
GET    /stocks/meta                                        # 枚举值 ❌
GET    /concepts/tab-by-symbol/{symbol}                    # 概念 Tab 分组 ❌
GET    /stocks/{symbol}/analysis                           # AI 归因入口 ❌
```

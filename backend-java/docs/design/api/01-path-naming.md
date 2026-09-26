# 01 · 路径与命名规范

> 本文档是 `00-api-style.md` 中"路径 / HTTP 方法 / 资源命名"承诺的展开。  
> 内容覆盖：路径三段式、模块前缀、资源命名、HTTP 方法分流、路径参数 vs query 参数 vs body、业务扁平化、子资源规则、命名反例。

---

## 1. 路径结构

```
{MODULE}/{RESOURCE}[/{ID}][/{SUB-RESOURCE}][?queryParams]
```

| 段                | 含义                        | 命名风格              |
| ----------------- | --------------------------- | --------------------- |
| `MODULE`          | 业务模块前缀                | 复数或领域名词        |
| `RESOURCE`        | 资源名                      | 复数优先，名词        |
| `{ID}`            | 资源主键                    | 路径参数              |
| `{SUB-RESOURCE}`  | 子资源（必要时存在）        | 仅必要时存在          |
| `?queryParams`    | 过滤/分页/排序参数          | camelCase query 串    |

**嵌套层级**：**优先扁平**，但**允许多层 id 出现**。  
常见多层 id 场景是**复合业务主键**（如 `/{symbol}/{tradeDate}`、`/{poolId}/{symbol}`），以及"进度子视图"（如 `/{id}/progress`）。  
关于何时应该优先扁平、何时保留多层，见第 6 节。

---

## 2. 模块前缀（MODULE）

### 2.1 已规划模块

| 模块              | URL 前缀       | 涵盖业务                              |
| ----------------- | -------------- | ------------------------------------- |
| `stock`           | `/stock/*`     | 个股信息、股票统计                    |
| `pool`            | `/pool/*`      | 股票池                                |
| `pool-member`     | `/pool-member/*` | 股票池成员（**独立资源，非嵌套**）   |
| `pool-operation`  | `/pool-operation/*` | 股票池操作记录（独立资源）       |
| `kline`           | `/kline/*`     | K 线（日 K / 分钟 K）                 |
| `concept`         | `/concept/*`   | 概念（板块）信息                      |
| `concept-member`  | `/concept-member/*` | 概念成员（独立资源）            |
| `collect`         | `/collect/*`   | 采集任务                              |
| `collect-progress`| `/collect-progress/*` | 任务进度（独立资源）           |
| `collect-cancel`  | `/collect-cancel/*` | 取消操作（独立动作资源）         |
| `panel`           | `/panel/*`     | 面板                                  |
| `minute-kline`    | `/minute-kline/*` | 分钟 K（独立模块，区别于日 K）     |
| `health`          | `/health/*`    | 健康检查（K8s 探针）                  |

> 出现"操作进度 / 取消 / 导入任务"等本属于父子操作的资源，**升级为独立模块**，避免路径嵌套。

---

## 3. HTTP 方法与路径模式

| 操作语义       | HTTP 方法 | 路径模式                              | 示例                                       |
| -------------- | --------- | ------------------------------------- | ------------------------------------------ |
| 查询单个       | GET       | `/{module}/{resource}/{id}`           | `GET /stock/info/000001.SZ`                |
| 查询列表       | GET       | `/{module}/{resource}`                | `GET /stock/list`                          |
| 查询统计       | GET       | `/{module}/{resource}/stats`          | `GET /stock/stats`                         |
| 创建           | POST      | `/{module}/{resource}`                | `POST /stock/info`                         |
| 全量替换       | PUT       | `/{module}/{resource}/{id}`           | `PUT /stock/info/000001.SZ`                |
| 部分更新       | PATCH     | `/{module}/{resource}/{id}`           | `PATCH /stock/info/000001.SZ`              |
| 删除           | DELETE    | `/{module}/{resource}/{id}`           | `DELETE /stock/info/000001.SZ`             |
| 触发异步任务   | POST      | `/{task-module}/{resource}`           | `POST /collect/task`                       |
| 查询异步进度   | GET       | `/{progress-module}/{id}`             | `GET /collect-progress/{taskId}`           |
| 取消异步任务   | POST      | `/{cancel-module}/{id}`               | `POST /collect-cancel/{taskId}`            |
| K 线按日期删   | DELETE    | `/{module}/{resource}/{id1}/{id2}`    | `DELETE /kline/000001.SZ/20250925`（复合主键允许多层） |

**详细模块路径见附录 A。**

---

## 4. 路径参数 / Query 参数 / Body 的分流规则

> **核心口诀**：**路径 = 定位**，**query = 过滤**，**body = 内容**。

### 4.1 必须进路径（路径参数）

满足以下**任一**条件：

- 缺了这个值，无法定位资源（单一主键）
- 是**复合业务主键**（由两个或多个字段共同决定唯一性，常见于 K 线、组合关系等场景）

```
GET    /stock/info/{id}                    ← {id} = 股票代码
GET    /pool/{id}                          ← {id} = 池数字 ID
GET    /collect/task/{id}                  ← {id} = 任务数字 ID
DELETE /kline/{symbol}/{tradeDate}         ← {symbol} + {tradeDate} 联合主键（复合）
DELETE /pool-member/{poolId}/{symbol}      ← {poolId} + {symbol} 联合主键（复合）
```

### 4.2 必须进 Query 参数

满足以下**任一**条件：

- 不影响"定位哪个资源"，只影响"过滤/分页/排序"
- 是可选的、可以缺省的过滤维度

| 参数类型     | 示例                                              |
| ------------ | ------------------------------------------------- |
| 业务筛选     | `?industry=银行&exchange=SH&status=active`        |
| 分页         | `?page=1&pageSize=20`                             |
| 排序         | `?sortBy=marketCap&sortDir=desc`                  |
| 时间范围     | `?startDate=2025-01-01&endDate=2025-12-31`        |
| 包含/排除    | `?includeDeleted=false&onlyActive=true`           |
| 反向查询     | `?poolId=123&symbol=000001.SZ`                    |
| 搜索关键字   | `?keyword=平安&fuzzy=true`                        |

### 4.3 必须进 Body

满足以下**任一**条件：

- 是资源的"内容字段"（创建/修改时）
- 是批量操作的明细（数组、嵌套对象）
- 文件上传（multipart/form-data）

```jsonc
// POST /stock/info - 资源内容进 body
{
  "symbol": "000001.SZ",
  "name": "平安银行",
  "industry": "银行"
}

// PATCH /stock/info/{id} - 修改字段进 body
{
  "id": "000001.SZ",
  "name": "平安银行股份有限公司"
}

// POST /pool-member - 关联字段也进 body
{
  "poolId": 123,
  "symbol": "000001.SZ",
  "memo": "重点观察"
}
```

### 4.4 决策树（实现/评审用）

```
这个参数缺了，URL 还能定位到具体资源吗？
│
├── 能 → 这是过滤/分页/排序 → 进 query
│
└── 不能
    │
    ├── 是资源的"内容字段" → 进 body（POST/PUT/PATCH）
    │
    └── 是唯一标识的一部分 → 进路径（GET/DELETE/PUT/PATCH）
```

---

## 5. 命名风格

### 5.1 资源名（resource）

| 规则           | 示例                                            |
| -------------- | ----------------------------------------------- |
| 优先复数       | `members`、`items`、`tasks`                     |
| 单数允许       | 名词本身偏单数 / 抽象概念：`info`、`stats`、`meta` |
| 全部小写       | 禁止驼峰 / 下划线 / 中划线混入路径              |
| 中划线分隔多词 | `pool-member`、`concept-member`、`panel-rule`   |
| 业务相关优先   | `order` 而不是 `record`，`task` 而不是 `job`    |

### 5.2 路径参数（{id}）

| 资源类型        | id 形式                    | 示例                          |
| --------------- | -------------------------- | ----------------------------- |
| 股票            | 股票代码（含交易所后缀）   | `000001.SZ`、`600000.SH`      |
| 股票池          | 数据库数字主键             | `123`、`456`                  |
| 池成员          | 虚拟数字主键               | `789`                         |
| 任务            | 数据库数字主键             | `10001`                       |
| 概念            | 概念代码                   | `BK0001`                      |
| K 线日期        | ISO 日期字符串             | `20250925`                    |

> ⚠️ 注意：股票代码带 `.`，需要在 Spring 配置中保留 `.` 不被剥离：  
> `application.yml` → `spring.mvc.pathmatch.matching-strategy: ant_path_matcher`  
> 并显式声明 `{id:.+}` 形式或使用 `@PathVariable` + 自定义正则。

### 5.3 Query 参数

- 全部使用 **camelCase**：`pageSize`、`sortBy`、`startDate`
- 枚举值小写：`active`、`desc`、`asc`
- 时间格式：`yyyy-MM-dd`（日期）或 `yyyy-MM-dd HH:mm:ss`（时间戳）
- 布尔值：`true` / `false`（小写）

---

## 6. 优先扁平、允许多层 id

### 6.1 原则

> **优先**走扁平：能用 `{module}/{resource}/{id}` 单独定位的，就不要嵌套。  
> **但**允许多层 id 出现：当业务主键是复合字段（`{symbol}/{tradeDate}`），或者"进度子视图"（`{id}/progress`）是只读资源时，保留多层语义更清晰，不必强行扁平化。

> 🔑 **不要教条**。扁平化是为了**操作/缓存/CDN 配置更简单**。  
> 如果扁平化反而**模糊业务含义**（比如给 K 线按日期删建一个虚拟 id），就保留多层。  
> 如果多层表达**子资源从属关系清晰**（进度、取消），就保留。

### 6.2 拆分模式

| 类型           | 嵌套写法（保留）                          | 扁平写法（推荐）                                |
| -------------- | ----------------------------------------- | ----------------------------------------------- |
| 池成员         | `/pool-member/{poolId}/{symbol}`          | `/pool-member/{id}`                            |
| 池成员查询     | `/pool-member?poolId={poolId}`            | `/pool-member?poolId={poolId}`                  |
| 池成员反向     | `/pool-member/by-symbol/{symbol}`         | `/pool-member/by-symbol/{symbol}`              |
| 池操作记录     | `/pool-operation?poolId={poolId}`         | `/pool-operation?poolId={poolId}`               |
| 概念成员       | `/concept-member?conceptCode={code}`      | `/concept-member?conceptCode={code}`           |
| 股票财务       | `/stock-finance/{symbol}?reportDate=2024Q4` | `/stock-finance/{symbol}?reportDate=2024Q4`   |
| 任务进度       | `/collect/task/{id}/progress`             | `/collect-progress/{taskId}`                    |
| 取消任务       | `/collect/task/{id}/cancel`               | `/collect-cancel/{taskId}`                      |

### 6.3 何时优先扁平、何时保留嵌套

| 问题                                       | 优先扁平           | 保留多层              |
| ------------------------------------------ | ------------------ | --------------------- |
| 是否有独立的虚拟主键？                     | 有 → 扁平          | 没有 → 复合主键时保留  |
| 仅靠父子组合才能唯一定位吗？                | 否 → 扁平          | 是 → 保留             |
| 删除/更新时，是否能只引用子资源？           | 能 → 扁平          | 不能 → 保留           |
| 是只读进度/状态子视图？                     | -                  | 是 → 保留             |

### 6.4 数据库要求（实施扁平化时）

实施扁平化前，**子表必须存在稳定的虚拟主键 `id`**：

```sql
-- pool_member：原本用 (pool_id, symbol) 复合主键，需补一个 id 自增列
ALTER TABLE pool_member ADD COLUMN id BIGINT AUTO_INCREMENT PRIMARY KEY;

-- pool_operation：原本用复合键同理
ALTER TABLE pool_operation ADD COLUMN id BIGINT AUTO_INCREMENT PRIMARY KEY;
```

> 数据库迁移脚本见后续 `rebuild/08-db-migration.md`（待编写）。

### 6.5 多层 id 常见场景

以下场景**保留多层**：

| 路径                                       | 类别              | 理由                                 |
| ------------------------------------------ | ----------------- | ------------------------------------ |
| `/kline/{symbol}/{tradeDate}`              | 复合主键          | 业务主键天然是两个字段组合            |
| `/pool-member/{poolId}/{symbol}`           | 复合主键          | 联合主键无独立虚拟主键                |
| `/pool-operation/{id}/progress`           | 进度子视图        | 只读进度，强业务从属关系               |
| `/collect/task/{id}/progress`              | 进度子视图        | 同上                                  |
| `/pool-operation/{id}/cancel`              | 取消子动作        | 动作型子资源，与进度同级               |
| `/collect/task/{id}/cancel`                | 取消子动作        | 同上                                  |

> 这些都是**业务语义驱动**的多层：复合主键不可拆、进度/取消强从属。  
> **不要为了"看起来扁平"硬拆**：给 K 线按日期删硬造一个虚拟 id，反而把 URL 语义搞坏。

---

## 7. 模块级路径清单

### 7.1 股票（stock）

```
GET    /stock/info/{id}                   # 查单个股票信息
GET    /stock/list                        # 列表（分页 + 筛选）
GET    /stock/stats                       # 统计

POST   /stock/info                        # 新增
PUT    /stock/info/{id}                   # 全量修改
PATCH  /stock/info/{id}                   # 部分修改
DELETE /stock/info/{id}                   # 删除
```

### 7.2 股票池（pool + pool-member + pool-operation）

```
GET    /pool/list                         # 池列表
GET    /pool/{id}                         # 池详情
POST   /pool                              # 创建池
PUT    /pool/{id}                         # 改池
DELETE /pool/{id}                         # 删池

GET    /pool-member/{id}                  # 成员详情
GET    /pool-member?poolId={id}           # 某池的成员列表
GET    /pool-member/by-symbol/{symbol}    # 某股票所属的池
GET    /pool-member/{poolId}/{symbol}     # 复合主键：直接按池+股票定位成员（保留多层）
POST   /pool-member                       # 加成员（body: {poolId, symbol, memo}）
PATCH  /pool-member/{id}                  # 改成员备注
DELETE /pool-member/{id}                  # 删成员
DELETE /pool-member/{poolId}/{symbol}     # 复合主键：直接按池+股票删除（保留多层）

GET    /pool-operation/{id}               # 某操作详情
GET    /pool-operation?poolId={id}        # 某池的操作记录
GET    /pool-operation/{id}/progress      # 操作进度（保留多层，只读进度子视图）
POST   /pool-operation                    # 创建操作（body: {poolId, type, ...}）
POST   /pool-operation/{id}/cancel        # 取消操作（保留多层，子动作）
```

> 注：  
> - 池成员的复合主键（`{poolId}/{symbol}`）和虚拟主键（`{id}`）**两种定位方式都提供**，由前端按场景选择。  
> - `/pool-operation/{id}/progress` 是"进度查询"操作，**只读**，保留多层以保证业务语义清晰。  
> - `/pool-operation/{id}/cancel` 是子动作资源，与进度同级，保留多层。

### 7.3 K 线（kline + minute-kline）

```
GET    /kline/{symbol}                    # 查 K 线（query: startDate, endDate, period）
GET    /kline/{symbol}/stats               # K 线统计
DELETE /kline/{symbol}                    # 删某股票全部 K 线
DELETE /kline/{symbol}/{tradeDate}        # 复合主键：删某日 K 线（保留多层）

GET    /minute-kline/{symbol}             # 同上但分钟级
DELETE /minute-kline/{symbol}/{tradeDate} # 复合主键：删某分钟 K 线（保留多层）
```

### 7.4 概念（concept + concept-member）

```
GET    /concept/list                      # 概念列表
GET    /concept/{code}                    # 概念详情

GET    /concept-member?conceptCode={code} # 概念成员
GET    /concept-member/by-symbol/{symbol} # 反向查
POST   /concept-member                    # 加成员
DELETE /concept-member/{id}               # 删成员

POST   /concept-sync                       # 触发同步
GET    /concept-sync/status                # 同步状态
```

### 7.5 采集任务（collect + collect-progress + collect-cancel）

```
POST   /collect/task                       # 创建采集任务
GET    /collect/task/list                  # 任务列表
GET    /collect/task/{id}                  # 任务详情
GET    /collect/task/{id}/progress         # 进度（保留多层，只读进度子视图）
POST   /collect/task/{id}/cancel           # 取消任务（保留多层，子动作）

POST   /collect-cancel/{taskId}            # 取消任务（独立动作资源，与上等价）
GET    /collect-progress/{taskId}          # 进度（独立资源，与上等价）
```

> 同一含义可由"嵌套子动作"和"独立模块"两种方式表达，**团队选一种风格保持一致**（推荐用嵌套，更直观）。

### 7.6 面板（panel）

```
GET    /panel/stock                        # 股票面板
GET    /panel/stock/{id}                   # 单只股票面板
```

### 7.7 健康检查（health）

```
GET    /health                              # 综合健康检查
GET    /health/ready                        # K8s readiness 探针
GET    /health/live                         # K8s liveness 探针
```

---

## 8. 命名反例（禁止）

| 反例                                              | 原因                                       |
| ------------------------------------------------- | ------------------------------------------ |
| `/stock/getStockInfo`                             | 动词重复，HTTP 方法已经表达了"get"          |
| `/stock/listStockInfo?page=2`                     | 路径里再次出现 "list"，应改 `/stock/list`  |
| `/pool/{poolId}/member/{symbol}`                   | 嵌套了两层，违反扁平化原则                  |
| `/stock/list/industry/银行/exchange/SH`           | 把过滤条件塞进路径，会导致 URL 组合爆炸     |
| `/stock/info/page/2/size/20/sort/name`            | 分页、排序不应进路径                        |
| `/stock/delete/info/{id}`                         | 动词不应进路径，HTTP DELETE 已表达          |
| `/Stock/Info`                                     | 大小写敏感会出错，必须全小写                |
| `/stock_info/{id}`                                | 资源名不应使用下划线，统一中划线            |

---

## 9. 评审 checklist（路径规范部分）

- [ ] 模块前缀列表（第 2.1 节）覆盖现有所有 controller
- [ ] HTTP 方法分流（第 3 节）符合业务语义
- [ ] 路径/query/body 分流规则（第 4 节）无歧义
- [ ] 命名风格（第 5 节）可在团队内统一执行
- [ ] 优先扁平的拆分思路（第 6 节）逻辑闭环：所有"看起来要嵌套的"都有取舍依据
- [ ] 多层 id 场景（第 6.5 节）覆盖：复合主键 + 进度子视图 + 取消子动作
- [ ] 第 7 节模块清单完整覆盖 stock / pool / kline / concept / collect / panel / health

---

## 10. 变更记录

| 版本 | 日期       | 变更人 | 变更内容                                                |
| ---- | ---------- | ------ | ------------------------------------------------------- |
| v0.2 | 2026-09-25 | -      | 允许多层 id：复合主键、进度子视图、取消子动作都保留多层   |
| v0.1 | 2026-09-25 | -      | 初稿，待评审                                            |

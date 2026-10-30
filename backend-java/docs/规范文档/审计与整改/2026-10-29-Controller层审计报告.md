# 分层整改报告（2026-10-29 · Controller 层）

> **归档文档，勿修改。**
> 本文件是 2026-10-29 Controller 层审计的**一次性快照**，记录审计时的真实数字。
> 规范本体见 `../纵向分层规范/Controller层规范.md`——那里只写规则，不含任何计数。

> 排查时间：2026-10-29　范围：`backend-java` 全部 17 个 Controller、89 个接口方法

---

## 1. 总览

| 检查项 | 现状 | 目标 | 状态 |
|---|---|---|---|
| Controller 文件数 | 17 | — | — |
| 接口方法数（mapping 注解） | 89 | — | — |
| 返回 `ApiResponse<?>`（放弃类型） | **83** | 0 | ⬜ 待整改 |
| 返回 `ApiResponse<T>`（泛型具体） | **1**（`CollectLogController`，唯一范例）| 全部 | ⬜ 待整改 |
| `@PathVariable` 未显式命名 | **48** | 0 | ⬜ 待整改 |
| `@PathVariable` 已显式命名 | 13 | — | — |
| Controller 内手工 `query.setXxx` | **51**（8 个文件） | 0（改 `@ModelAttribute`）| ⬜ 待整改 |
| 手拼 `Map.of("message", ...)` 响应 | **9** | 0 | ⬜ 待整改 |
| Controller 内业务判断 | 1（`StockController.syncDailyBasic`）| 0 | ⬜ 待整改 |
| Controller 直接注入 `CollectorService` 并拼 params | **3 个 Controller / 5 个方法** | 0 | ⬜ 待整改 |
| 手写 `Authorization` 头提取 | 4（`AuthController`×3 / `AuthCompatController`×1）| 集中到拦截器 | ⬜ 待整改 |
| `@Valid @RequestBody` 使用 | ✅ 已全面应用 | — | ✅ |
| 响应体结构 `{code,message,data}` | ✅ 全项目统一 | — | ✅ |

---

## 2. `ApiResponse<?>` 分布（83 处）

| Controller | 数量 | 备注 |
|---|---|---|
| `DataBoardController` | 19 | 全部是查询接口，可直接写成 `ApiResponse<XxxVO>` |
| `PoolController` | 16 | 混合查询 / 写操作 |
| `AuthController` | 10 | |
| `ConceptQueryController` | 7 | |
| `KlineController` | 7 | 含 2 个 collector 触发接口（`collect` / `collect/batch`）|
| `StockController` | 7 | 含 2 个 collector 触发接口（`sync` / `syncDailyBasic`）|
| `UserController` | 5 | |
| `ConceptBoardController` | 3 | |
| `AuthCompatController` | 2 | |
| `ConceptQuoteController` | 2 | |
| `MinuteKlineController` | 1 | |
| `PanelController` | 1 | |
| `PermissionController` | 1 | |
| `RoleController` | 1 | |
| `StockAnalysisController` | 1 | |
| `CollectProxyController` | 0 | 豁免（`ResponseEntity<Map>`）|
| `CollectLogController` | 0 | ✅ 已是 `ApiResponse<PageResult<CollectLogVO>>`（唯一范例）|

> ✅ **唯一正确范例**：`CollectLogController` 用 `ApiResponse<PageResult<CollectLogVO>>`——改造时以它为模板。

---

## 3. Controller 内业务判断 / 编排

| 位置 | 问题 | 应改为 |
|---|---|---|
| `StockController.syncDailyBasic` | Controller 里 `if (trade_date == null)` 并自己拼 `Map` 响应 | 下沉 Service，返回 `XxxVO` |
| `KlineController.collect` | Controller 拼 collector `params`（`symbols` / `days` / `start_date`）| 下沉 Service |
| `KlineController.collect/batch` | 同上 | 下沉 Service |
| `StockController.sync` / `syncDailyBasic` | Controller 拼 collector `params` | 下沉 Service |
| `MinuteKlineController.get` | Controller 内做 `instanceof` 拆包 + 逐字段 `set`（**纯数据搬运**）| 下沉 Service，Controller 只收 VO |

> ⚠️ `MinuteKlineController` 是最严重的越界案例：它在 Controller 里完成了「外部响应 → VO」的完整转换，
> 违反 POJO 规范 §4.3「转换发生在 Service 层」。

---

## 4. 参数绑定问题

| 问题 | 数量 | 说明 |
|---|---|---|
| `@PathVariable` 未命名 | 48 | 依赖 `-parameters` 编译参数，脆弱 |
| 手工 `query.setXxx` | 51 | `PanelController` 13、`ConceptBoardController` 14、`CollectLogController` 5、`ConceptQueryController` 4、`KlineController` 4、`UserController` 4、`DataBoardController` 4、`PoolController` 3 |
| `page` / `page_size` clamp 分散 | 8 处 | `Math.max(page,1)` / `Math.min(Math.max(pageSize,1), 500)` 散落各处，上限还不统一（100 / 200 / 500）|

---

## 5. 路径风格不统一

| 现象 | 位置 |
|---|---|
| 类级 `@RequestMapping("/api/pools")` + 方法级 `@GetMapping("/")` | `UserController` / `RoleController` / `PermissionController` / `PanelController` / `ConceptQueryController` |
| 类级 `@RequestMapping("/api")` + 方法级 `@PostMapping("/pools")` | `PoolController`（资源路径写在方法上）|
| 类级 `@RequestMapping("/api/stocks")` + 方法级 `@PostMapping("/")` | `StockController` |
| 类级 `@RequestMapping("/api/collect/logs")` + 方法级 `@GetMapping`（无斜杠）| `CollectLogController` |

> 四种风格并存。建议统一为：**类级 `@RequestMapping` 写完整资源路径（不带尾斜杠），方法级用相对路径或空串**。

---

## 6. 已是正解的部分（保持）

| 项 | 说明 |
|---|---|
| `@Valid @RequestBody` | 全项目 `@RequestBody` 均带 `@Valid`，校验失败统一 422 + 全部字段错误 |
| `ApiResponse.ok/created` | 响应结构 `{code,message,data}` 全项目统一，前端拦截器零改动 |
| `GlobalExceptionHandler` | `BusinessException` → 对应 HTTP 状态码；校验失败 → 422；兜底 → 500 不泄漏堆栈 |
| `BusinessException(code, msg)` | Service 用 `code` 表达 404 / 401 / 403 等语义，Controller 无需感知 |
| `PageResult<T>` | 分页出参统一 `PageResult<XxxVO>`，无自定义字段名 |

---

## 7. 整改落地路径（2026-10-29 制定）

| 阶段 | 内容 | 风险 |
|---|---|---|
| **P0** | `StockController.syncDailyBasic` 业务判断下沉 Service | 低 |
| **P0** | `MinuteKlineController` 转换逻辑下沉 Service（Controller 只收 VO）| 中 |
| **P1** | `ApiResponse<?>` → `ApiResponse<XxxVO>`（83 处，分批改）| 中（响应体结构不变，前端零改动）|
| **P1** | 手拼 `Map` 响应 → `ApiResponse<Void>` / 新 VO（9 处）| 中（前端若读 `data.message` 需同步）|
| **P1** | Controller 直连 `CollectorService` 的 3 处下沉 Service | 中 |
| **P2** | `@PathVariable` 显式命名（48 处）| 极低 |
| **P2** | 路径风格统一（4 种 → 1 种）| 中（改路径需同步前端 + 文档）|
| **P3** | `@ModelAttribute` 替代手工 Query 装配（51 处）| 中 |
| **P3** | page/pageSize clamp 收敛到 Query 基类 | 低 |
| **P4** | `Authorization` 提取集中到拦截器 / 参数解析器 | 中 |

---

> **本报告是一次性审计快照，数字反映 2026-10-29 的代码状态，后续不再更新。**
> 规范本体见 `../纵向分层规范/Controller层规范.md`。

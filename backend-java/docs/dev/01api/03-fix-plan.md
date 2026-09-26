# 03 · 修改方案

> 配套文档：
> - 接口对照：`01-api-mapping.md`
> - 不符合规范点：`02-non-compliance.md`
> - 规范来源：`docs/design/api/01-endpoint-spec.md` / `02-response-spec.md`
>
> 本文档**只列修改方案，不动代码**，等你确认后再实施。

---

## 1. 总览

按 P0 / P1 / P2 三档分组，**P0 必须改**、**P1 应该改**、**P2 视情况**：

| 档位 | 任务数 | 总估时       | 说明 |
| ---- | ------ | ------------ | ---- |
| P0   | 5      | ~1.5 天      | 响应封装 + 异常机制 + Controller 改业务异常 |
| P1   | 6      | ~3 天        | 缺失接口补齐 + 路径命名统一 + 分页参数统一 + VO 统一 |
| P2   | 4      | ~2 天        | 管理类接口补齐 + AI 归因 |

---

## 2. P0（响应封装 + 异常机制）

### 2.1 删 `ApiResponse.fail()`

**位置**：`backend-java/src/main/java/com/attribution/dto/response/ApiResponse.java:58-64`

**改动**：
- 删除 `fail(String)` 方法。
- 删除 `@Deprecated` 不适用，**直接删**。

**影响**：唯一调用方是 `CollectController.getProgress`，改抛异常即可。

### 2.2 删 / Deprecated `ApiResponse.error()`

**位置**：`backend-java/src/main/java/com/attribution/dto/response/ApiResponse.java:50-56`

**改动（方案 A，直接删）**：
- 删除 `error(int, String)` 方法。

**改动（方案 B，标记 Deprecated）**：
```java
@Deprecated(since = "3.0", forRemoval = true)
public static <T> ApiResponse<T> error(int code, String message) { ... }
```

**推荐**：方案 A（直接删）。

### 2.3 重写 `GlobalExceptionHandler.handleBusiness`

**位置**：`backend-java/src/main/java/com/attribution/exception/GlobalExceptionHandler.java:19-25`

**改动**：
- 引入新的 `ErrorResponse.ofBiz(int httpStatus, String bizCode, String humanMessage)` 静态方法。
- handler 调用 `ofBiz` 替代 `of(int, String, Object)`。

**新增方法**：

```java
public static ErrorResponse ofBiz(int httpStatus, String bizCode, String humanMessage) {
    return ErrorResponse.builder()
            .code(httpStatus)
            .message(bizCode)          // 业务错误码字符串，如 "STOCK_NOT_FOUND"
            .data(humanMessage)         // 人话消息，如 "股票不存在: 000001.SZ"
            .build();
}
```

**改动后 handler**：

```java
@ExceptionHandler(BusinessException.class)
public ResponseEntity<ErrorResponse> handleBusiness(BusinessException ex) {
    return ResponseEntity
            .status(ex.getHttpStatus())
            .body(ErrorResponse.ofBiz(ex.getHttpStatus(), ex.getCode(), ex.getMessage()));
}
```

### 2.4 重构 `BusinessException`，停止拼接 message

**位置**：`backend-java/src/main/java/com/attribution/exception/BusinessException.java:40, 46-51`

**改动**：
- `super(message)` 替代 `super(format(module, code, message))`。
- 删除 `format()` 私有方法。
- `getMessage()` 返回的就是**纯人话消息**（无方括号）。

**改动后**：

```java
public BusinessException(String module, String code, String message, int httpStatus) {
    super(message);    // 直接存人话消息
    this.module = module;
    this.code = code;
    this.httpStatus = httpStatus;
}
```

> ⚠️ `getMessage()` 行为变了，要确认无其他代码依赖"`[module]-[code]-[msg]`"格式的字符串。grep 后无业务代码依赖。

### 2.5 `CollectController.getProgress` 改抛异常

**位置**：`backend-java/src/main/java/com/attribution/controller/CollectController.java:41-43`

**改动**：

```java
// 旧
if (progress == null) {
    return ResponseEntity.ok(ApiResponse.fail("任务不存在"));
}

// 新
if (progress == null) {
    throw new BusinessException("collect", "TASK_NOT_FOUND", "任务不存在: " + taskId, 404);
}
```

---

## 3. P1（缺失接口 + 命名 + 分页 + VO 统一）

### 3.1 补齐 `CollectController` 缺失接口

**位置**：`backend-java/src/main/java/com/attribution/controller/CollectController.java`

**新增接口**：

```java
@GetMapping("/tasks")
@Operation(summary = "任务列表")
public ResponseEntity<ApiResponse<PageResponse<SysCollectTaskVO>>> listTasks(
        @RequestParam(defaultValue = "kline_daily") String taskType,
        @RequestParam(required = false) String status,
        @RequestParam(defaultValue = "20") @Min(1) @Max(100) Integer limit,
        @RequestParam(defaultValue = "0") @Min(0) Integer offset) { ... }

@GetMapping("/tasks/{taskId}")
@Operation(summary = "任务详情")
public ResponseEntity<ApiResponse<SysCollectTaskVO>> getTask(
        @PathVariable Long taskId,
        @RequestParam(defaultValue = "kline_daily") String taskType) { ... }

@PostMapping("/tasks/{taskId}/cancel")
@Operation(summary = "取消任务")
public ResponseEntity<ApiResponse<Void>> cancelTask(
        @PathVariable Long taskId,
        @RequestParam(defaultValue = "false") Boolean force) { ... }
```

> 路径风格建议沿用 Java 现状 `/collect/tasks/{taskId}/...`（与 Python 风格有差异，但前端已按 Java 调用）。

### 3.2 补齐 `StockController` 同步接口

**位置**：`backend-java/src/main/java/com/attribution/controller/StockController.java`

**新增接口**：

```java
@PostMapping("/sync")
@ResponseStatus(HttpStatus.CREATED)
@Operation(summary = "同步股票基本信息")
public ResponseEntity<ApiResponse<Void>> syncStockBasics() { ... }

@PostMapping("/sync-daily-basic")
@ResponseStatus(HttpStatus.CREATED)
@Operation(summary = "同步日频估值指标")
public ResponseEntity<ApiResponse<Void>> syncDailyBasic(
        @RequestParam(required = false) String tradeDate) { ... }
```

### 3.3 补齐 `ConceptController` 缺失接口

**位置**：`backend-java/src/main/java/com/attribution/controller/ConceptController.java`

**新增接口**：

```java
@PostMapping("/sync")
@ResponseStatus(HttpStatus.CREATED)
@Operation(summary = "触发概念同步")
public ResponseEntity<ApiResponse<Void>> syncConcepts(
        @RequestParam(required = false) String source,
        @RequestParam(defaultValue = "false") Boolean full) { ... }

@GetMapping("/tab-by-symbol/{symbol}")
@Operation(summary = "股票所属概念 Tab（按类型分组）")
public ResponseEntity<ApiResponse<List<ConceptTabVO>>> getStockConceptTabs(
        @PathVariable String symbol) { ... }
```

### 3.4 补齐 `OperationController.cancel`

**位置**：`backend-java/src/main/java/com/attribution/controller/OperationController.java`

**确认状态**：当前 `OperationController` 已有 `POST /operations/{opId}/cancel`（第 37 行），**无需新增**。仅在 `01-api-mapping.md` 标注的状态为"差 1"，实际**已对齐**。

### 3.5 `PanelController` 分页参数改为 `limit + offset`

**位置**：`backend-java/src/main/java/com/attribution/controller/PanelController.java:30-31`

**改动**：

```java
// 旧
@RequestParam(defaultValue = "1") int page,
@RequestParam(defaultValue = "20") int size,

// 新
@RequestParam(defaultValue = "20") @Min(1) @Max(500) Integer limit,
@RequestParam(defaultValue = "0") @Min(0) Integer offset,
```

**对应 VO**：`StockPanelResponse` 已含 `page + size`，**保留即可**（响应里仍回传 `page + size`，与查询参数解耦）。

### 3.6 `ConceptController.list` 改为分页

**位置**：`backend-java/src/main/java/com/attribution/controller/ConceptController.java:24-29`

**改动**：

```java
// 旧
public ResponseEntity<ApiResponse<List<ConceptBriefVO>>> list(
        @RequestParam(required = false) String source) {
    return ResponseEntity.ok(ApiResponse.ok(conceptService.getAllConcepts(source)));
}

// 新
public ResponseEntity<ApiResponse<PageResponse<ConceptBriefVO>>> list(
        @RequestParam(required = false) String source,
        @RequestParam(defaultValue = "100") @Min(1) @Max(500) Integer limit,
        @RequestParam(defaultValue = "0") @Min(0) Integer offset) {
    return ResponseEntity.ok(ApiResponse.ok(conceptService.getConceptsPaged(source, limit, offset)));
}
```

---

## 4. P2（管理类 + AI 归因）

### 4.1 补 `StockController` CRUD

**位置**：`backend-java/src/main/java/com/attribution/controller/StockController.java`

**新增接口**：

```java
@PostMapping
@ResponseStatus(HttpStatus.CREATED)
@Operation(summary = "新增 / 更新股票")
public ResponseEntity<ApiResponse<StockDetailVO>> upsertStock(
        @Valid @RequestBody StockUpsertRequest request) { ... }

@PatchMapping("/{symbol}")
@Operation(summary = "部分更新股票")
public ResponseEntity<ApiResponse<StockDetailVO>> patchStock(
        @PathVariable String symbol,
        @Valid @RequestBody StockPatchRequest request) { ... }

@DeleteMapping("/{symbol}")
@Operation(summary = "删除股票")
public ResponseEntity<ApiResponse<Void>> deleteStock(@PathVariable String symbol) { ... }
```

### 4.2 路径命名不一致（概念、K 线、采集）

| 位置                                                                 | 改动 | 说明 |
| -------------------------------------------------------------------- | ---- | ---- |
| `controller/ConceptController.java:37` (`/stock/{symbol}`)            | **不改** | Java 端更简洁，Python 端加兼容即可 |
| `controller/ConceptController.java:31` (`/{code}`)                   | **不改** | Java 用 `code` 更准确，Python 端按需调整 |
| `controller/KlineController.java:67, 104` (`{tradeDate}`)            | **不改** | Java 端 camelCase 符合规范 |
| `controller/CollectController.java:17` (`/api/v1/collect`)            | **不改** | Java 风格更清晰 |

> 这 4 处是 Python vs Java 的风格差异，不是 bug，**保持现状**即可。

### 4.3 补 AI 归因接口

**位置**：新建 `controller/StockAnalysisController.java`

```java
@RestController
@RequestMapping("/api/v1/stocks")
@Tag(name = "AI 归因")
public class StockAnalysisController {

    @GetMapping("/{symbol}/analysis")
    @Operation(summary = "股票归因分析（AI 入口）")
    public ResponseEntity<ApiResponse<StockAnalysisVO>> analyzeStock(
            @PathVariable String symbol,
            @RequestParam(required = false) String tradeDate) { ... }
}
```

### 4.4 分页 VO 字段统一

**当前 4 个 VO**：

| VO 类                  | 字段                              | 建议 |
| ---------------------- | --------------------------------- | ---- |
| `PoolListVO`           | `total, items`                    | 改为 `PageResponse<PoolVO>` |
| `PoolMemberListVO`     | `poolId, total, items`            | 改为 `PageResponse<PoolMemberVO>` + 业务字段 `poolId` 放 query |
| `PoolOperationListVO`  | `poolId, total, items`            | 同上 |
| `StockPanelResponse`   | `rows, total, page, size, tradeDate` | 保留（多 `tradeDate` 业务字段），`rows` 改 `items` |

**改动**：
- `PoolListVO` → 替换为 `PageResponse<PoolVO>`。
- `PoolMemberListVO` / `PoolOperationListVO` → 拆为 `PageResponse<...>` + 业务字段。
- `StockPanelResponse.rows` → 改 `items`，**保留** `tradeDate`。

---

## 5. 总修改清单

### 5.1 修改类

| 文件                                                                 | 改动类型 |
| -------------------------------------------------------------------- | -------- |
| `dto/response/ApiResponse.java`                                      | 删除 `fail()` 和 `error()` 方法 |
| `dto/response/ErrorResponse.java`                                    | 新增 `ofBiz(...)` 静态方法 |
| `exception/BusinessException.java`                                   | 停止拼接 message |
| `exception/GlobalExceptionHandler.java`                              | 用 `ofBiz` 替代 `of(int, String, Object)` |
| `controller/CollectController.java`                                  | 改抛业务异常 |
| `controller/PanelController.java`                                    | 分页参数改 `limit + offset` |
| `controller/ConceptController.java`                                  | 列表加分页 |
| `dto/pool/PoolListVO.java`                                           | 替换为 `PageResponse<PoolVO>` 或保留并加 `page + size` |
| `dto/pool/PoolMemberListVO.java`                                     | 同上 |
| `dto/operation/PoolOperationListVO.java`                              | 同上 |
| `dto/StockPanelResponse.java`                                        | `rows` 改 `items` |

### 5.2 新增类

| 文件                                                                                | 用途 |
| ----------------------------------------------------------------------------------- | ---- |
| `controller/StockAnalysisController.java`                                           | AI 归因接口 |
| （可选）`exception/BizCodeException.java`                                           | 特殊解耦场景独立异常类 |
| （可选）`exception/GlobalExceptionHandler.java` 内新增 `handleBizCode`               | 特殊解耦处理器 |

---

## 6. 工时估算

| 档位 | 任务                                    | 工时估 |
| ---- | --------------------------------------- | ------ |
| P0   | 删 `fail()` / `error()`、重写 handler   | 0.5 天 |
| P0   | 重构 `BusinessException.format()`        | 0.5 天 |
| P0   | `CollectController.getProgress` 改抛异常 | 0.5 天 |
| P1   | 补 `collect` 3 个接口                   | 1 天   |
| P1   | 补 `stock/sync` 2 个接口                | 1 天   |
| P1   | 补 `concept/sync` + `tab-by-symbol`     | 1 天   |
| P1   | PanelController / ConceptController 分页改 `limit+offset` | 0.5 天 |
| P2   | 补 `StockController` CRUD               | 1 天   |
| P2   | 补 AI 归因接口                          | 2 天   |
| P2   | 4 个分页 VO 字段统一                    | 0.5 天 |
| **合计** |                                         | **~8 天** |

---

## 7. 风险与注意

| 风险 | 说明 | 缓解 |
| ---- | ---- | ---- |
| 字段命名变化影响前端 | `rows` 改 `items`、分页参数改 `limit+offset` 都会影响前端解析 | 文档明确，团队通知 |
| 路径风格差异（Python vs Java）| Python 用 `/collect/tasks`，Java 用 `/collect` | Java 端维持现状，Python 端不动 |
| 业务异常 message 行为变化 | `getMessage()` 从 `"[m]-[c]-[msg]"` 变为纯 `msg` | 确认无其他代码依赖拼接格式 |
| `PoolListVO` 字段移除影响前端 | 当前返回 `{total, items}`，改为 `PageResponse` 后多 `page + size` 字段，前端兼容 | 前端可选忽略新字段 |

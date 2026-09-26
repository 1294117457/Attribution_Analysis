# 02 · 不符合规范点（Java 工程现状）

> 依据 `docs/design/api/01-endpoint-spec.md`（接口规范）与 `02-response-spec.md`（统一返回参），列出当前 Java 工程中所有不符合规范的代码位置与具体问题。  
> 配套修改方案见 `03-fix-plan.md`。

---

## 1. 问题分类概览

| 类别 | 数量 | 优先级 |
| ---- | ---- | ------ |
| **响应封装违规** | 4 | P0 |
| **路径命名不一致** | 4 | P1 |
| **分页参数风格不一致** | 2 | P1 |
| **业务异常机制缺陷** | 3 | P0 |
| **业务方自定义 VO 不统一** | 4 | P1 |

---

## 2. 响应封装违规（P0）

### 2.1 `HealthController` 返回裸 Map

**位置**：`backend-java/src/main/java/com/attribution/controller/HealthController.java:19`

```java
public ResponseEntity<Map<String, Object>> health() {
    return ResponseEntity.ok(Map.of(
            "status", "ok",
            "version", "3.0.0"
    ));
}
```

**问题**：
- 返回类型是 `Map<String, Object>`，**不**走 `ApiResponse` 封装。
- 违反 `02-response-spec.md §9` "必须返回 ApiResponse<T>"。

**说明**：
- 这是 K8s 探针专用接口。规范**第 10 节**明确允许此例外。
- 当前实现**符合规范**（作为唯一例外保留），**无需修改**。
- 仅作为记录，告知评审者这是**有意保留**而非疏漏。

### 2.2 `ApiResponse.fail()` 写死 `code = 404`，但 HTTP 头是 200

**位置**：`backend-java/src/main/java/com/attribution/dto/response/ApiResponse.java:58-64`

```java
public static <T> ApiResponse<T> fail(String message) {
    return ApiResponse.<T>builder()
            .code(404)              // ← 写死
            .message(message)
            .data(null)
            .build();
}
```

**调用方**：`backend-java/src/main/java/com/attribution/controller/CollectController.java:42`

```java
return ResponseEntity.ok(ApiResponse.fail("任务不存在"));
```

**问题**：
- body 是 `{code: 404, message: "任务不存在", data: null}`
- HTTP 头是 **200**
- **`code` 与 HTTP 状态码不一致**，违反 `02-response-spec.md §1` 默认规则。
- **`fail` 方法名误导**：暗示"失败"但只支持"找不到"（404），无法表达 400/403/500 等其他错误。
- 前端用 `fetch`/axios 默认**不会进入 catch 分支**（HTTP 200），必须读 body 才能识别错误，**判定逻辑分散**。

**修复方向**（详见 `03-fix-plan.md`）：
- 删 `ApiResponse.fail()` 方法
- Controller 改抛 `BusinessException`，由 `GlobalExceptionHandler` 统一处理

### 2.3 `ApiResponse.error()` 不应该被 Controller 直接使用

**位置**：`backend-java/src/main/java/com/attribution/dto/response/ApiResponse.java:50-56`

```java
public static <T> ApiResponse<T> error(int code, String message) {
    return ApiResponse.<T>builder()
            .code(code)
            .message(message)
            .data(null)
            .build();
}
```

**问题**：
- 当前**无人调用**（已确认），但**方法存在**，给"偷懒"留口子。
- 违反 `02-response-spec.md §9` "不允许直接构造 ErrorResponse"。
- 业务错误**必须**走 `GlobalExceptionHandler` 统一处理。

**修复方向**：
- 将 `ApiResponse.error()` 标记为 `@Deprecated` 或直接删除。

### 2.4 `ErrorResponse.handleBusiness` 字段语义与命名不一致

**位置**：`backend-java/src/main/java/com/attribution/exception/GlobalExceptionHandler.java:24`

```java
.body(ErrorResponse.of(ex.getHttpStatus(), ex.getCode(), ex.getMessage()));
```

**实际数据流向**：

| ErrorResponse 字段 | 实际来源                          | 期望（按字段名暗示）      |
| ------------------ | --------------------------------- | ------------------------- |
| `code`             | HTTP 状态码（404）                | 状态码或业务码            |
| `message`          | 业务错误码字符串（"STOCK_NOT_FOUND"） | 人话消息                |
| `data`             | 真正的异常 message（带方括号格式） | 结构化错误详情            |

**问题**：
- `ErrorResponse.message` 拿到的是 `"STOCK_NOT_FOUND"`，**不是给人看的**。
- `ErrorResponse.data` 拿到的是 `"[stock]-[STOCK_NOT_FOUND]-[股票不存在]"`，**带方括号的格式化字符串**，前端展示给用户不合适。
- 前端按"`message` 是错误消息"理解会困惑——只能按"`data` 才是 message"理解，**视觉欺骗**。
- 异常 message 经过 `BusinessException.format()` 拼装为 `[module]-[code]-[msg]`，**已经自带冗余信息**（code 字段就是同样的"STOCK_NOT_FOUND"）。

**修复方向**（详见 `03-fix-plan.md`）：
- 加 `ErrorResponse.ofBiz(int httpStatus, String bizCode, String humanMessage)` 具名方法，让意图清晰。
- `message` 装**业务错误码字符串**（如 `STOCK_NOT_FOUND`），`data` 装**人话消息**（如 `股票不存在: 000001.SZ`）。

---

## 3. 路径命名不一致（P1）

### 3.1 概念反向查询路径措辞

**位置**：`backend-java/src/main/java/com/attribution/controller/ConceptController.java:37`

```java
@GetMapping("/stock/{symbol}")   // Java
// vs Python: GET /concepts/by-symbol/{symbol}
```

**问题**：
- 与 Python 不一致，前端如果同时调两套会有 2 个路径要写。
- 规范没有强制要求统一，但**团队选一种**。

**修复方向**：
- 推荐 Java 用 `/stock/{symbol}`（更简洁），Python 端加兼容路由。
- 或反向：Java 改为 `/by-symbol/{symbol}`，与 Python 对齐。

### 3.2 概念 id 命名

**位置**：`backend-java/src/main/java/com/attribution/controller/ConceptController.java:31`

```java
@GetMapping("/{code}")           // Java
// vs Python: GET /concepts/{name}
```

**问题**：
- Java 用 `code`，Python 用 `name`，不一致。
- `code` 更准确（概念名称可能重复），但 Python 端按 `name` 调用是兼容问题。

**修复方向**：
- 推荐 Java 用 `code`，Python 端如果前端按 `name` 调用则改成 `code`（推荐）。

### 3.3 K 线日期参数命名

**位置**：`backend-java/src/main/java/com/attribution/controller/KlineController.java:67, 104`

```java
@GetMapping("/{symbol}/{tradeDate}")   // Java camelCase
// vs Python: GET /klines/{symbol}/{trade_date}  snake_case
```

**问题**：
- 仅占位符命名风格差异。
- Spring 的 `@PathVariable("tradeDate")` 会用 `{tradeDate}` 作为路径表达式，与 Python 的 `{trade_date}` 不同。

**修复方向**：
- 推荐 Java 用 `tradeDate`（camelCase，符合团队规范）。
- Python 端保留 `trade_date`（已在生产）。

### 3.4 采集任务路径风格

**位置**：`backend-java/src/main/java/com/attribution/controller/CollectController.java:17, 35`

```java
@RequestMapping("/api/v1/collect")
@PostMapping                                   // Java: POST /collect
@GetMapping("/{taskId}/progress")              // Java: GET /collect/{taskId}/progress

// vs Python:
// POST /collect/tasks
// GET  /collect/tasks/{taskId}/progress
```

**问题**：
- Python 把任务当**复数子资源** `tasks`，Java 直接用**根路径 `/collect`**。
- 路径命名风格不一致。

**修复方向**：
- 推荐以 Java 为准（"主表即模块名"），Python 端保持不变（已在生产）。
- 这是迁移规范差异，**不是 bug**。

---

## 4. 分页参数风格不一致（P1）

### 4.1 同工程两种分页风格并存

| Controller              | 接口                                   | 风格              |
| ----------------------- | -------------------------------------- | ----------------- |
| `PoolController`        | `GET /pools`                           | `limit + offset`（0-based）|
| `PoolController`        | `GET /pools/{poolId}/members`          | `limit + offset`  |
| `PoolController`        | `GET /pools/{poolId}/operations`       | `limit + offset`  |
| `KlineController`       | `GET /klines/{symbol}`                 | `limit`（按日期范围） |
| `PanelController`       | `GET /stock-panel`                     | `page + size`（1-based）|

**位置**：
- `backend-java/src/main/java/com/attribution/controller/PoolController.java:67-70, 121-124, 178-181`
- `backend-java/src/main/java/com/attribution/controller/PanelController.java:30-31`
- `backend-java/src/main/java/com/attribution/controller/KlineController.java:48`

**问题**：
- 同一工程内部**两种风格并存**，前端要写 2 套分页逻辑。
- 违反 `01-endpoint-spec.md §5` "分页参数统一为 `limit + offset`"。

**修复方向**：
- `PanelController` 改为 `limit + offset`。
- `KlineController` 是按日期范围查询，`limit` 单独使用是合理的，**保留**。

### 4.2 `ConceptController` 列表返回裸 List，无 total

**位置**：`backend-java/src/main/java/com/attribution/controller/ConceptController.java:24-29`

```java
@GetMapping
public ResponseEntity<ApiResponse<List<ConceptBriefVO>>> list(
        @RequestParam(required = false) String source) {
    return ResponseEntity.ok(ApiResponse.ok(conceptService.getAllConcepts(source)));
}
```

**问题**：
- 返回 `List<ConceptBriefVO>` 而**不是分页结构**（没有 `total`）。
- 违反 `02-response-spec.md §6.1` "业务方自定义 ListVO 必须至少包含 `{total, items}`"。
- 前端分页组件完全没法用。

**修复方向**：
- 改为 `PageResponse<ConceptBriefVO>` 或自定义 ListVO 含 `total`。
- 加 `limit` + `offset` 参数。

---

## 5. 业务异常机制缺陷（P0）

### 5.1 `BusinessException` 不支持"特殊解耦"

**位置**：`backend-java/src/main/java/com/attribution/exception/BusinessException.java:19-44`

```java
public class BusinessException extends RuntimeException {
    private final String module;
    private final String code;        // String 业务码
    private final int httpStatus;     // HTTP 状态码
    // 没有 bodyCode 字段
}
```

**问题**：
- `GlobalExceptionHandler.handleBusiness` 强制 `body.code = httpStatus`，**无法实现"HTTP 403 + body.code 1001（token 过期）"这种特殊解耦**。
- 违反 `02-response-spec.md §5` "特殊解耦场景"（鉴权 / 限流 / token 过期）。

**修复方向**（详见 `03-fix-plan.md`）：
- 新增独立异常类 `BizCodeException`，专门走"特殊解耦"路径。
- `handleBizCode` 异常处理器，HTTP 状态码与 body.code 分别赋值。

### 5.2 `GlobalExceptionHandler.handleBusiness` 字段语义错位

**位置**：`backend-java/src/main/java/com/attribution/exception/GlobalExceptionHandler.java:19-25`

```java
@ExceptionHandler(BusinessException.class)
public ResponseEntity<ErrorResponse> handleBusiness(BusinessException ex) {
    return ResponseEntity
            .status(ex.getHttpStatus())
            .body(ErrorResponse.of(ex.getHttpStatus(), ex.getCode(), ex.getMessage()));
}
```

**问题**：
- 见 §2.4，字段赋值方向与命名暗示不一致。
- `ErrorResponse.code` 装 HTTP 状态码、`message` 装业务错误码字符串、`data` 装格式化后的人话消息。

**修复方向**：
- 用新的 `ErrorResponse.ofBiz(httpStatus, bizCode, humanMessage)` 替代。
- 清晰表达意图。

### 5.3 `BusinessException.format()` 把 message 又拼了一遍

**位置**：`backend-java/src/main/java/com/attribution/exception/BusinessException.java:46-51`

```java
private static String format(String module, String code, String message) {
    return "[" + m + "]-[" + c + "]-[" + msg + "]";
}
```

**问题**：
- 调用 `super(format(module, code, message))` 把 message 拼成 `"[module]-[code]-[msg]"`。
- 然后 `handleBusiness` 又把 code 和 message 拆开分别填到 `ErrorResponse.message` 和 `ErrorResponse.data`。
- **结果**：`data` 里出现的字符串是 `"[stock]-[STOCK_NOT_FOUND]-[股票不存在]"`，带方括号，前端不能直接展示给用户。
- **冗余**：code 已经在 message 字段了，又出现在 data 里。

**修复方向**：
- 改用 `super(message)`（不拼装），把 module + code + message 分别存字段，handler 自行决定如何组合。

---

## 6. 业务方自定义 VO 不统一（P1）

### 6.1 4 个分页 VO 字段不一致

| VO 类                  | 字段                              | 位置  |
| ---------------------- | --------------------------------- | ----- |
| `PoolListVO`           | `total, items`                    | dto/pool |
| `PoolMemberListVO`     | `poolId, total, items`            | dto/pool |
| `PoolOperationListVO`  | `poolId, total, items`            | dto/operation |
| `StockPanelResponse`   | `rows, total, page, size, tradeDate` | dto |

**问题**：
- 字段命名不统一：`items` vs `rows`。
- 字段集不统一：有的带 `page + size`，有的只带 `total`。
- 前端拿到的分页结构**4 种都不同**，解析时要写 4 套代码。
- 违反 `02-response-spec.md §6.3` "必须保留 `{total, items|rows}` 两个核心字段"。

**修复方向**：
- **推荐**：所有分页 VO 统一用 `PageResponse<T>`（含 `{total, page, size, items}`）。
- **折中**：保留业务 VO，但**强制最小字段**为 `{total, items}`。
- **当前现状**：4 个 VO 都至少有 `{total, items|rows}`，**勉强满足**最小字段约束。但命名风格仍需统一。

### 6.2 `ConceptController.list` 返回裸 List VO

**位置**：`backend-java/src/main/java/com/attribution/controller/ConceptController.java:24-29`

（详见 §4.2）

---

## 7. 汇总表

| #  | 问题                                       | 位置                                                                                       | 优先级 | 类别 |
| --- | ------------------------------------------ | ------------------------------------------------------------------------------------------ | ------ | ---- |
| 1  | `ApiResponse.fail()` 写死 404 + HTTP=200   | `dto/response/ApiResponse.java:58`                                                         | P0     | 响应封装 |
| 2  | `ApiResponse.error()` 不应该被直接调用     | `dto/response/ApiResponse.java:50`                                                         | P0     | 响应封装 |
| 3  | `ErrorResponse.handleBusiness` 字段语义错位 | `exception/GlobalExceptionHandler.java:24`                                                | P0     | 响应封装 |
| 4  | `BusinessException` 不支持特殊解耦         | `exception/BusinessException.java`                                                        | P0     | 异常机制 |
| 5  | `BusinessException.format()` 冗余拼装      | `exception/BusinessException.java:46`                                                      | P0     | 异常机制 |
| 6  | `CollectController.getProgress` 调 `fail()` | `controller/CollectController.java:42`                                                     | P0     | 响应封装 |
| 7  | 概念反向路径措辞（`/stock` vs `/by-symbol`）| `controller/ConceptController.java:37`                                                     | P1     | 路径命名 |
| 8  | 概念 id 命名（`code` vs `name`）            | `controller/ConceptController.java:31`                                                     | P1     | 路径命名 |
| 9  | K 线日期参数命名（`tradeDate` vs `trade_date`）| `controller/KlineController.java:67, 104`                                                | P1     | 路径命名 |
| 10 | 采集任务路径风格（`/collect` vs `/collect/tasks`）| `controller/CollectController.java:17`                                                  | P1     | 路径命名 |
| 11 | Panel 分页参数风格（`page+size` vs `limit+offset`）| `controller/PanelController.java:30`                                                    | P1     | 分页参数 |
| 12 | `ConceptController.list` 无分页             | `controller/ConceptController.java:24`                                                     | P1     | 分页参数 |
| 13 | 4 个分页 VO 字段不统一                     | `dto/pool/PoolListVO.java` 等                                                              | P1     | VO 统一 |
| 14 | 业务异常 message 拼接后含方括号             | `exception/BusinessException.java:50`                                                      | P1     | 异常机制 |

> 💡 `HealthController.health()` 返回裸 Map 是**规范明确允许的例外**，**不算违规**。

# 03 · 统一响应封装 `[code, data, msg]`

> 本文档定义系统中**所有业务接口**的统一响应结构、错误码体系、HTTP 状态码同步策略。  
> 与 `02-page-vo.md` 配合：`PageVO<T>` 是 `data` 字段的形态之一。

---

## 1. 设计目标

| 目标           | 描述                                                  |
| -------------- | ----------------------------------------------------- |
| 业务自描述     | 业务错误码 + 错误消息，前端能直接展示给用户             |
| 协议层通用     | HTTP 状态码能正确反映请求层面的成功/失败               |
| 可扩展         | 未来加 `serverTime` / `version` 等元信息不影响前端       |

---

## 2. 顶层结构

### 2.1 JSON 形态

```jsonc
{
  "code": 0,                    // 业务状态码（见第 4 节）
  "data": { ... } | [ ... ] | null,  // 业务数据
  "msg": "ok"                   // 文案（成功为 "ok"，失败为可展示的错误文案）
}
```

### 2.2 字段定义

| 字段       | 类型              | 是否可缺省 | 含义                                                  |
| ---------- | ----------------- | ---------- | ----------------------------------------------------- |
| `code`     | `int`             | 否         | 业务状态码（**不是 HTTP 状态码**）。0 表示成功。      |
| `data`     | `object \| array \| null` | 是  | 业务数据。成功时为具体内容；失败时为 `null`。        |
| `msg`      | `string`          | 否         | 文案。成功为 `ok`；失败为可展示给用户的错误描述。      |

> 🔑 **`code = 0` 表示成功**（不要用 `200` 当业务成功码，因为 200 是 HTTP 协议层概念）。  
> 前端判定逻辑：**`code === 0` → 业务成功**，否则按 `msg` 提示用户。

---

## 3. Java 类型定义

### 3.1 顶层封装类

```java
package com.attribution.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "统一响应封装")
public class ApiResponse<T> {

    @Schema(description = "业务状态码（0=成功）")
    private int code;

    @Schema(description = "业务数据")
    private T data;

    @Schema(description = "文案")
    private String msg;

    public static <T> ApiResponse<T> ok(T data) {
        ApiResponse<T> r = new ApiResponse<>();
        r.code = ErrorCode.SUCCESS.getCode();
        r.data = data;
        r.msg = ErrorCode.SUCCESS.getMsg();
        return r;
    }

    public static <T> ApiResponse<T> error(ErrorCode code) {
        ApiResponse<T> r = new ApiResponse<>();
        r.code = code.getCode();
        r.msg = code.getMsg();
        return r;
    }

    public static <T> ApiResponse<T> error(ErrorCode code, String msg) {
        ApiResponse<T> r = new ApiResponse<>();
        r.code = code.getCode();
        r.msg = msg;
        return r;
    }
}
```

### 3.2 错误码枚举

```java
package com.attribution.dto;

public enum ErrorCode {

    SUCCESS(0, "ok"),

    // ========== 客户端错误 1xxxx ==========
    BAD_REQUEST(10001, "请求参数错误"),
    MISSING_PARAM(10002, "缺少必要参数"),
    INVALID_PARAM(10003, "参数值非法"),
    UNAUTHORIZED(11001, "未登录或登录已过期"),
    FORBIDDEN(11002, "无权限访问"),
    NOT_FOUND(12001, "资源不存在"),

    // ========== 业务错误 2xxxx ==========
    STOCK_NOT_FOUND(20001, "股票不存在"),
    POOL_NOT_FOUND(20101, "股票池不存在"),
    POOL_MEMBER_EXISTS(20102, "成员已存在"),
    POOL_MEMBER_NOT_FOUND(20103, "成员不存在"),
    CONCEPT_NOT_FOUND(20201, "概念不存在"),
    KLINE_NOT_FOUND(20301, "K 线不存在"),
    TASK_NOT_FOUND(20401, "任务不存在"),
    TASK_ALREADY_RUNNING(20402, "任务正在运行"),
    TASK_ALREADY_CANCELED(20403, "任务已取消"),

    // ========== 第三方错误 3xxxx ==========
    TUSHARE_API_ERROR(30001, "Tushare 接口调用失败"),
    PYTDX_API_ERROR(30002, "Pytdx 接口调用失败"),
    AKSHARE_API_ERROR(30003, "AkShare 接口调用失败"),

    // ========== 服务端错误 5xxxx ==========
    INTERNAL_ERROR(50001, "服务内部异常"),
    DB_ERROR(50002, "数据库异常"),
    CACHE_ERROR(50003, "缓存异常"),
    REMOTE_CALL_ERROR(50004, "下游服务调用失败");

    private final int code;
    private final String msg;

    ErrorCode(int code, String msg) {
        this.code = code;
        this.msg = msg;
    }

    public int getCode() { return code; }
    public String getMsg() { return msg; }
}
```

---

## 4. 错误码规划（与 HTTP 状态码对齐）

### 4.1 错误码区段

| 区段      | 含义               | 对应 HTTP 状态码          |
| --------- | ------------------ | ------------------------- |
| `0`       | 业务成功           | 200                       |
| `1xxxx`   | 客户端错误         | 400 / 401 / 403 / 404     |
| `2xxxx`   | 业务错误           | 200 / 409                 |
| `3xxxx`   | 第三方 / 外部错误  | 502 / 503                 |
| `4xxxx`   | 限流 / 配额        | 429                       |
| `5xxxx`   | 服务端内部错误     | 500                       |

### 4.2 业务码 vs HTTP 状态码

**关键原则**：

- **HTTP 状态码** 反映 **协议层** 成功/失败（路由有没有到、参数格式对不对）
- **业务码 `code`** 反映 **业务语义** 成功/失败（数据是否存在、规则是否允许）

| 场景                           | HTTP 状态码 | 业务码 `code`        | 说明                                    |
| ------------------------------ | ----------- | -------------------- | --------------------------------------- |
| 查询成功                       | 200         | `0`                  | 标准成功                                |
| 资源不存在                     | 404         | `12001` / `20001` 等 | 协议层 404，业务码指明具体找不到什么      |
| 参数缺失                       | 400         | `10002`              | Bean Validation 失败                    |
| 参数值非法                     | 400         | `10003`              | 业务校验失败                            |
| 未登录                        | 401         | `11001`              | 鉴权失败                                |
| 无权限                        | 403         | `11002`              | RBAC 失败                               |
| 业务冲突（成员已存在）          | 409         | `20102`              | 业务冲突，HTTP 同步 409                  |
| 内部异常                       | 500         | `50001`              | 服务端兜底                              |
| 下游服务失败                   | 502         | `30001` / `50004`    | 上游问题                                |

> 🔑 **业务码 2xxxx 通常仍然返回 HTTP 200**，因为业务层"完成了一次请求"。  
> 例：股票不存在 = 业务语义，不是协议错误。HTTP 200 + `code=20001` 是合理表达。  
> 但**客户端错误**（参数错、未登录）必须同步 HTTP 400/401，前端能立刻拿到协议层失败信息。

### 4.3 业务码使用决策

```
业务失败是因为"协议层错了"吗？
│
├── 是（参数格式、鉴权、路由）→ HTTP 4xx + 业务码 1xxxx
│
└── 否（业务规则不允许）→ HTTP 200 + 业务码 2xxxx
```

---

## 5. Spring 实现要点

### 5.1 全局异常处理

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BizException.class)
    public ApiResponse<Void> handleBiz(BizException ex) {
        return ApiResponse.error(ex.getErrorCode(), ex.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ApiResponse<Void> handleValidation(MethodArgumentNotValidException ex) {
        String msg = ex.getBindingResult().getAllErrors().stream()
                .findFirst().map(ObjectError::getDefaultMessage).orElse("请求参数错误");
        return ApiResponse.error(ErrorCode.INVALID_PARAM, msg);
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ApiResponse<Void> handleMissingParam(MissingServletRequestParameterException ex) {
        return ApiResponse.error(ErrorCode.MISSING_PARAM, "缺少必要参数: " + ex.getParameterName());
    }

    @ExceptionHandler(Exception.class)
    public ApiResponse<Void> handleAny(Exception ex) {
        log.error("unhandled exception", ex);
        return ApiResponse.error(ErrorCode.INTERNAL_ERROR, "服务内部异常");
    }
}
```

### 5.2 Controller 写法

```java
@GetMapping("/list")
public ApiResponse<PageVO<StockInfoVO>> list(@Valid StockListQuery query) {
    return ApiResponse.ok(stockService.list(query));
}

@GetMapping("/{id}")
public ApiResponse<StockDetailVO> get(@PathVariable String id) {
    StockDetailVO detail = stockService.get(id);
    if (detail == null) {
        throw new BizException(ErrorCode.STOCK_NOT_FOUND);
    }
    return ApiResponse.ok(detail);
}
```

---

## 6. 完整响应示例

### 6.1 成功（GET 列表）

```jsonc
{
  "code": 0,
  "data": {
    "total": 153,
    "page": 1,
    "pageSize": 20,
    "dataList": [ ... ]
  },
  "msg": "ok"
}
```

### 6.2 成功（GET 单个）

```jsonc
{
  "code": 0,
  "data": {
    "symbol": "000001.SZ",
    "name": "平安银行"
  },
  "msg": "ok"
}
```

### 6.3 业务失败（资源不存在）

```jsonc
{
  "code": 20001,
  "data": null,
  "msg": "股票不存在"
}
```

HTTP 状态码：`200`（业务层错误，但协议层成功）  
> 也可选择返回 `404` + `code=20001`，取决于团队约定（见第 7 节"两种风格的取舍"）

### 6.4 协议层失败（参数缺失）

```jsonc
{
  "code": 10002,
  "data": null,
  "msg": "缺少必要参数: poolId"
}
```

HTTP 状态码：`400`

### 6.5 未登录

```jsonc
{
  "code": 11001,
  "data": null,
  "msg": "未登录或登录已过期"
}
```

HTTP 状态码：`401`

### 6.6 服务端异常

```jsonc
{
  "code": 50001,
  "data": null,
  "msg": "服务内部异常"
}
```

HTTP 状态码：`500`

---

## 7. 两种风格的取舍（业务失败时 HTTP 状态码）

### 风格 A：业务失败 → HTTP 200（**推荐**）

```
"股票不存在" → HTTP 200, code=20001
```

| 优点                            | 缺点                                     |
| ------------------------------- | ---------------------------------------- |
| 前端只用 `code === 0` 判定成功   | 监控/CDN 边缘节点可能漏计失败请求         |
| 业务错误信息更详细              | HTTP 网关层无法基于状态码做重试            |
| 与 tRPC / GraphQL 错误模型接近   | 略不"标准 REST"                         |

### 风格 B：业务失败 → HTTP 4xx

```
"股票不存在" → HTTP 404, code=20001
"成员已存在" → HTTP 409, code=20102
```

| 优点                            | 缺点                                     |
| ------------------------------- | ---------------------------------------- |
| 严格符合 REST HTTP 语义         | 前端需要同时判断 HTTP 状态码和 `code`     |
| 网关 / CDN 可以基于状态码路由    | 业务失败信息在响应体中，前端要解析          |
| 标准 OpenAPI 工具友好            | HTTP 层 404 在列表场景下语义尴尬（"列表里某个项不存在"） |

### 推荐

> **风格 A 为主**：业务失败统一 `HTTP 200 + code != 0`。  
> **例外**：客户端协议错误（参数错、鉴权失败）同步 `HTTP 4xx`，便于网关拦截。

| 失败类型         | HTTP 状态码 | 业务码 `code`        |
| ---------------- | ----------- | -------------------- |
| 参数缺失 / 非法   | 400         | `10002` / `10003`    |
| 未登录           | 401         | `11001`              |
| 无权限           | 403         | `11002`              |
| **业务规则失败** | **200**     | **2xxxx**            |
| 第三方服务失败   | 502         | `3xxxx`              |
| 限流             | 429         | `4xxxx`              |
| 服务端异常       | 500         | `5xxxx`              |

> ⚠️ **如果团队倾向于"风格 B"**：所有业务失败也同步 HTTP 4xx，文档实施时统一调整。

---

## 8. 前端约定

### 8.1 判定成功

```js
const isSuccess = (resp) => resp.code === 0;
```

### 8.2 显示错误

```js
if (!isSuccess(resp)) {
    toast.error(resp.msg);
    if (resp.code === 11001) {
        redirectToLogin();
    }
}
```

---

## 9. Swagger / OpenAPI 集成

### 9.1 全局响应包装

```java
public class ApiResponseSchemaPlugin implements ModelConverter {

    // SpringDoc / Swagger 自动识别 ApiResponse<T> 作为通用响应包装
}
```

实际更简单的方式是在 `@Operation` 注解上声明：

```java
@Operation(
    summary = "查询股票列表",
    responses = {
        @ApiResponse(responseCode = "200", description = "成功",
            content = @Content(schema = @Schema(implementation = ApiResponse.class))),
        @ApiResponse(responseCode = "400", description = "参数错误",
            content = @Content(schema = @Schema(implementation = ApiResponse.class))),
    }
)
```

---

## 10. 评审 checklist

- [ ] 顶层结构字段（`code` / `data` / `msg` 共 3 个）接受
- [ ] `code = 0` 表示成功这条约定接受
- [ ] 错误码区段划分（1xxxx / 2xxxx / 3xxxx / 5xxxx）接受
- [ ] 业务码与 HTTP 状态码的对应表（第 4.2 节）接受
- [ ] **风格 A vs 风格 B** 的取舍（第 7 节）已选定（推荐 A）
- [ ] `data: null` 在失败时使用，**不在成功时使用**（除非业务允许）

---

## 11. 变更记录

| 版本 | 日期       | 变更人 | 变更内容                       |
| ---- | ---------- | ------ | ------------------------------ |
| v0.2 | 2026-09-25 | -      | 响应去掉 `traceId` 字段         |
| v0.1 | 2026-09-25 | -      | 初稿，待评审                   |

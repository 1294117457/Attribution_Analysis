# interface 层规范

> 只关心 HTTP 协议。业务逻辑全部委托给 AppService。

## 1. 包结构

```
com.attribution.interface/
├── controller/       REST 控制器
├── dto/              跨层数据传输（Request / Response / VO）
│   └── response/     ApiResponse / PageResponse / ErrorResponse（跨模块通用响应）
└── handler/          GlobalExceptionHandler（统一异常映射）
```

未来扩展：`rpc/` / `graphql/` / `scheduler/` / `mq/`

> 💡 **设计原则**：interface 是**唯一对外暴露的层**，DTO 是**对外接口契约**，所以 DTO 必须与 controller 同层。
> 
> dto 子包按业务模块划分，模块名随业务演进自然增长，不在规范中预先枚举（详见 `00-overview.md §3.1`）。

## 2. Controller 规范

### 命名

- `XxxController`（不带 `AppService` 后缀）
- 一类资源一个 Controller（`PoolController` / `KlineController`）

### 注解

```java
@RestController
@RequestMapping("/api/v1/pools")
@RequiredArgsConstructor
@Tag(name = "股票池")    // OpenAPI
public class PoolController {
    ...
}
```

### 方法样板

```java
@GetMapping("/{id}")
@Operation(summary = "查询股票池")
public ResponseEntity<ApiResponse<PoolDetailVO>> getPool(@PathVariable @Min(1) Long id) {
    PoolDetailVO vo = poolControllerService.queryPool(id);   // 见 §4.2 解释
    return ResponseEntity.ok(ApiResponse.ok(vo));
}

@PostMapping
@Operation(summary = "创建股票池")
public ResponseEntity<ApiResponse<PoolVO>> createPool(
        @RequestBody @Valid PoolCreateRequest req) {
    PoolVO vo = poolControllerService.createPool(req);
    return ResponseEntity
        .status(HttpStatus.CREATED)
        .body(ApiResponse.created(vo, "创建成功"));
}
```

### 路径规范

| 操作 | HTTP | 路径 |
|------|------|------|
| 列表 | GET | `/xxx` |
| 详情 | GET | `/xxx/{id}` |
| 创建 | POST | `/xxx` |
| 更新 | PUT | `/xxx/{id}` |
| 部分更新 | PATCH | `/xxx/{id}` |
| 删除 | DELETE | `/xxx/{id}` |
| 子资源 | GET | `/xxx/{id}/yyy` |

## 3. 入参规范

### 3.1 Request DTO 必须

- 入参对象用 `XxxRequest` 命名，带 `@Valid`
- 字段级校验（`@NotNull` / `@Size` / `@Min` 等）
- 路径参数加 `@Min(1)` 等基础校验
- 放在 `interface/dto/{module}/`（**禁止**放在 domain 或 application 包）

### 3.2 Request 与 Query 的区分

```
入参来源：
  ├── HTTP 请求体（JSON）              → interface/dto/{module}/*Request
  ├── HTTP 查询参数（@RequestParam）    → 简单类型 / 直接在 Controller 方法签名声明
  └── 业务命令（AppService 内部）       → application/command/{X}Command
```

> ❌ **禁止把 `interface/dto/*Request` 直接传给 AppService**（详见 `02-application-spec.md §2.4`）。  
> Controller 应在最后一公里做 DTO → Command 转换。

### 3.3 禁止

- 用 `Map<String, Object>` 当入参
- 直接用 entity 当入参
- 把 `interface/dto/*Request` 传给 AppService

## 4. 出参规范

### 4.1 Response DTO 必须

- 统一用 `ApiResponse<T>` 包装（详见 `docs/design/api/02-response-spec.md`）
- 业务对象用 `XxxVO` 命名，放在 `interface/dto/{module}/`
- 分页用 `PageResponse<T>` 包装
- ✅ 在 Controller 内完成 entity → VO 的装配（assembler / mapstruct）

### 4.2 装配模式

**A. Controller 内直接装配（简单场景）**

```java
@GetMapping("/{id}")
public ApiResponse<PoolDetailVO> getPool(@PathVariable Long id) {
    PoolDetailVO vo = poolAppService.queryPool(id);  // AppService 直接返回 VO（存量代码）
    return ApiResponse.ok(vo);
}
```

**B. Controller + Assembler 装配（推荐）**

```java
@GetMapping("/{id}")
public ApiResponse<PoolDetailVO> getPool(@PathVariable Long id) {
    PoolEntity entity = poolAppService.queryPool(id);  // AppService 返回 entity
    PoolDetailVO vo = PoolAssembler.toDetailVO(entity);  // 装配层
    return ApiResponse.ok(vo);
}
```

**C. Controller + MapStruct（重场景）**

```java
@Mapper(componentModel = "spring")
public interface PoolAssembler {
    PoolDetailVO toDetailVO(PoolEntity entity);
    List<PoolVO> toListVOs(List<PoolEntity> entities);
}
```

### 4.3 模板

```java
public record ApiResponse<T>(
    int code,
    String message,
    T data
) {
    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(200, "success", data);
    }
}
```

> 完整规范见 `docs/design/api/02-response-spec.md`。

## 5. DTO 命名规范

| 类型 | 命名 | 例 |
|------|------|----|
| 入参 | `XxxRequest` | `PoolCreateRequest`、`KlineQueryRequest` |
| 出参（单条） | `XxxVO` | `PoolVO`、`KlineVO` |
| 出参（列表 / 分页） | `XxxListVO` 或 `PageResponse<XxxVO>` | `PoolListVO`、`PageResponse<PoolVO>` |
| 出参（详情） | `XxxDetailVO` | `PoolDetailVO` |
| 出参（进度 / 状态） | `XxxProgressVO` / `XxxStatusVO` | `PoolOperationProgressVO`、`ConceptSyncStatusVO` |
| 出参（动作结果） | `XxxResultVO` | `PoolAddMembersResultVO` |
| 通用响应 | `ApiResponse` / `PageResponse` / `ErrorResponse` | — |

## 6. 禁止清单

| ❌ 禁止 | ✅ 应该 |
|--------|--------|
| 注入 repository | 通过 AppService |
| 注入 entity | — |
| 写业务逻辑 | — |
| `try-catch` 后重新包装异常 | 交给 `GlobalExceptionHandler` |
| 返回 entity | 返回 VO |
| `HttpServletRequest.getParameter(...)` | 用 `@RequestParam` |
| 把 `interface/dto/*Request` 传给 AppService | Controller 做 DTO → Command 转换 |
| 把 `interface/dto/*VO` 当 AppService 返回值 | AppService 返回 entity，Controller 装配 |
| domain.repository 返回 DTO | Repository 返回 entity |

## 7. GlobalExceptionHandler 规范

### 位置

- 放在 `interface/handler/`（不是 infrastructure）

### 职责

- 把 `DomainException` / `BusinessException` / `CollectionException` 转成 HTTP 响应
- 字段语义详见 `docs/design/api/02-response-spec.md §2.4`

### 模板

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ErrorResponse> handleBusiness(BusinessException e) {
        return ResponseEntity
            .status(e.getHttpStatus())
            .body(ErrorResponse.ofBiz(e.getHttpStatus(), e.getCode(), e.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException e) {
        List<String> errors = /* 收集错误 */;
        return ResponseEntity
            .status(HttpStatus.UNPROCESSABLE_ENTITY)
            .body(ErrorResponse.of(422, "请求参数校验失败", errors));
    }
}
```

### 状态码约定

| 异常类型 | HTTP 状态 |
|---------|-----------|
| `PoolNotFoundException` 等"找不到" | 404 |
| `DuplicateMemberException` 等"业务冲突" | 409 |
| `BusinessException` 其他业务错误 | 400 |
| `MethodArgumentNotValidException` 入参校验 | 422 |
| 其他系统异常 | 500 |

## 8. CORS / 安全

- CORS 配置放 `infrastructure/config/CorsConfig`
- 安全相关（Spring Security / JWT）放 `infrastructure/security/`
- Controller 只关心业务，不写安全逻辑

## 9. 当前代码违规清单（已知项，待 PR 收口）

> ⚠️ 以下是**当前代码已存在的违规**（与文档规范不符），列出来用于后续 PR 收口跟踪。

### 9.1 DTO 跨层引用

| # | 位置 | 现状 | 目标 |
|---|------|------|------|
| 1 | `service/ConceptService` | 直接返回 `ConceptBriefVO` / `ConceptDetailVO` / `ConceptMemberVO` / `ConceptSyncStatusVO` | 返回 entity / domain VO，controller 装配 |
| 2 | `service/StockPanelService` | 入参接 `StockPanelQuery`，返回 `StockPanelResponse` | 入参改 application/command/*Command，返回 entity |
| 3 | `adapter/collector/tushare/TushareKlineCollector` | `collect()` 返回 `KlineCollectVO` | 返回 entity / domain VO |
| 4 | `domain/repository/StockPanelComposeRepository` | `queryPanel()` 返回 `StockPanelRowVO` | 返回 entity |
| 5 | `infrastructure/query/StockPanelComposeRepositoryImpl` | `queryPanel()` 返回 `StockPanelRowVO` | 返回 entity |

### 9.2 dto 包路径

| # | 项 | 现状 | 目标 |
|---|----|------|------|
| 1 | dto 顶级包 | `com.attribution.dto` | `com.attribution.interface.dto` |
| 2 | dto 子包 | `pool` / `kline` / `operation` / `stock`（不规范命名） | 与文档 §1 一致 |

### 9.3 应用层包路径

| # | 项 | 现状 | 目标 |
|---|----|------|------|
| 1 | service 顶级包 | `com.attribution.service` | `com.attribution.application.service` |

### 9.4 迁移 PR 计划

迁移 `dto` 包时，建议按以下顺序：

```
PR1: 新增 interface/dto/（新位置）
PR2: 旧 dto 标记 @Deprecated，import 加 @see 指向新位置
PR3: 按模块迁移 controller（import 替换）
PR4: 按模块迁移 service（消除 service → dto 引用）
PR5: 按模块迁移 adapter / repository（消除下层 → dto 引用）
PR6: 删除旧 dto 包
```

## 10. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-25 | -      | 初稿 |
| v0.2  | 2026-09-25 | -      | 新增 `dto/` 子包完整定义（§1）；明确 DTO 命名规范（§5）；新增"当前代码违规清单"（§9） |

# Controller 层规范（HTTP 协议适配层）

> 适用范围：`backend-java` 全部 Maven 模块的 `controller/` 包
> 核心原则：**Controller 只做「协议适配」——绑定参数、触发校验、提取鉴权信息、封装响应。**
> 同层文档：`Service层规范.md`（业务编排）、`Mapper层规范.md`（持久化）、`POJO规范.md`（数据形状）

---

## 0. 一句话结论
> **Controller 里不应该出现任何业务判断。**
> 凡是「这个值合不合法（要查库才知道）」「这条数据存不存在」「这个操作允不允许」——全部属于 Service。
> Controller 只回答一个问题：**「这个 HTTP 请求的形状对不对？」**

---

## 1. 职责速查

```
┌──────────────────────────────────────────────────────────────┐
│ Controller  ★ 协议适配层 ★                                     │
│             · 路径与方法映射（@GetMapping / @PostMapping）      │
│             · 参数绑定（@RequestBody / @RequestParam /         │
│               @PathVariable / @ModelAttribute）                │
│             · 触发格式校验（@Valid）                           │
│             · 提取鉴权信息（Authorization / UA / IP）           │
│             · 封装响应（ApiResponse<T>）                       │
│             · 异常 → HTTP 的映射（由 GlobalExceptionHandler 兜）│
│   ↕ DTO(Query) / VO                                          │
├──────────────────────────────────────────────────────────────┤
│ Service     业务编排（见 Service层规范.md）                     │
└──────────────────────────────────────────────────────────────┘
```

| 层 | 唯一职责 | 判断标准 |
|---|---|---|
| **Controller** | 协议适配 | 代码里出现 `@RequestParam` / `@PathVariable` / `HttpServletRequest` / `ApiResponse` |
| **Service** | 业务编排 | 代码里出现查库后的 `if` 判断、多个 Mapper 协作、`@Transactional` |
| **Mapper** | 数据存取 | 代码里只有查询条件与结果映射，无业务判断 |

> ⚠️ **反向自检**：**如果你在 Controller 里写了 `if`，先问自己一句「这个判断需要查库吗？」**
> 不需要 → 应该是 DTO 的 `@Valid` 注解；需要 → 下沉 Service。

---

## 2. Controller 层「该做」什么

### 2.1 路径与方法映射

| 规则 | 说明 |
|---|---|
| **统一前缀 `/api`** | 业务接口一律 `/api/**`；CORS 也只放开 `/api/**` |
| **资源路径小写 + 连字符** | `/api/stock-panel`、`/api/minute-klines`、`/api/data-board`（复数用 `-klines` 这类固定后缀，全项目一致）|
| **集合 vs 单资源** | 集合 `/api/pools`；单资源 `/api/pools/{id}`；子资源 `/api/pools/{id}/members` |
| **动作用子路径，不造动词** | `/sync`、`/cancel`、`/progress`、`/collect`（全项目统一风格）|
| **同一资源域可拆多个 Controller** | `ConceptQueryController` / `ConceptBoardController` / `ConceptQuoteController` 共用 `@RequestMapping("/api/concepts")`，按「读 / 大盘 / 实时」拆分而非按方法拆分 |
| **尾斜杠** | **类级 `@RequestMapping` 不带尾斜杠**；方法级 `@GetMapping` 集合根用 `""` 或 `"/"` 二选一，全项目统一 |

```java
// ✅ 正确：集合根用空串，子资源用相对路径
@RestController
@RequestMapping("/api/pools")
@RequiredArgsConstructor
public class PoolController {
    private final PoolService poolService;

    @GetMapping
    public ApiResponse<PageResult<PoolVO>> list(@Valid @ModelAttribute PoolQuery query) {
        return ApiResponse.ok(poolService.list(query));
    }

    @GetMapping("/{id}")
    public ApiResponse<PoolDetailVO> one(@PathVariable("id") int id) {
        return ApiResponse.ok(poolService.one(id));
    }
}
```

### 2.2 参数绑定

| 参数来源 | 注解 | 规则 |
|---|---|---|
| 请求体（复杂对象）| `@Valid @RequestBody XxxRequest` | **必须**带 `@Valid`，否则 Bean Validation 静默失效 |
| 查询条件（多字段）| `@Valid @ModelAttribute XxxQuery` | **推荐**替代「一堆 `@RequestParam` + 手工 `query.setXxx()`」|
| 单个路径变量 | `@PathVariable("id") int id` | **必须显式写名字** |
| 单个查询参数 | `@RequestParam(...) String x` | 仅 1~2 个标量时可直接用 |
| 鉴权头 / UA / IP | `@RequestHeader` / `HttpServletRequest` | 从服务端取，**不允许前端传** |

**`@PathVariable` 必须显式命名**：

```java
// ❌ 依赖编译参数 -parameters 才生效：父 pom 的 maven-compiler-plugin 配了 <parameters>true</parameters>，
//    但换 IDE 直接 javac、换构建工具或有人删掉这个配置，就会静默 404（不报错，只是取不到值）
public ApiResponse<XxxVO> one(@PathVariable String symbol) { ... }

// ✅ 显式绑定，不依赖任何编译配置
public ApiResponse<?> one(@PathVariable("symbol") String symbol) { ... }
```

### 2.3 触发格式校验

**格式校验（长度 / 正则 / 范围 / 必填）一律用 Bean Validation 注解，不写 `if`。**

```java
// ✅ 正确
@PostMapping("/pools")
public ApiResponse<PoolVO> create(@Valid @RequestBody PoolCreateRequest request) {
    return ApiResponse.created(poolService.create(request));
}
```

| 写法 | 行为 |
|---|---|
| `@Valid @RequestBody XxxRequest` | ✅ 触发校验，失败抛 `MethodArgumentNotValidException` → 422 + 全部字段错误 |
| `@RequestBody Map<String,Object>` | ❌ **无任何校验**，字段名靠手写字符串 |
| `@RequestParam String email` | ⚠️ 触发校验，但逐个参数，不适合多字段 |

> `GlobalExceptionHandler` 收集**全部**字段错误（`joining("; ")`），返回 422，前端拦截器直接弹提示，**前端零改动**。

### 2.4 提取鉴权 / 环境信息

| 信息 | 取法 | 禁止 |
|---|---|---|
| `Authorization` 头 | `@RequestHeader(value = "Authorization", required = false) String auth` | 禁止前端在 body 里传 token |
| User-Agent | `httpRequest.getHeader("user-agent")` | 禁止作为 DTO 字段由前端提交（可伪造）|
| 客户端 IP | `httpRequest.getRemoteAddr()` | 同上 |

> 📌 **统一要求**：鉴权信息的提取应集中在**拦截器 / 参数解析器**中，不要散落在各 Controller 的方法签名里。

### 2.5 封装响应

**统一使用 `ApiResponse<T>`，泛型必须写实参类型。**

```java
// ✅ 正确：类型可被 IDE 检查
public ApiResponse<PoolDetailVO> one(@PathVariable("id") int id) {
    return ApiResponse.ok(poolService.one(id));
}

// ❌ 错误：放弃全部类型检查，返回值只能是 Object
public ApiResponse<?> one(@PathVariable("id") int id) {
    return ApiResponse.ok(poolService.one(id));
}
```

| 工厂方法 | 使用场景 | HTTP |
|---|---|---|
| `ApiResponse.ok(data)` | 查询 / 更新 / 删除成功 | 200 |
| `ApiResponse.created(data)` | **真正创建资源**（`POST` 建池、建概念）| 201 |
| `ApiResponse.fail(code, msg)` | **仅限** Controller 自身的格式性拒绝（如 codes 超上限）| 由 `code` 决定 |

**删除类接口**：返回 `ApiResponse<Void>` + `ApiResponse.ok()`，不要 204（前端拦截器已适配 `{code,message,data}` 结构）。

```java
// ✅ 正确
@DeleteMapping("/{id}")
public ApiResponse<Void> delete(@PathVariable("id") int id) {
    poolService.delete(id);
    return ApiResponse.ok();
}

// ❌ 错误：手拼字面量 Map 响应
@DeleteMapping("/{id}")
public ApiResponse<?> delete(@PathVariable("id") int id) {
    poolService.delete(id);
    return ApiResponse.ok(Map.of("message", "删除成功"));
}
```

### 2.6 分页参数

`page` / `page_size` 的**默认值与上下界 clamp 必须只有一处**——放在 Query DTO 内部，不要散落在 Controller。

```java
// ✅ 正确：Query 自己夹逼，Controller 只负责绑定
@Data
public class StockPanelQuery {
    @Min(value = 1, message = "页码需大于 0")
    private int page = 1;

    @Min(value = 1, message = "每页条数需大于 0")
    @Max(value = 500, message = "每页条数最多 500")
    private int pageSize = 20;
}
```

> ⚠️ **注意命名**：Java 字段是 `pageSize`，而前端参数是 `page_size`。
> Jackson `SNAKE_CASE` 只作用于 **JSON 序列化**，**不影响 `@RequestParam` 的 query string 绑定**。
> 因此 `@ModelAttribute` 绑定时 `page_size` **不会**自动映射到 `pageSize`。
> 两种解法二选一（全项目统一）：
> 1. Query 字段直接命名 `page_size`（需 IDE 关闭下划线告警）；或
> 2. 保留 `pageSize`，在 Controller 用 `@RequestParam(name = "page_size")` 显式桥接一次。

### 2.7 纯透传接口的豁免

`CollectProxyController` 转发的是 **Python collector 的数据结构**，跨语言契约，Java 侧定义 DTO 会造成两语言强耦合
（Python 改字段 → Java 编译失败）。此类接口**豁免** `ApiResponse` 约束，可直接返回 `ResponseEntity<Map<String, Object>>`。

| 豁免条件 | 本项目示例 |
|---|---|
| 数据结构由外部系统定义、原样转发 | `CollectProxyController` 全部方法 |
| 前端契约本身是动态 key | `ConceptService.quotes` 返回 `Map<String, ConceptSnapshotVO>` |

> ⚠️ **豁免必须「原样透传」**。一旦需要对透传数据做加工（改字段名、脱敏、补字段），就不再是豁免场景，
> 必须在 Service 层转成 VO 后再用 `ApiResponse` 返回。

---

## 3. Controller 层「不该做」什么

### 3.1 ❌ 禁止：业务判断

```java
// ❌ 错误：Controller 里判参数并自己拼响应
@PostMapping("/sync-daily-basic")
public ApiResponse<?> syncDailyBasic(
        @RequestParam(required = false) String trade_date,
        @RequestParam(defaultValue = "1") int days) {
    if (trade_date == null)
        return ApiResponse.ok(
                Map.of("synced_count", 0, "dates", List.of(), "message", "请提供 trade_date（YYYYMMDD）"));
    Map<String, Object> syncResult = collectorService.createTask(...);
    return ApiResponse.ok(syncResult);
}

// ✅ 正确：下沉 Service，Controller 只转发
@PostMapping("/sync-daily-basic")
public ApiResponse<Map<String, Object>> syncDailyBasic(@Valid @RequestBody SyncDailyBasicRequest request) {
    return ApiResponse.ok(dataBoardService.syncDailyBasic(request));
}
```

### 3.2 ❌ 禁止：数据搬运（PO → VO 转换）

转换属于 Service（见 `POJO规范.md` §4.3）。Controller 拿到 Service 返回的 VO 直接塞进 `ApiResponse` 即可。

```java
// ❌ 错误：Controller 里拼 VO
StockInfoPO po = stockInfoMapper.selectById(id);
StockInfoVO vo = new StockInfoVO();
vo.setSymbol(po.getSymbol());
// ...

// ✅ 正确
return ApiResponse.ok(stockInfoService.get(symbol));
```

### 3.3 ❌ 禁止：注入 Mapper

```java
// ❌ 错误：Controller 直连持久层
private final StockInfoMapper stockInfoMapper;

// ✅ 正确：只依赖 Service
private final StockInfoService stockInfoService;
```

> Mapper 是**持久化唯一入口**，但它的调用者是 **Service**，不是 Controller。

### 3.4 ❌ 禁止：try-catch 兜业务异常

```java
// ❌ 错误
try {
    return ApiResponse.ok(service.doSomething());
} catch (Exception e) {
    return ApiResponse.fail(500, "服务器错误");
}
```

Service 抛 `BusinessException`，由 `GlobalExceptionHandler` 统一转 HTTP 响应（400/401/403/404/500 + 校验 422）。

### 3.5 ❌ 禁止：手拼 `Map` 响应

```java
// ❌ 错误
return ApiResponse.ok(Map.of("message", "删除成功"));
return ApiResponse.ok(Map.of("removed_count", removed));

// ✅ 正确：无返回值 → ApiResponse<Void>；有计数 → 定义 VO
@DeleteMapping("/{id}/members")
public ApiResponse<Void> removeMembers(@PathVariable("id") int id,
                                       @Valid @RequestBody PoolMembersRequest request) {
    poolService.removeMembers(id, request);
    return ApiResponse.ok();
}
```

> 若确实需要返回计数等结构化字段，**定义 `XxxVO`**（如 `PoolOperationCreateVO` 已有先例），不要用裸 `Map`。

### 3.6 ❌ 禁止：手工装配 Query 对象

```java
// ❌ 错误：手写十几行 set
StockPanelQuery query = new StockPanelQuery();
query.setKeyword(q);
query.setIndustry(industry);
// ... × 13
query.setPage(Math.max(page, 1));
query.setPageSize(Math.min(Math.max(page_size, 1), 500));

// ✅ 正确：@ModelAttribute 自动绑定 + Query 内部 clamp
public ApiResponse<PageResult<StockPanelVO>> page(@Valid @ModelAttribute StockPanelQuery query) {
    return ApiResponse.ok(stockInfoService.page(query));
}
```

### 3.7 ❌ 禁止：事务 / 线程池 / 外部调用编排

| 禁止项 | 归属 |
|---|---|
| `@Transactional` | Service |
| `Executors.new*` | Spring `@Bean` |
| 多次外部 API 调用的编排与容错 | Service（见 `Service层规范.md` §2.6）|
| 直接调用 `CollectorService` 拼 collector 参数 | Service（Controller 只调 Service）|

---

## 4. 决策流程（写代码时照着走）

```
我要写一个接口
  │
  ├─ 参数怎么进？
  │   ├─ JSON 体 + ≥3 字段 / 需校验 → @Valid @RequestBody XxxRequest
  │   ├─ JSON 体 + 1~2 字段      → 仍建 XxxRequest（保持契约稳定）
  │   ├─ query string 多条件      → @Valid @ModelAttribute XxxQuery
  │   ├─ query string 单标量      → @RequestParam
  │   └─ 路径变量                 → @PathVariable("name")（显式命名）
  │
  ├─ 逻辑放哪？
  │   ├─ 格式/范围/必填            → DTO 注解
  │   ├─ 存在性/状态/一致性        → Service
  │   └─ 纯搬运/转换              → Service + Converter
  │
  ├─ 返回什么？
  │   ├─ 有结构 → ApiResponse<XxxVO>
  │   ├─ 无内容 → ApiResponse<Void> + ApiResponse.ok()
  │   ├─ 创建   → ApiResponse.created(XxxVO)
  │   └─ 原样透传外部结构 → 明文豁免，ResponseEntity<Map>
  │
  └─ 出错怎么表达？
      ├─ 业务错误 → Service 抛 BusinessException(code, msg)
      ├─ 格式错误 → @Valid 注解 → 422
      └─ Controller 永不 try-catch
```

---

## 5. Controller 方法模板

### 5.1 查询（返回 VO）

```java
@GetMapping("/{symbol}")
public ApiResponse<StockInfoVO> one(@PathVariable("symbol") String symbol) {
    return ApiResponse.ok(stockInfoService.get(symbol));
}
```

### 5.2 分页查询

```java
@GetMapping
public ApiResponse<PageResult<StockPanelVO>> page(@Valid @ModelAttribute StockPanelQuery query) {
    return ApiResponse.ok(stockInfoService.page(query));
}
```

### 5.3 创建（返回 201）

```java
@PostMapping("/pools")
public ApiResponse<PoolVO> create(@Valid @RequestBody PoolCreateRequest request) {
    return ApiResponse.created(poolService.create(request));
}
```

### 5.4 更新（PATCH，包装类型 DTO）

```java
@PatchMapping("/{symbol}")
public ApiResponse<StockInfoVO> patch(
        @PathVariable("symbol") String symbol, @Valid @RequestBody StockUpdateRequest request) {
    return ApiResponse.ok(stockInfoService.patch(symbol, request));
}
```

### 5.5 删除（无返回体）

```java
@DeleteMapping("/{id}")
public ApiResponse<Void> delete(@PathVariable("id") int id) {
    poolService.delete(id);
    return ApiResponse.ok();
}
```

### 5.6 子资源操作

```java
@PostMapping("/{id}/members")
public ApiResponse<PoolAddMembersVO> addMembers(
        @PathVariable("id") int id, @Valid @RequestBody PoolMembersRequest request) {
    return ApiResponse.ok(poolService.addMembers(id, request));
}
```

---

## 6. Code Review 清单

| # | 检查项 | 违规信号 |
|---|---|---|
| 1 | Controller 里有业务 `if`？ | `if` 分支里出现「查库结果判断」「状态冲突」 |
| 2 | 返回值放弃了泛型？ | `ApiResponse<?>` |
| 3 | 手拼 `Map` 响应？ | `Map.of("message", ...)` / `Map.of("xxx_count", ...)` |
| 4 | 注入了 Mapper？ | `private final XxxMapper` |
| 5 | 注入了 `CollectorService` / 外部客户端？ | `private final CollectorService` |
| 6 | 在 Controller 里做 PO→VO 转换？ | `new XxxVO()` + 一串 `setXxx` |
| 7 | `@RequestBody` 缺 `@Valid`？ | `@RequestBody XxxRequest` 无 `@Valid` |
| 8 | `@PathVariable` 未显式命名？ | `@PathVariable String symbol` |
| 9 | 手工装配 Query？ | `new XxxQuery()` + `query.setXxx` |
| 10 | page/pageSize clamp 散落？ | `Math.max(page, 1)` 出现在 Controller |
| 11 | try-catch 兜异常？ | `catch (Exception e) { return ApiResponse.fail(...) }` |
| 12 | `@Transactional`？ | 出现在 Controller |
| 13 | 自己 new 线程池？ | `Executors.new*` |
| 14 | 尾斜杠风格混用？ | 同一资源域 `/pools` 与 `/pools/` 并存 |

---

## 7. 新增 Controller 的检查清单

- [ ] 类级 `@RequestMapping` 写完整资源路径，**不带尾斜杠**
- [ ] 返回 `ApiResponse<XxxVO>` / `ApiResponse<Void>`，**没有 `?`**
- [ ] `@PathVariable` **全部显式命名**
- [ ] `@RequestBody` **全部带 `@Valid`**
- [ ] 多条件查询用 `@ModelAttribute XxxQuery`，无手工 `query.setXxx`
- [ ] `page` / `pageSize` 的 clamp 在 **Query 内部**，Controller 不出现 `Math.max`
- [ ] 只依赖 `Service`，**没有 Mapper / CollectorService**
- [ ] **没有业务 `if`**、没有 PO→VO 转换
- [ ] 没有 `Map.of("message", ...)` 手拼响应
- [ ] 没有 try-catch、没有 `@Transactional`、没有 `Executors.new*`
- [ ] 鉴权信息从 `Authorization` / `HttpServletRequest` 取，不接受前端传

---

## 8. 技术前提（环境事实，长期有效）

| 项 | 值 | 来源 |
|---|---|---|
| Web 框架 | Spring Boot 3.2.5 / Spring MVC | `pom.xml` |
| 统一响应 | `{code, message, data}`，`ApiResponse.ok/created/fail` | `attribution-common/response/ApiResponse.java` |
| 分页出参 | `PageResult<T>` | `attribution-common/response/PageResult.java` |
| 参数校验 | Jakarta Bean Validation（`@Valid`）| `jakarta.validation.*` |
| 校验失败 | 422，返回**全部**字段错误（`joining("; ")`）| `GlobalExceptionHandler` |
| 业务异常 | `BusinessException(code, message)`，`code` 即 HTTP 状态码 | `attribution-common/exception/` |
| 全局异常处理 | `GlobalExceptionHandler`：业务异常 → 对应状态码；兜底 → 500 不泄漏堆栈 | `attribution-common/exception/` |
| Jackson 命名策略 | `SNAKE_CASE`（**只影响 JSON，不影响 query string 绑定**）| `application.yml` |
| 跨域 | 仅放开 `/api/**` | `WebConfig` |
| 依赖注入 | Lombok `@RequiredArgsConstructor` 构造器注入（**禁止字段注入**，详见 `../横切技术规范/依赖注入与Bean规范.md`）| 各 Controller |
| 编译参数 | `-parameters` **已开启**（`<parameters>true</parameters>`），故 `@PathVariable` 隐式命名当前可用——但仍**要求显式命名**以免换构建工具时静默失效 | 父 `pom.xml` → `maven-compiler-plugin` |
| 透传豁免 | Python collector 的结构原样转发，允许 `Map` | `../../开发文档/采集模块/采集模块现状文档（三类采集：增量-全量覆盖-实时查询）.md` §4.4 |

---

## 9. 与其他文档的关系

| 文档 | 管什么 |
|---|---|
| **`Controller层规范.md`（本文）** | Controller 的**路径、绑定、校验、响应、豁免**、Code Review 清单 |
| `Service层规范.md` | Service 层**该做什么、不该做什么**、事务、跨模块协作 |
| `POJO规范.md` | DTO / PO / VO / BO 的**定义规范**：字段类型、校验注解、Converter 写法 |
| `Mapper层规范.md` | **持久化唯一入口**：XML 写法、批量与聚合、视图行定义、分页 |
| `../审计与整改/` | **历史快照**：某次整改的实测数字，勿作为规范依据 |

> 分工：**「用什么形状传递数据」看 `POJO规范.md`；「哪层负责什么」看三份分层规范。**

---

> **本文档只写规则，不含任何现状计数。**
> 新增接口请按 §6（Code Review 清单）与 §7（新增 Controller 检查清单）自查；
> 改动路径 / 参数名 / 响应字段时，**必须同步前端 TS**——
> Jackson `SNAKE_CASE` 会让字段名改动对前端**静默失效**（拿到 `undefined` 而不报错）。

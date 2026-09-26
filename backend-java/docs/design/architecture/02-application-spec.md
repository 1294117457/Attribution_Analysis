# application 层规范

> 一个方法 = 一个用户意图。管事务、管缓存。

## 1. 包结构

```
com.attribution.application/
└── service/        AppService（用例编排）
```

> ⚠️ **当前代码现状**：实际路径是 `service/`（顶级包），与文档定义的 `application/service/` 有偏差。  
> 迁移期间保持兼容，规范以 `application/service/` 为目标。

## 2. AppService 规范

### 一个方法 = 一个用例

- 方法名就是用户意图：`createPool` / `cancelOperation` / `queryPanel`
- ❌ `save` / `process` / `do` / `handle`

### 注解使用

| 场景 | 注解 |
|------|------|
| 写操作 | `@Transactional`（类级或方法级） |
| 读操作 | `@Transactional(readOnly = true)` |
| 缓存读 | `@Cacheable`（方法级） |
| 清除缓存 | `@CacheEvict` |

### 标准步骤

```java
public PoolVO createPool(PoolCreateRequest req) {
    // 1. 入参校验（Request 自带 @Valid）
    // 2. 查 / 构造 entity
    // 3. 调 domain（entity 方法 或 DomainService）
    // 4. 持久化（repository）
    // 5. 返回 VO（DTO 在 controller 装配，AppService 也可直接返回 entity 装配结果）
}
```

### 禁止

- 注入 `HttpClient` / `RestTemplate` / 第三方 SDK 具体类
- 写业务算法（→ `domain/service`）
- ❌ **直接接 `interface/dto/*Request` 入参**（详见 §2.4）
- ❌ **直接返回 `interface/dto/*VO`**（详见 §2.4）

### 2.4 DTO 边界（铁律）

> AppService 应该是**业务用例的编排**，不直接耦合对外接口的 Request / Response。

#### 入参边界

```java
// ❌ 错误：AppService 直接接 DTO Request
public PoolVO createPool(PoolCreateRequest req) { ... }

// ✅ 正确：AppService 接收"业务命令对象"（domain 内的 record / 内部类）
public PoolVO createPool(CreatePoolCommand cmd) {
    // command 是 domain 内的不可变对象
}

// ✅ 过渡方案（当前存量代码）：接 DTO Request，但 Controller 做一次浅转换
// Controller:
PoolVO vo = poolAppService.createPool(PoolCreateCommand.from(req));
// AppService:
public PoolVO createPool(PoolCreateCommand cmd) { ... }
```

#### 出参边界

```java
// ❌ 错误：AppService 直接返回 DTO VO
public StockPanelResponse queryPanel(StockPanelQuery query) { ... }

// ✅ 正确：AppService 返回 entity / domain VO，由 controller 装配
public List<StockPanelRowEntity> queryPanelRows(StockPanelQuery query) { ... }

// ✅ 过渡方案（当前存量代码）：AppService 返回 DTO VO
// Controller 拿到 VO 后再包一层返回，或直接透传
// 标注为"已知违规"，后续 PR 收口
```

#### 为什么

- DTO 是**对外格式**（HTTP 序列化、JSON 注解、Swagger 注解）。
- AppService 是**业务用例**，被 controller 之外的入口（如 RPC、GraphQL、消息消费）调用时，DTO 可能不同。
- 一旦 AppService 强依赖 DTO，**换协议要全改 AppService**。

### 示例（标准写法）

```java
@Service
@RequiredArgsConstructor
public class PoolOperationAppService {

    private final PoolOperationRepository opRepo;
    private final KlineCollectionExecutor klineCollector;

    @Transactional
    public PoolOperationEntity startKlineCollection(StartKlineCollectCommand cmd) {
        // 1. 构造 entity
        PoolOperationEntity op = PoolOperationEntity.start(cmd);

        // 2. 持久化
        op = opRepo.save(op);

        // 3. 调外部（直接调 adapter，暂无 port 抽象）
        klineCollector.dispatch(op);

        return op;   // 返回 entity，由 controller 装配 VO
    }
}
```

## 3. Application Command（业务命令对象）

> 当 AppService 不直接接 DTO Request 时，需要在 application 层定义**业务命令对象**。

### 3.1 命名

| 类型 | 命名 | 例 |
|------|------|----|
| 命令对象（写操作） | `XxxCommand` | `CreatePoolCommand`、`StartKlineCollectCommand` |
| 查询对象（读操作） | `XxxQuery` | `PanelQuery`、`KlineHistoryQuery` |
| 结果对象（业务级） | `XxxResult` | `PoolOperationResult` |

### 3.2 位置

```
application/
  ├── command/      XxxCommand（写用例）
  ├── query/        XxxQuery（读用例）
  └── result/       XxxResult（业务级结果）
```

> 💡 **也可以放在 domain 内**：因为 command / query 本质也是"业务数据"。具体位置由团队约定，推荐 `application/`，与 domain 解耦。

### 3.3 与 DTO Request 的关系

```
HTTP Request (interface/dto/{module}/*Request)
    ↓ Controller 做浅转换（同名字段拷贝）
Command/Query (application/command/{X}Command)
    ↓ AppService 处理
entity / DomainVO
    ↓ Controller 装配
HTTP Response (interface/dto/{module}/*VO)
```

> **存量代码兼容**：当前 AppService 直接接 DTO Request / 返回 DTO VO 视为过渡方案，不阻塞业务开发。后续 PR 按模块迁移。

## 4. 跨层依赖

```
application/service/
  ├──→ domain/entity                ✅
  ├──→ domain/vo（DomainVO）         ✅
  ├──→ domain/repository            ✅
  ├──→ domain/service               ✅
  ├──→ infrastructure/adapter        ✅（通过 port 接口）
  │
  ├──× interface/dto/*Request 入参    ❌（过渡方案允许）
  ├──× interface/dto/*VO 返回        ❌（过渡方案允许）
  └──× interface/controller         ❌（AppService 不感知 controller）
```

## 5. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-25 | -      | 初稿 |
| v0.2  | 2026-09-25 | -      | 新增 DTO 边界铁律（§2.4）；新增 Command/Query/Result 概念（§3）；明确当前代码现状与过渡方案 |

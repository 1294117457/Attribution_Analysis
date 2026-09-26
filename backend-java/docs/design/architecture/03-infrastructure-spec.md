# infrastructure 层规范

> 外部世界的所有实现都在这里。

## 1. 包结构

```
com.attribution.infrastructure/
├── adapter/        外部 SDK 适配器（Tushare / AkShare / pytdx）
├── persistence/    repository 实现（JPA）
├── query/          复杂查询实现（Repository 复杂查询的专用实现）
├── config/         Spring Bean / 外部客户端
└── exception/      业务异常类
```

> ⚠️ domain 层**不允许**依赖 infrastructure（详见 `01-domain-spec.md §6`）。

## 2. Adapter 规范

### 职责

- 包装外部 SDK（Tushare / AkShare / pytdx）
- 被 AppService 直接调用（暂无 port 抽象）

### 命名

| 类型 | 命名 |
|------|------|
| 外部 SDK 客户端 | `XxxClient` / `XxxCollector` / `XxxExecutor` |
| 调度任务 | `XxxScheduler` |

### 禁止

- ❌ 注入或返回 `interface/dto/*VO`
- ❌ 把 `IOException` / `TimeoutException` / `RestClientException` 直接抛给上层
- ✅ 统一抛 `BusinessException` 子类
- ✅ 返回 entity 或 domain VO（数据装配由 controller 完成）

### 示例

```java
@Component
@RequiredArgsConstructor
public class KlineCollectionExecutor {

    private final TushareApiClient tushare;

    public KlineCollectionResult dispatch(PoolOperationEntity op) {   // 返回 entity / domain VO
        try {
            List<KlineEntity> data = tushare.fetchKline(op.stockCode(), op.startDate());
            // ... 持久化 ...
        } catch (RestClientException e) {
            throw new CollectionException("K线采集失败: " + op.stockCode(), e);
        }
        return KlineCollectionResult.of(op.id(), fetchedCount);
    }
}
```

## 3. Persistence 规范

### 3.1 两种实现方式

**A. Spring Data JPA（推荐）**

```java
// domain/repository/StockPoolRepository.java
public interface StockPoolRepository extends JpaRepository<StockPoolEntity, Long> {
    Optional<StockPoolEntity> findByName(String name);
}
```

不写实现类——Spring 自动生成。需要 `@EnableJpaRepositories(basePackages = "com.attribution.infrastructure.persistence")`。

**B. 自定义实现**

```java
@Repository
public class StockPoolRepositoryImpl implements StockPoolRepository {

    @PersistenceContext
    private EntityManager em;

    @Override
    public List<StockPoolEntity> findActivePools() {
        // 自定义 JPQL / Criteria API
    }
}
```

### 3.2 Query 复杂查询（独立子包）

> 复杂查询（如多表 JOIN、窗口函数、聚合）建议放 `infrastructure/query/`，**不放在 `persistence/`**。

```
infrastructure/
  ├── persistence/    简单 repository 实现
  └── query/          复杂查询（自定义 SQL / 视图 / 多表 JOIN）
```

**目录约定**：

```java
// domain/repository/StockPanelComposeRepository.java
public interface StockPanelComposeRepository {
    List<StockPanelRowEntity> queryPanel(StockPanelQuery query);
    long countPanel(StockPanelQuery query);
}

// infrastructure/query/StockPanelComposeRepositoryImpl.java
@Repository
@RequiredArgsConstructor
public class StockPanelComposeRepositoryImpl implements StockPanelComposeRepository {

    private final JdbcTemplate jdbc;

    @Override
    public List<StockPanelRowEntity> queryPanel(StockPanelQuery query) {
        // 自定义 SQL，返回 entity
    }
}
```

### 3.3 禁止

- 在实现里写业务逻辑
- ❌ **直接返回 DTO**（要返回 entity / domain VO）
- ❌ **接收 `interface/dto/*Query` 之外的 DTO 入参**

> **理由**：Persistence 实现是 Repository 接口的实现，Repository 接口本身不返回 DTO（详见 `01-domain-spec.md §4.3`），实现类也不能返回 DTO。

## 4. Config 规范

### 分类

| 类型 | 命名 | 例 |
|------|------|----|
| 配置属性 | `XxxProperties` | `TushareProperties` |
| 客户端 Bean | `XxxConfig` | `WebClientConfig` |
| 跨切面 | `XxxAspect` | `CacheConfig` |
| CORS / 拦截器 | `XxxConfig` | `CorsConfig` |

### 必须

- `@ConfigurationProperties` 类要标 `@Validated`
- 客户端 Bean（RestTemplate / WebClient）放 config，不要散落在 adapter 里

### 禁止

- 把业务逻辑写进 config
- 在 config 里 `new` entity
- ❌ 引用或暴露 `interface/dto/*VO`

## 5. Exception 规范

### 分层

| 类型 | 基类 | 例 |
|------|------|----|
| 领域异常 | `DomainException` | `PoolNotFoundException` |
| 业务异常 | `BusinessException` | `PoolFullException` |
| 外部异常 | `CollectionException` | `TushareApiException` |

### 命名

- 统一后缀 `Exception`
- 命名表达"业务含义"，不是"技术错误"：
  - ✅ `PoolNotFoundException`
  - ❌ `PoolQueryEmptyException`

### 携带信息

```java
@Getter
public class PoolNotFoundException extends DomainException {
    private final Long poolId;

    public PoolNotFoundException(Long poolId) {
        super("股票池不存在: " + poolId);
        this.poolId = poolId;
    }
}
```

### 禁止

- 直接抛 `RuntimeException` / `IllegalStateException`
- 用异常做流程控制
- ❌ exception 携带 `interface/dto/*VO` 作为字段（异常不应耦合对外格式）

## 6. GlobalExceptionHandler 归属

`GlobalExceptionHandler` 本质是 `@RestControllerAdvice`，**属于 interface 层**（不是 infrastructure）。

- 放在 `interface/handler/` 或 `controller/exception/`
- 职责：把 domain/infra 异常映射成 HTTP 状态码 + 统一响应体

## 7. 跨层依赖

```
infrastructure/
  ├── adapter/
  │     ↑ 实现 domain.port（如有）
  │     ├──→ domain/entity         ✅
  │     ├──→ domain/vo             ✅
  │     └──× interface/dto         ❌
  │
  ├── persistence/
  │     ├──→ domain/entity         ✅
  │     ├──→ domain/vo             ✅
  │     └──× interface/dto         ❌
  │
  ├── query/
  │     ├──→ domain/entity         ✅
  │     ├──→ domain/vo             ✅
  │     └──× interface/dto         ❌
  │
  ├── config/
  │     └──× domain / interface    ❌
  │
  └── exception/
        └──× interface/dto         ❌（异常不带 DTO）
```

## 8. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-25 | -      | 初稿 |
| v0.2  | 2026-09-25 | -      | 新增 `query/` 子包规范（§3.2）；明确 Adapter / Persistence / Config / Exception 均不允许引用 DTO（§3.3 / §4 / §5 / §7） |

# 分层架构设计

## 一、整体架构

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        API Layer (Controllers)                      │
│   StockController  │  PoolController  │  KlineController  │ ...   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                      Application Layer (Services)                     │
│   StockPoolService  │  PoolOperationService  │  StockAnalysisService │
│   KlineService      │  DataCollectionService                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                        Domain Layer (Entities)                       │
│   StockPool  │  PoolMember  │  Kline  │  StockInfo  │  Concept     │
│   ─────────────────────────────────────────────────────────────────  │
│   Value Objects: StockCode, TradeDate, PoolType                      │
│   Domain Events: PoolCreated, MemberAdded, KlineCollected            │
│   Domain Exceptions: PoolDomainError, KlineDataError                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                    Infrastructure Layer                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐│
│  │ Repository  │  │ Data Source  │  │    External Services        ││
│  │  (JPA)     │  │  Adapters    │  │                            ││
│  │             │  │              │  │  TushareFetcher (HTTP)    ││
│  │ StockRepo   │  │ TushareConfig│  │  PytdxFetcher (TCP)       ││
│  │ KlineRepo   │  │ PostgreSQL   │  │  AkShareFetcher (HTTP)    ││
│  │ PoolRepo    │  │ Flyway       │  │                            ││
│  └─────────────┘  └──────────────┘  └────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 层级职责

| 层级 | 职责 | Java 实现 |
|---|---|---|
| **API Layer** | HTTP 请求处理、参数校验、响应包装 | `@RestController` + `@Valid` |
| **Application Layer** | 用例编排、事务边界、DTO 转换 | `@Service` + `@Transactional` |
| **Domain Layer** | 业务规则、聚合根、值对象、领域事件 | `@Entity` + `@Embeddable` + `DomainEvent` |
| **Infrastructure Layer** | 数据库访问、外部 API 调用、技术实现 | `@Repository` + `WebClient` + `@Component` |

### 1.3 与 Python FastAPI 项目的对应关系

```
Python FastAPI                      Java Spring Boot
─────────────────────────────────────────────────────────────────────
src/route/api/v1/*.py      →      src/main/java/*/controller/
src/application/*.py       →      src/main/java/*/service/
src/domain/*/entity.py      →      src/main/java/*/domain/entity/
src/domain/*/schemas.py    →      src/main/java/*/dto/
src/infrastructure/repos/  →      src/main/java/*/repository/
src/infrastructure/collectors →   src/main/java/*/adapter/collector/
```

## 二、DDD 领域模型设计

### 2.1 聚合根划分

| 聚合根 | 核心实体 | 边界内实体 | 边界外引用 |
|---|---|---|---|
| **StockPool** | StockPool, PoolMember | PoolOperation | StockInfo (via symbol) |
| **Kline** | Kline | - | StockInfo (via symbol) |
| **StockInfo** | StockInfo | Industry, Market | - |
| **Concept** | Concept | ConceptMember | StockInfo (via symbol) |

### 2.2 领域事件

Java Spring 支持通过 `ApplicationEventPublisher` 实现领域事件：

```java
// Domain Event
public record PoolCreatedEvent(Long poolId, String poolName) { }

// Aggregate Root
@Entity
public class StockPool {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    // Domain event publisher
    @Autowired
    @Transient
    private ApplicationEventPublisher eventPublisher;

    public void rename(String newName) {
        this.name = newName;
        eventPublisher.publishEvent(new PoolRenamedEvent(this.id, newName));
    }
}
```

### 2.3 值对象

使用 `@Embeddable` 实现值对象：

```java
@Embeddable
public record StockCode(String value) {
    public StockCode {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("Stock code cannot be empty");
        }
    }
}

@Embeddable
public record TradeDate(LocalDate date) {
    public TradeDate {
        Objects.requireNonNull(date);
    }
}

@Embeddable
public record PoolType(String code, String label) {
    public static final PoolType WATCHLIST = new PoolType("watchlist", "自选");
    public static final PoolType CUSTOM = new PoolType("custom", "自定义");

    public static PoolType fromCode(String code) {
        return switch (code) {
            case "watchlist" -> WATCHLIST;
            case "custom" -> CUSTOM;
            default -> new PoolType(code, code);
        };
    }
}
```

## 三、包结构

```
src/main/java/com/attribution/
├── AttributionApplication.java          # Spring Boot 启动类
│
├── controller/                          # API 层
│   ├── StockController.java
│   ├── PoolController.java
│   ├── KlineController.java
│   ├── ConceptController.java
│   └── dto/                            # Request/Response DTO
│       ├── PoolCreateRequest.java
│       ├── PoolVO.java
│       └── KlineQueryRequest.java
│
├── service/                            # 应用层
│   ├── StockPoolService.java
│   ├── PoolOperationService.java
│   ├── KlineService.java
│   ├── StockAnalysisService.java
│   └── DataCollectionService.java
│
├── domain/                             # 领域层
│   ├── entity/                         # 聚合根 + 实体
│   │   ├── StockPool.java
│   │   ├── PoolMember.java
│   │   ├── Kline.java
│   │   ├── StockInfo.java
│   │   └── Concept.java
│   ├── vo/                             # 值对象
│   │   ├── StockCode.java
│   │   ├── TradeDate.java
│   │   └── PoolType.java
│   ├── event/                          # 领域事件
│   │   ├── PoolCreatedEvent.java
│   │   ├── MemberAddedEvent.java
│   │   └── KlineCollectedEvent.java
│   └── exception/                      # 领域异常
│       ├── PoolDomainException.java
│       └── KlineDataException.java
│
├── repository/                         # 基础设施层 - Repository
│   ├── StockPoolRepository.java        # 接口
│   ├── StockPoolRepositoryImpl.java   # JPA 实现
│   ├── KlineRepository.java
│   └── StockRepository.java
│
├── adapter/                            # 适配器层
│   ├── collector/                      # 数据采集适配器
│   │   ├── TushareCollector.java
│   │   ├── PytdxCollector.java
│   │   └── AkShareCollector.java
│   └── http/                           # HTTP 客户端适配器
│       └── TushareApiClient.java
│
├── config/                             # 配置类
│   ├── AppConfig.java
│   ├── WebClientConfig.java
│   └── TushareConfig.java
│
└── exception/                          # 全局异常处理
    ├── GlobalExceptionHandler.java
    └── ErrorResponse.java
```

## 四、关键设计模式

### 4.1 Repository 模式

Python SQLAlchemy:
```python
class StockPoolRepoImpl:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_id(self, id: int) -> Optional[StockPool]:
        result = await self._session.execute(
            select(StockPoolDB).where(StockPoolDB.id == id)
        )
        ...
```

Java JPA:
```java
public interface StockPoolRepository extends JpaRepository<StockPoolDB, Long> {
    Optional<StockPoolDB> findById(Long id);
    List<StockPoolDB> findByIsArchivedFalse();
}

@Service
@Transactional(readOnly = true)
public class StockPoolRepositoryImpl implements StockPoolRepository {
    private final JpaRepository<StockPoolDB, Long> jpaRepository;

    @Override
    public Optional<StockPool> findById(Long id) {
        return jpaRepository.findById(id)
            .map(this::toDomain);
    }
}
```

### 4.2 Strategy 模式（采集器注册中心）

Python:
```python
class FetcherRegistry:
    _providers: dict[type, object] = {}

    def register_instance(self, protocol, instance): ...
    def get(self, protocol): ...
```

Java:
```java
@Component
public class CollectorRegistry {
    private final Map<Class<?>, Collector> collectors = new HashMap<>();

    public <T extends Collector> void register(Class<T> type, T collector) {
        collectors.put(type, collector);
    }

    @SuppressWarnings("unchecked")
    public <T extends Collector> T get(Class<T> type) {
        Collector collector = collectors.get(type);
        if (collector == null) {
            throw new IllegalStateException("No collector registered for: " + type);
        }
        return (T) collector;
    }
}
```

### 4.3 Builder 模式（复杂 DTO）

```java
public class StockAnalysisResponse {
    private StockInfoVO stock;
    private TechnicalSummaryVO summary;
    private List<KlineWithIndicatorVO> klines;
    private List<PoolMembershipVO> pools;

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private StockAnalysisResponse response = new StockAnalysisResponse();

        public Builder stock(StockInfoVO stock) {
            response.stock = stock;
            return this;
        }

        public Builder summary(TechnicalSummaryVO summary) {
            response.summary = summary;
            return this;
        }

        public StockAnalysisResponse build() {
            return response;
        }
    }
}
```

## 五、事务边界

### 5.1 应用服务层事务

```java
@Service
public class StockPoolService {
    private final StockPoolRepository repository;

    @Transactional
    public PoolVO createPool(PoolCreateRequest request) {
        StockPool pool = StockPool.create(
            request.getName(),
            PoolType.fromCode(request.getPoolType())
        );
        StockPool saved = repository.save(pool);
        return PoolVO.fromEntity(saved);
    }
}
```

### 5.2 跨库操作（采集任务）

```java
@Service
public class DataCollectionService {
    private final TushareCollector tushareCollector;
    private final KlineRepository klineRepository;

    @Transactional
    public KlineCollectResult collect(String symbol, int days) {
        // 1. 调用外部 API
        List<KlineDTO> klines = tushareCollector.fetchKlines(symbol, days);

        // 2. 批量写入数据库
        List<Kline> entities = klines.stream()
            .map(this::toEntity)
            .toList();

        klineRepository.saveAll(entities);

        return new KlineCollectResult(symbol, entities.size());
    }
}
```

## 六、异常处理

### 6.1 全局异常处理器

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(PoolNotFoundException.class)
    public ResponseEntity<ErrorResponse> handlePoolNotFound(PoolNotFoundException ex) {
        return ResponseEntity
            .status(HttpStatus.NOT_FOUND)
            .body(ErrorResponse.of(404, ex.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        List<String> errors = ex.getBindingResult().getFieldErrors()
            .stream()
            .map(e -> e.getField() + ": " + e.getDefaultMessage())
            .toList();

        return ResponseEntity
            .status(HttpStatus.UNPROCESSABLE_ENTITY)
            .body(ErrorResponse.of(422, "Validation failed", errors));
    }

    @ExceptionHandler(CollectionException.class)
    public ResponseEntity<ErrorResponse> handleCollection(CollectionException ex) {
        return ResponseEntity
            .status(HttpStatus.BAD_GATEWAY)
            .body(ErrorResponse.of(502, ex.getMessage()));
    }
}
```

## 七、配置外部化

### 7.1 application.yml

```yaml
spring:
  application:
    name: attribution-analysis

  datasource:
    url: ${DATABASE_URL:jdbc:postgresql://localhost:5432/attribution}
    username: ${DATABASE_USERNAME:postgres}
    password: ${DATABASE_PASSWORD:postgres}
    driver-class-name: org.postgresql.Driver
    hikari:
      maximum-pool-size: 200
      minimum-idle: 10

  jpa:
    hibernate:
      ddl-auto: validate  # 不自动创建，仅验证
    show-sql: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        format_sql: true

  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true

tushare:
  token: ${TUSHARE_TOKEN:}
  base-url: https://api.tushare.pro
  timeout: 30000

server:
  port: ${SERVER_PORT:8000}
```

### 7.2 多环境配置

```
src/main/resources/
├── application.yml              # 默认配置
├── application-dev.yml          # 开发环境
├── application-prod.yml         # 生产环境
└── db/migration/
    └── V1__init_schema.sql     # Flyway 迁移脚本
```

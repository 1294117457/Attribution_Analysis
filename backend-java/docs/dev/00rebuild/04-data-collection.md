# 数据采集设计

> 这是重构中**复杂度最高**的模块。Python 项目的核心价值就在数据采集流水线：tushare + pytdx + akshare → PostgreSQL。Java 重写最大的风险点也在此。

## 一、采集器架构

### 1.1 整体设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CollectorRegistry (Spring Bean)                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ TushareCollector │  │  PytdxCollector  │  │ AkShareCollector │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘ │
│           │                      │                      │            │
└───────────┼──────────────────────┼──────────────────────┼────────────┘
            │                      │                      │
┌───────────▼──────────────────────▼──────────────────────▼──────────┐
│                    WebClient / Netty (HTTP/TCP)                        │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────┐
│                        External APIs                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐│
│  │ Tushare Pro  │  │   Pytdx      │  │  AKShare     │  │  Tushare   ││
│  │ (HTTP REST)  │  │ (TCP Binary) │  │ (HTTP REST)  │  │   Basic    ││
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘│
└───────────────────────────────────────────────────────────────────────┘
```

### 1.2 Collector 接口设计

```java
package com.attribution.adapter.collector;

/**
 * 数据采集器接口
 */
public interface Collector {

    /**
     * 采集器名称
     */
    String name();

    /**
     * 执行采集任务
     */
    CollectionResult collect(CollectionRequest request);
}

public record CollectionRequest(
    String symbol,
    LocalDate startDate,
    LocalDate endDate,
    Map<String, String> options
) {}

public record CollectionResult(
    String symbol,
    int fetchedCount,
    int savedCount,
    List<String> errors
) {}
```

## 二、Tushare 采集器

### 2.1 Python 原实现分析

```python
# Python: infrastructure/collectors/tushare.py
class TushareFetcher:
    def __init__(self, bo_type: type[KlineBO]):
        self._pro = TushareProApi()  # 内部维护 requests.Session

    def daily(self, ts_code: str, start_date: str, end_date: str) -> list[KlineBO]:
        df = self._pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        return [KlineBO.from_dict(row.to_dict()) for row in df.itertuples()]
```

关键点：
- 使用 `requests.Session` 保持连接池
- Tushare Pro API 返回 pandas DataFrame
- 内部有 token 管理和重试逻辑

### 2.2 Java 实现

```java
@Component
@RequiredArgsConstructor
@Slf4j
public class TushareCollector implements Collector {

    private final WebClient webClient;
    private final TushareProperties properties;

    @Override
    public String name() {
        return "Tushare";
    }

    @Override
    public CollectionResult collect(CollectionRequest request) {
        try {
            List<TushareKlineDTO> klines = fetchDailyKlines(
                request.symbol(),
                request.startDate(),
                request.endDate()
            );

            List<TechKlineDailyEntity> entities = klines.stream()
                .map(this::toEntity)
                .toList();

            klineRepository.saveAll(entities);

            return CollectionResult.success(request.symbol(), entities.size());
        } catch (Exception e) {
            log.error("Tushare collect failed: {}", request.symbol(), e);
            return CollectionResult.failed(request.symbol(), e.getMessage());
        }
    }

    private List<TushareKlineDTO> fetchDailyKlines(
            String symbol, LocalDate startDate, LocalDate endDate) {

        Map<String, Object> body = new HashMap<>();
        body.put("api_name", "daily");
        body.put("token", properties.getToken());
        body.put("params", Map.of(
            "ts_code", symbol,
            "start_date", startDate.format(DateTimeFormatter.BASIC_ISO_DATE),
            "end_date", endDate.format(DateTimeFormatter.BASIC_ISO_DATE)
        ));
        body.put("fields", "ts_code,trade_date,open,high,low,close,vol,amount");

        TushareResponse response = webClient.post()
            .uri(properties.getBaseUrl())
            .bodyValue(body)
            .retrieve()
            .bodyToMono(TushareResponse.class)
            .block(Duration.ofSeconds(properties.getTimeout()));

        if (response == null || response.getCode() != 0) {
            throw new RuntimeException("Tushare API error: " + response);
        }

        return response.getData().getItems().stream()
            .map(this::parseKlineItem)
            .toList();
    }
}
```

### 2.3 Tushare API 响应解析

```java
@Data
public class TushareResponse {
    private int code;
    private String msg;
    private TushareData data;
}

@Data
public class TushareData {
    private List<String> fields;
    private List<List<Object>> items;
}

public class TushareKlineDTO {
    private String tsCode;
    private LocalDate tradeDate;
    private Double open;
    private Double high;
    private Double low;
    private Double close;
    private Long volume;
    private Double amount;
}
```

### 2.4 配置

```java
@Configuration
@ConfigurationProperties(prefix = "tushare")
public class TushareProperties {
    private String token;
    private String baseUrl = "http://api.tushare.pro";
    private int timeout = 30_000;
    private int maxRetries = 3;
}
```

```yaml
# application.yml
tushare:
  token: ${TUSHARE_TOKEN:}
  base-url: http://api.tushare.pro
  timeout: 30000
  max-retries: 3
```

## 三、Pytdx 采集器

### 3.1 Python 原实现分析

```python
# Python: infrastructure/collectors/pytdx.py
class PytdxFetcher:
    def __init__(self):
        self._tdx = TdxExHq_API(heartbeat=True)

    def connect(self):
        return self._tdx.connect('72.14.215.115', 7709)

    def fetch_minute(self, code: str, market: int) -> pd.DataFrame:
        data = self._tdx.get_security_bars(...)
        return pd.DataFrame(data)
```

关键点：
- Pytdx 维护 TCP 长连接
- 需要心跳保活
- 返回二进制数据需要解析

### 3.2 Java 实现（简化版）

Pytdx 协议是私有的二进制协议，实现较复杂。建议方案：

**方案 A**：用 Java 直接实现 Pytdx 协议（工程量大）
**方案 B**：封装 Python Pytdx 为 HTTP 服务，Java 调用（推荐）
**方案 C**：仅用 Tushare，放弃 Pytdx 分钟K线（最简单）

```java
/**
 * Pytdx 分钟K线采集器
 *
 * 由于 Pytdx 使用私有二进制协议，建议采用以下方案之一：
 * 1. 将 Python pytdx 封装为 HTTP 微服务
 * 2. 使用 AkShare 作为分钟K线来源
 *
 * 当前实现为占位符，实际功能通过外部服务调用
 */
@Component
@Slf4j
public class PytdxCollector implements MinuteKlineCollector {

    private final RestTemplate restTemplate;
    private final PytdxProperties properties;

    @Override
    public String name() {
        return "Pytdx";
    }

    @Override
    public List<MinuteKlineDTO> fetchMinuteKlines(String symbol, int market, int count) {
        // 调用 Python Pytdx HTTP 服务
        String url = properties.getBaseUrl() + "/api/minute/" + symbol;

        PytdxMinuteResponse response = restTemplate.getForObject(
            url,
            PytdxMinuteResponse.class,
            Map.of("market", market, "count", count)
        );

        return response.getData();
    }
}
```

**推荐方案**：在 Python 项目中暴露 `/api/pytdx/*` 端点，Java 项目通过 HTTP 调用。这样无需重写 Pytdx 协议。

## 四、采集任务调度

### 4.1 Python 原实现分析

```python
# Python: infrastructure/tasks/collect.py
class DailyKlineCollectTask:
    def __init__(self, fetcher: KlineFetcher):
        self._fetcher = fetcher

    async def run(self, symbols: list[str], days: int):
        tasks = [self._fetch_one(s, days) for s in symbols]
        await asyncio.gather(*tasks)

    async def _fetch_one(self, symbol: str, days: int):
        # 1. 调用 fetcher
        data = await self._fetcher.daily(symbol, ...)
        # 2. 写入数据库
        await self._repo.save_all(data)
        # 3. 更新进度
        await self._op_repo.update_progress(op_id, done=...)
```

关键点：
- 使用 `asyncio.gather` 并发执行
- 任务可取消
- 进度跟踪

### 4.2 Java 实现（Virtual Threads）

```java
@Service
@Slf4j
public class KlineCollectionTask {

    private final TushareCollector tushareCollector;
    private final TechKlineDailyRepository klineRepository;
    private final PoolOperationRepository operationRepository;
    private final ExecutorService executor;

    public KlineCollectionTask() {
        // Virtual Threads 线程池
        this.executor = Executors.newVirtualThreadPerTaskExecutor();
    }

    @Async
    public CompletableFuture<CollectionResult> collectForPool(
            Long operationId, Long poolId, List<String> symbols, int days) {

        // 1. 更新状态为 running
        operationRepository.updateStatus(operationId, "running");
        operationRepository.updateStartedAt(operationId, LocalDateTime.now());

        List<String> errors = new CopyOnWriteArrayList<>();
        AtomicInteger done = new AtomicInteger(0);

        try {
            // 2. 使用 Virtual Threads 并发采集
            List<CompletableFuture<Void>> futures = symbols.stream()
                .map(symbol -> CompletableFuture.runAsync(() -> {
                    try {
                        CollectionResult result = tushareCollector.collect(
                            new CollectionRequest(symbol,
                                LocalDate.now().minusDays(days),
                                LocalDate.now(),
                                Map.of())
                        );

                        if (result.hasErrors()) {
                            errors.addAll(result.getErrors());
                        }

                        int current = done.incrementAndGet();
                        operationRepository.updateProgress(
                            operationId,
                            Map.of("done", current, "total", symbols.size(), "failed", errors.size())
                        );

                    } catch (Exception e) {
                        log.error("Collect failed for {}", symbol, e);
                        errors.add(symbol + ": " + e.getMessage());
                        done.incrementAndGet();
                    }
                }, executor))
                .toList();

            // 3. 等待所有任务完成
            CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

            // 4. 更新最终状态
            operationRepository.updateProgress(operationId, Map.of(
                "done", symbols.size(),
                "total", symbols.size(),
                "failed", errors.size()
            ));
            operationRepository.updateStatus(operationId, "completed");
            operationRepository.updateFinishedAt(operationId, LocalDateTime.now());

            return CompletableFuture.completedFuture(
                new CollectionResult(poolId, symbols.size(), errors.size())
            );

        } catch (Exception e) {
            operationRepository.updateStatus(operationId, "failed");
            operationRepository.updateErrorMessage(operationId, e.getMessage());
            return CompletableFuture.completedFuture(
                new CollectionResult(poolId, 0, symbols.size())
            );
        }
    }
}
```

### 4.3 取消任务

```java
public class KlineCollectionTask {
    private final Map<Long, CompletableFuture<?>> runningTasks = new ConcurrentHashMap<>();

    public void cancel(Long operationId) {
        CompletableFuture<?> task = runningTasks.remove(operationId);
        if (task != null && !task.isDone()) {
            task.cancel(true);
            operationRepository.updateStatus(operationId, "cancelled");
            log.info("Task cancelled: {}", operationId);
        }
    }
}
```

## 五、采集策略

### 5.1 增量采集

```java
@Service
public class IncrementalCollectionStrategy {

    private final TechKlineDailyRepository klineRepository;

    /**
     * 计算需要采集的日期范围
     */
    public LocalDate[] calculateRange(String symbol, int lookbackDays) {
        LocalDate end = LocalDate.now();

        // 查询最新一条记录
        Optional<TechKlineDailyEntity> latest = klineRepository
            .findTopBySymbolOrderByTradeDateDesc(symbol);

        LocalDate start;
        if (latest.isPresent()) {
            // 增量：只采集最新日期之后的数据
            start = latest.get().getTradeDate().plusDays(1);
        } else {
            // 全量：从 lookbackDays 天前开始
            start = end.minusDays(lookbackDays);
        }

        // 防止重复采集
        if (start.isAfter(end)) {
            return null;
        }

        return new LocalDate[]{start, end};
    }
}
```

### 5.2 批量处理

```java
@Service
public class BatchCollectionService {

    private final TushareCollector collector;
    private final TechKlineDailyRepository repository;

    private static final int BATCH_SIZE = 500;

    @Transactional
    public int collectInBatches(String symbol, LocalDate start, LocalDate end) {
        int totalSaved = 0;
        List<TushareKlineDTO> buffer = new ArrayList<>(BATCH_SIZE);

        // 模拟分批获取（实际按 Tushare 限制分页）
        List<TushareKlineDTO> all = collector.fetchDailyKlines(symbol, start, end);

        for (TushareKlineDTO dto : all) {
            buffer.add(dto);

            if (buffer.size() >= BATCH_SIZE) {
                saveAndClear(buffer);
                totalSaved += buffer.size();
            }
        }

        // 处理剩余
        if (!buffer.isEmpty()) {
            saveAndClear(buffer);
            totalSaved += buffer.size();
        }

        return totalSaved;
    }

    private void saveAndClear(List<TushareKlineDTO> buffer) {
        List<TechKlineDailyEntity> entities = buffer.stream()
            .map(this::toEntity)
            .toList();

        repository.saveAll(entities);
        buffer.clear();
    }
}
```

## 六、错误处理与重试

### 6.1 重试机制

```java
@Component
public class RetryableCollector {

    private final TushareCollector delegate;
    private final int maxRetries;
    private final long retryDelayMs;

    public CollectionResult collectWithRetry(CollectionRequest request) {
        Exception lastException = null;

        for (int attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return delegate.collect(request);
            } catch (Exception e) {
                lastException = e;
                log.warn("Attempt {} failed for {}", attempt, request.symbol(), e);

                if (attempt < maxRetries) {
                    try {
                        Thread.sleep(retryDelayMs * attempt);  // 指数退避
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }

        return CollectionResult.failed(request.symbol(), lastException.getMessage());
    }
}
```

### 6.2 限流

```java
@Configuration
public class RateLimiterConfig {

    @Bean
    public RateLimiter tushareRateLimiter(TushareProperties properties) {
        // Tushare Pro 限制：每分钟最多 2000 次调用
        return RateLimiter.create(2000.0 / 60.0);  // 每秒 ~33 次
    }
}

@Service
public class ThrottledTushareCollector {

    private final TushareCollector delegate;
    private final RateLimiter rateLimiter;

    public CollectionResult collect(CollectionRequest request) {
        rateLimiter.acquire();  // 阻塞直到获取许可
        return delegate.collect(request);
    }
}
```

## 七、Tushare API 清单

| API 名称 | Python 方法 | Java 实现 | 用途 |
|---|---|---|---|
| 日K线 | `pro.daily()` | `TushareCollector.fetchDaily()` | K线数据 |
| 每日指标 | `pro.daily_basic()` | `TushareCollector.fetchDailyBasic()` | 换手率、市值 |
| 股票列表 | `pro.stock_basic()` | `TushareCollector.fetchStockBasic()` | 基本信息 |
| 融资融券 | `pro.margin_detail()` | `TushareCollector.fetchMarginDetail()` | 融资融券明细 |
| 龙虎榜 | `pro.top_list()` | `TushareCollector.fetchTopList()` | 营业部龙虎榜 |
| 大宗交易 | `pro.block_trade()` | `TushareCollector.fetchBlockTrade()` | 大宗交易 |
| 资金流向 | `pro.moneyflow()` | `TushareCollector.fetchMoneyflow()` | 主力资金流向 |
| 股权变动 | `pro.holder_num()` | `TushareCollector.fetchHolderNum()` | 股东人数 |
| 财务报表 | `pro.fina_indicator()` | `TushareCollector.fetchFinIndicator()` | 财务指标 |
| 分红送股 | `pro.dividend()` | `TushareCollector.fetchDividend()` | 分红信息 |
| 停牌复牌 | `pro.suspend()` | `TushareCollector.fetchSuspend()` | 停牌信息 |

## 八、采集任务配置

```yaml
# application.yml
collection:
  task:
    # 每批采集的股票数量
    batch-size: 100
    # 批次间延迟（毫秒）
    batch-delay: 1000
    # 最大并发数
    max-concurrency: 50
    # 单只股票最大重试次数
    max-retries: 3
    # 采集默认回溯天数
    default-lookback-days: 365

tushare:
  token: ${TUSHARE_TOKEN:}
  rate-limit: 33  # 每秒请求数
```

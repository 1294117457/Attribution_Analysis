# 03 Java 工程精简方案

> 数据采集下沉到 Python 后，`backend-java` 工程的**架构精简、Port/Adapter 落地、调用方式、文件级改动清单**。

---

## 0. 当前实施范围（Phase 1）

> **本 PR 仅实施 Phase 1**：Java 端**保留入库与指标计算职责**（`TechKlineDailyRepository.saveAll` + `IndicatorCalculator` 仍由 Java 跑），Python 只返回明细 JSON。
> **Phase 2（不在本 PR）**：Python 直连 DB 写入，Java 改为只读验数 + 删 `saveAll` / `IndicatorCalculator`。

| 维度 | Phase 1（本 PR） | Phase 2（后续 PR） |
| --- | --- | --- |
| Python → Java 返回 | 明细 `items: [...]` | 摘要 `{fetched, saved, source}` |
| Java 入库 | ✅ JPA `saveAll` | ❌ 删除 |
| 指标计算 | ✅ Java `IndicatorCalculator` | ❌ 删除（Python 用 `pandas_ta`） |
| Java 端 `IndicatorCalculator` | 保留 | 删除 |
| Java 端 `TechKlineDailyRepository.saveAll` 调用 | 保留 | 删除 |

---

## 1. 精简前后对比

### 1.1 精简前（当前）

```
backend-java/
└── src/main/java/com/attribution/
    ├── domain/
    │   ├── entity/               (entity 全集)
    │   ├── repository/           (repository 全集)
    │   └── service/
    │       └── IndicatorCalculator    ← 仍保留
    │
    ├── application/service/
    │   ├── KlineCollectTask           ← 调用 Java 采集器
    │   ├── DailyBasicCollectTask      ← 调用 Java 采集器
    │   ├── ConceptCollectTask         ← 调用 Java 采集器
    │   ├── FinReportCollectTask       ← 调用 Java 采集器
    │   ├── CollectorRegistry          ← 仍保留（用于内部 collector）
    │   └── ...
    │
    ├── infrastructure/
    │   ├── adapter/collector/         ← ⬇️ 全部下沉到 Python
    │   │   ├── Collector.java
    │   │   ├── pytdx/PytdxMinuteKlineCollector.java
    │   │   ├── tushare/TushareKlineCollector.java
    │   │   ├── tushare/TushareStockBasicCollector.java
    │   │   ├── tushare/TushareApiClient.java
    │   │   ├── tushare/TushareResponse.java
    │   │   ├── tushare/TushareKlineDTO.java
    │   │   └── akshare/AkShareConceptCollector.java
    │   ├── config/
    │   │   ├── TushareProperties.java    ← 改为 PythonClientProperties
    │   │   └── CollectionProperties.java
    │   └── exception/
    │
    └── interface/
        ├── controller/
        │   ├── CollectController.java
        │   └── MinuteKlineController.java
        └── dto/
            └── kline/
                └── KlineCollectVO.java     ← 改为 KlineCollectResultVO（在 DTO 层）
```

### 1.2 精简后（目标）

```
backend-java/
└── src/main/java/com/attribution/
    ├── domain/                       ← 不变
    │   ├── entity/
    │   ├── repository/
    │   ├── port/                     ← 🆕 输出端口
    │   │   ├── DataCollectorPort.java        (接口)
    │   │   └── KlineCollectorPort.java       (接口)
    │   └── service/
    │       └── IndicatorCalculator
    │
    ├── application/service/
    │   ├── KlineCollectTask           ← 改：调 Port
    │   ├── DailyBasicCollectTask      ← 改：调 Port
    │   ├── ConceptCollectTask         ← 改：调 Port
    │   ├── FinReportCollectTask       ← 改：调 Port
    │   ├── CollectTaskService         ← 不变（保留任务调度）
    │   └── ...
    │
    ├── infrastructure/
    │   ├── adapter/collector/         ← 🆕 瘦身后的 adapter
    │   │   ├── PythonDataCollectorAdapter.java   (实现 KlineCollectorPort)
    │   │   └── PythonKlineAdapter.java           (实现 KlineCollectorPort)
    │   ├── client/                   ← 🆕 HTTP 客户端
    │   │   ├── DataCollectorClient.java   (WebClient 封装 + HMAC 签名)
    │   │   └── HmacSigner.java
    │   ├── config/
    │   │   ├── DataCollectorProperties.java     🆕 (URL / HMAC secret / 超时)
    │   │   └── CollectionProperties.java       保留
    │   └── exception/
    │       └── DataCollectorUnavailableException.java   🆕
    │
    └── interface/                    ← 不变（对外接口）
        ├── controller/
        │   ├── CollectController.java         (不变)
        │   └── MinuteKlineController.java     (改为调 Port)
        └── dto/
            └── kline/
                └── KlineCollectResultVO.java   ← 改名 KlineCollectResponseVO
```

---

## 2. 落地 Port/Adapter

### 2.1 domain/port 设计（接口在域内，实现在 infra）

> 严格遵循 `design/architecture/00-overview.md §2 依赖铁律`：domain 不依赖任何外部。Port 定义在 domain。

```java
// domain/port/DataCollectorPort.java
package com.attribution.domain.port;

import com.attribution.domain.port.data.DailyKlineData;
import com.attribution.domain.port.data.MinuteKlineData;
import com.attribution.domain.port.data.StockBasicData;
import java.util.List;

/**
 * 数据采集输出端口（domain 定义，infra 实现）。
 *
 * <p>职责：把"获取外部数据"抽象成域内接口，由 infrastructure 适配器去对接 Python 服务。
 */
public interface DataCollectorPort {

    /**
     * 拉取日 K（指定区间）。
     * @param symbol ts_code（带后缀，如 000001.SZ）
     * @param startDate 起始日期（含）
     * @param endDate 结束日期（含）
     */
    List<DailyKlineData> fetchDailyKline(String symbol, java.time.LocalDate startDate, java.time.LocalDate endDate);

    /**
     * 拉取分 K（最近 N 根，不落库）。
     */
    List<MinuteKlineData> fetchMinuteKline(String symbol, String interval, int count);

    /**
     * 拉取股票基础信息（可全量或按 symbol）。
     */
    List<StockBasicData> fetchStockBasic(List<String> symbols);

    /**
     * 健康检查。
     */
    boolean ping();
}
```

### 2.2 domain 层 DataObject（不引用 DTO）

```java
// domain/port/data/DailyKlineData.java
package com.attribution.domain.port.data;

import java.time.LocalDate;

/**
 * 日 K 数据对象（域内）。仅承载数据，不带 JSON 注解。
 */
public record DailyKlineData(
    String symbol,
    LocalDate tradeDate,
    Double open,
    Double high,
    Double low,
    Double close,
    Long volume,
    Double amount,
    Double changePct,
    Double adjFactor,
    String source        // tushare/akshare/eastmoney
) {}
```

```java
// domain/port/data/MinuteKlineData.java
public record MinuteKlineData(
    String symbol,
    String datetime,        // "YYYY-MM-DD HH:MM"
    String interval,
    Double open,
    Double close,
    Double high,
    Double low,
    Long volume,
    Double amount,
    String source
) {}
```

```java
// domain/port/data/StockBasicData.java
public record StockBasicData(
    String symbol,
    String tsCode,
    String name,
    String industry,
    String market,
    String exchange,
    LocalDate listDate,
    LocalDate delistDate,
    String isHs,
    String actName,
    String actEntType,
    String source
) {}
```

### 2.3 infrastructure 适配器实现

```java
// infrastructure/adapter/collector/PythonKlineAdapter.java
package com.attribution.infrastructure.adapter.collector;

import com.attribution.domain.port.DataCollectorPort;
import com.attribution.domain.port.data.DailyKlineData;
import com.attribution.infrastructure.client.DataCollectorClient;
import com.attribution.infrastructure.config.DataCollectorProperties;
import com.attribution.infrastructure.exception.DataCollectorUnavailableException;
import com.attribution.infrastructure.client.dto.DailyKlineResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class PythonKlineAdapter implements DataCollectorPort {

    private final DataCollectorClient client;
    private final DataCollectorProperties properties;

    @Override
    public List<DailyKlineData> fetchDailyKline(String symbol, LocalDate startDate, LocalDate endDate) {
        try {
            DailyKlineResponse resp = client.post(
                "/v1/collect/kline/daily",
                new DailyKlineRequest(
                    symbol,
                    startDate.format(DateTimeFormatter.BASIC_ISO_DATE),
                    endDate.format(DateTimeFormatter.BASIC_ISO_DATE),
                    "qfq"
                ),
                DailyKlineResponse.class
            );

            return resp.items().stream()
                .map(item -> new DailyKlineData(
                    item.symbol(),
                    item.tradeDate(),
                    item.open(),
                    item.high(),
                    item.low(),
                    item.close(),
                    item.volume(),
                    item.amount(),
                    item.changePct(),
                    item.adjFactor(),
                    item.meta().source().getValue()
                ))
                .toList();

        } catch (Exception e) {
            log.error("Python fetchDailyKline failed: {} {}~{}", symbol, startDate, endDate, e);
            throw new DataCollectorUnavailableException("data-collector fetchDailyKline failed", e);
        }
    }

    // ... fetchMinuteKline / fetchStockBasic / ping 同理
}
```

### 2.4 HTTP 客户端（HMAC 签名内建）

```java
// infrastructure/client/DataCollectorClient.java
package com.attribution.infrastructure.client;

import com.attribution.infrastructure.config.DataCollectorProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataCollectorClient {

    private final WebClient webClient;
    private final DataCollectorProperties properties;
    private final ObjectMapper objectMapper;
    private final HmacSigner signer;

    public <TReq, TResp> TResp post(String path, TReq body, Class<TResp> respType) {
        long ts = Instant.now().getEpochSecond();
        String nonce = UUID.randomUUID().toString().replace("-", "");
        String bodyJson = serialize(body);

        String signature = signer.sign("POST", path, "", bodyJson, String.valueOf(ts), nonce);

        return webClient.post()
            .uri(properties.getBaseUrl() + path)
            .contentType(MediaType.APPLICATION_JSON)
            .header("X-Signature", signature)
            .header("X-Timestamp", String.valueOf(ts))
            .header("X-Nonce", nonce)
            .header("X-Service", "backend-java")
            .bodyValue(body)
            .retrieve()
            .bodyToMono(respType)
            .timeout(Duration.ofMillis(properties.getTimeoutMs()))
            .block();
    }

    public <TResp> TResp get(String path, String query, Class<TResp> respType) {
        long ts = Instant.now().getEpochSecond();
        String nonce = UUID.randomUUID().toString().replace("-", "");
        String fullPath = query.isEmpty() ? path : path + "?" + query;
        String signature = signer.sign("GET", path, query, "", String.valueOf(ts), nonce);

        return webClient.get()
            .uri(properties.getBaseUrl() + fullPath)
            .header("X-Signature", signature)
            .header("X-Timestamp", String.valueOf(ts))
            .header("X-Nonce", nonce)
            .header("X-Service", "backend-java")
            .retrieve()
            .bodyToMono(respType)
            .timeout(Duration.ofMillis(properties.getTimeoutMs()))
            .block();
    }

    private String serialize(Object body) {
        if (body == null) return "";
        try {
            return objectMapper.writeValueAsString(body);
        } catch (Exception e) {
            throw new RuntimeException("serialize body failed", e);
        }
    }
}
```

### 2.5 HMAC 签名器

```java
// infrastructure/client/HmacSigner.java
package com.attribution.infrastructure.client;

import com.attribution.infrastructure.config.DataCollectorProperties;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.apache.commons.codec.digest.HmacUtils;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class HmacSigner {

    private final DataCollectorProperties properties;
    private byte[] secretBytes;

    @PostConstruct
    public void init() {
        this.secretBytes = properties.getHmacSecret().getBytes(java.nio.charset.StandardCharsets.UTF_8);
    }

    public String sign(String method, String path, String query, String body, String timestamp, String nonce) {
        String signString = String.join("\n", method, path, query, body, timestamp, nonce);
        return HmacUtils.hmacSha256Hex(secretBytes, signString);
    }
}
```

### 2.6 配置

```java
// infrastructure/config/DataCollectorProperties.java
package com.attribution.infrastructure.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "data-collector")
@Getter
@Setter
public class DataCollectorProperties {
    private String baseUrl = "http://10.0.0.5:9100";
    private String hmacSecret;
    private int timeoutMs = 30_000;
    private int maxRetries = 2;
    private int rateLimitPerSecond = 50;
}
```

```yaml
# application.yml
data-collector:
  base-url: ${DATA_COLLECTOR_URL:http://10.0.0.5:9100}
  hmac-secret: ${INTERNAL_HMAC_SECRET:dev-secret-please-rotate}
  timeout-ms: 30000
  max-retries: 2
  rate-limit-per-second: 50
```

### 2.7 异常

```java
// infrastructure/exception/DataCollectorUnavailableException.java
package com.attribution.infrastructure.exception;

public class DataCollectorUnavailableException extends RuntimeException {
    public DataCollectorUnavailableException(String msg, Throwable cause) {
        super(msg, cause);
    }
}
```

---

## 3. application 层调整

### 3.1 KlineCollectTask 改造

**改动前**（直接调 Java collector）：
```java
@Slf4j
@Component
public class KlineCollectTask extends BaseCollectTask<String> {

    private final CollectorRegistry collectorRegistry;
    private final StockInfoRepository stockInfoRepository;

    @Override
    protected int processOne(String symbol) {
        return collectorRegistry.getKlineCollector().collectCount(symbol, 500);
    }
}
```

**改动后**（调 Port）：
```java
@Slf4j
@Component
public class KlineCollectTask extends BaseCollectTask<String> {

    private final DataCollectorPort dataCollectorPort;
    private final TechKlineDailyRepository klineRepository;
    private final IndicatorCalculator indicatorCalculator;

    @Override
    protected int processOne(String symbol) {
        // 1. 计算采集区间
        LocalDate end = LocalDate.now();
        LocalDate start = end.minusDays(Math.max(500, 80));

        // 2. 调 Python（端口注入，无需知道是 HTTP 还是别的）
        List<DailyKlineData> data = dataCollectorPort.fetchDailyKline(symbol, start, end);
        if (data.isEmpty()) return 0;

        // 3. domain → entity（域内组装）
        String name = stockInfoRepository.findBySymbol(symbol)
            .map(StockInfoEntity::getName).orElse(null);
        List<TechKlineDailyEntity> entities = data.stream()
            .map(d -> toEntity(symbol, name, d))
            .toList();

        // 4. 入库 + 指标计算（业务逻辑保留在 Java）
        klineRepository.saveAll(entities);
        recalculateIndicators(symbol);
        return entities.size();
    }

    private void recalculateIndicators(String symbol) {
        List<TechKlineDailyEntity> history = klineRepository.findBySymbolOrderByDateAsc(symbol);
        if (history.size() < 2) return;
        List<TechKlineDailyEntity> window = history.subList(Math.max(0, history.size() - 100), history.size());
        window.sort(Comparator.comparing(TechKlineDailyEntity::getDate));
        indicatorCalculator.enrich(window);
        klineRepository.saveAll(window);
    }
}
```

> **核心变化**：删掉 `CollectorRegistry` 依赖；删掉 `StockInfoRepository.findBySymbol` 这种细节（保留即可）；调 `DataCollectorPort` 拿到干净的 `List<DailyKlineData>`。

### 3.2 DailyBasicCollectTask / ConceptCollectTask / FinReportCollectTask 同理

> 所有 `BaseCollectTask` 子类把 `TushareApiClient` 依赖换成 `DataCollectorPort`，删掉 `parseItems` / `toEntity` 中间映射代码（Port 已经返回干净的 domain object）。

---

## 4. interface 层调整

### 4.1 MinuteKlineController 改造

**改动前**（直接调 Java `PytdxMinuteKlineCollector`）：
```java
@RestController
@RequestMapping("/api/v1/kline/minute")
public class MinuteKlineController {
    private final PytdxMinuteKlineCollector collector;

    @GetMapping
    public ApiResponse<List<Map<String, Object>>> get(...) {
        return ApiResponse.ok(collector.fetchMinuteKlines(symbol, interval, count));
    }
}
```

**改动后**（调 Port，Redis 缓存）：
```java
@RestController
@RequestMapping("/api/v1/kline/minute")
@RequiredArgsConstructor
public class MinuteKlineController {

    private final DataCollectorPort dataCollectorPort;
    private final StringRedisTemplate redis;
    private final MinuteKlineMapper mapper;   // domain → DTO 转换器

    @GetMapping
    public ApiResponse<List<MinuteKlineVO>> get(
        @RequestParam String symbol,
        @RequestParam(defaultValue = "5min") String interval,
        @RequestParam(defaultValue = "240") int count) {

        String cacheKey = "mk:" + symbol + ":" + interval;
        String cached = redis.opsForValue().get(cacheKey);
        if (cached != null) {
            return ApiResponse.ok(mapper.fromJson(cached));
        }

        List<MinuteKlineData> data = dataCollectorPort.fetchMinuteKline(symbol, interval, count);
        List<MinuteKlineVO> vo = data.stream().map(mapper::toVO).toList();
        redis.opsForValue().set(cacheKey, mapper.toJson(vo), Duration.ofSeconds(30));
        return ApiResponse.ok(vo);
    }
}
```

### 4.2 CollectController 不变

> CollectController 只接收前端的"触发任务"请求，创建任务记录，提交到 `CollectTaskService`（异步）。具体的采集动作在 `KlineCollectTask.processOne` 里。
>
> 前端交互不变，Java 工程对外 API **完全兼容**。

### 4.3 DTO 命名调整

```java
// interface/dto/kline/KlineCollectResponseVO.java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineCollectResponseVO {
    private String symbol;
    private String source;           // 新增：数据源
    private Integer fetched;
    private Integer saved;
    private LocalDate startDate;
    private LocalDate endDate;
    private String message;
}
```

> 注意：**不放在 domain/repository 返回值上**，只在 controller 装配。详见 `design/architecture/00-overview.md §4.3 DTO 不跨层铁律`（这条**修复**原 `TushareKlineCollector` 返回 `KlineCollectVO` 的违规）。

---

## 5. WebClient Bean 配置

```java
// infrastructure/config/WebClientConfig.java
@Configuration
public class WebClientConfig {

    @Bean("dataCollectorWebClient")
    public WebClient dataCollectorWebClient(DataCollectorProperties props) {
        return WebClient.builder()
            .baseUrl(props.getBaseUrl())
            .defaultHeader(HttpHeaders.USER_AGENT, "backend-java/1.0")
            .codecs(c -> c.defaultCodecs().maxInMemorySize(16 * 1024 * 1024))
            .build();
    }
}
```

---

## 6. 文件级改动清单（落地工单）

### 6.1 删除（迁出）

| 文件 | 说明 |
| ---- | ---- |
| `infrastructure/adapter/collector/Collector.java` | Java 端 collector 接口（迁移后由 Python 实现） |
| `infrastructure/adapter/collector/pytdx/PytdxMinuteKlineCollector.java` | 全部迁到 Python |
| `infrastructure/adapter/collector/tushare/TushareKlineCollector.java` | 全部迁到 Python |
| `infrastructure/adapter/collector/tushare/TushareStockBasicCollector.java` | 全部迁到 Python |
| `infrastructure/adapter/collector/tushare/TushareApiClient.java` | 全部迁到 Python |
| `infrastructure/adapter/collector/tushare/TushareResponse.java` | 全部迁到 Python |
| `infrastructure/adapter/collector/tushare/TushareKlineDTO.java` | 全部迁到 Python |
| `infrastructure/adapter/collector/akshare/AkShareConceptCollector.java` | 全部迁到 Python |
| `infrastructure/config/TushareProperties.java` | tushare token 在 Python 端 |
| `infrastructure/adapter/collector/tushare/*.java` 重复文件（`adapter` 与 `infrastructure` 同包名重复） | 一并清理 |

### 6.2 新增

| 文件 | 说明 |
| ---- | ---- |
| `domain/port/DataCollectorPort.java` | 输出端口接口 |
| `domain/port/data/DailyKlineData.java` | 域内数据对象（record） |
| `domain/port/data/MinuteKlineData.java` | 同上 |
| `domain/port/data/StockBasicData.java` | 同上 |
| `domain/port/data/FinReportData.java` | 同上 |
| `domain/port/data/ConceptData.java` | 同上 |
| `infrastructure/adapter/collector/PythonKlineAdapter.java` | DataCollectorPort 实现 |
| `infrastructure/client/DataCollectorClient.java` | HTTP 客户端（带 HMAC） |
| `infrastructure/client/HmacSigner.java` | HMAC 签名 |
| `infrastructure/config/DataCollectorProperties.java` | 配置 |
| `infrastructure/exception/DataCollectorUnavailableException.java` | 异常 |
| `infrastructure/client/dto/*.java` | Python 端响应的 Java DTO（snake_case 字段） |

### 6.3 修改

| 文件 | 改动 |
| ---- | ---- |
| `application/service/collect/KlineCollectTask.java` | 依赖 `TushareKlineCollector` → `DataCollectorPort` |
| `application/service/collect/DailyBasicCollectTask.java` | 依赖 `TushareApiClient` → `DataCollectorPort` |
| `application/service/collect/ConceptCollectTask.java` | 依赖 `TushareApiClient` + `AkShareConceptCollector` → `DataCollectorPort` |
| `application/service/collect/FinReportCollectTask.java` | 同上 |
| `application/service/CollectorRegistry.java` | 简化为只注册"内部" collector（如有），否则删除 |
| `interface/controller/MinuteKlineController.java` | 依赖 `PytdxMinuteKlineCollector` → `DataCollectorPort` + Redis 缓存 |
| `interface/dto/kline/KlineCollectVO.java` | 重命名为 `KlineCollectResponseVO`，加 `source` 字段 |
| `resources/application.yml` | 新增 `data-collector:` 配置块 |
| `pom.xml` | 删 `hutool`、`fastjson`（如不再需要），加 `commons-codec`（HMAC） |

### 6.4 不变

| 模块 | 理由 |
| ---- | ---- |
| `domain/entity/**` | entity 不动 |
| `domain/repository/**` | repository 不动 |
| `domain/service/IndicatorCalculator` | 指标计算在 Java 侧，保留 |
| `interface/controller/CollectController` | 对前端 API 不变 |
| `interface/controller/PoolController` 等业务 controller | 与采集无关 |
| `infrastructure/persistence/**` | JPA 实现不动 |
| `infrastructure/config/CollectionProperties` | 保留（用于 Java 侧采集参数，如并发、batch） |

---

## 7. 依赖清理

### 7.1 Maven 依赖调整

```xml
<!-- 保留 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webflux</artifactId>  <!-- WebClient -->
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>

<!-- 新增 -->
<dependency>
    <groupId>commons-codec</groupId>
    <artifactId>commons-codec</artifactId>  <!-- HMAC-SHA256 -->
</dependency>

<!-- 可删除（如不再用） -->
<!-- hutool-* 系列（如仅用于 HTTP 调用，可删） -->
<!-- fastjson / Gson（Jackson 已够用） -->
```

### 7.2 Spring Bean 精简

- 删除：`TushareKlineCollector` / `TushareStockBasicCollector` / `AkShareConceptCollector` / `PytdxMinuteKlineCollector` / `TushareApiClient` 的 `@Component`
- 删除：`TushareProperties` 的 `@ConfigurationProperties`
- 删除：`CollectorRegistry` 注册逻辑（保留类作为过渡，后续可删）
- 新增：`DataCollectorProperties` / `DataCollectorClient` / `HmacSigner` / `PythonKlineAdapter`

---

## 8. 测试策略

### 8.1 单元测试

```java
@ExtendWith(MockitoExtension.class)
class PythonKlineAdapterTest {

    @Mock DataCollectorClient client;
    @InjectMocks PythonKlineAdapter adapter;

    @Test
    void fetchDailyKline_returns_data_from_python() {
        // given
        when(client.post(eq("/v1/collect/kline/daily"), any(), eq(DailyKlineResponse.class)))
            .thenReturn(new DailyKlineResponse(...));

        // when
        List<DailyKlineData> result = adapter.fetchDailyKline("000001.SZ",
            LocalDate.of(2025, 1, 1), LocalDate.of(2025, 12, 31));

        // then
        assertEquals(243, result.size());
        assertEquals("tushare", result.get(0).source());
    }

    @Test
    void fetchDailyKline_throws_exception_when_python_unavailable() {
        when(client.post(...)).thenThrow(new RuntimeException("connection refused"));

        assertThrows(DataCollectorUnavailableException.class,
            () -> adapter.fetchDailyKline("000001.SZ", LocalDate.now(), LocalDate.now()));
    }
}
```

### 8.2 集成测试

- 用 WireMock 模拟 Python 服务
- 验证 HMAC 签名正确
- 验证重试/超时/降级

### 8.3 联调测试

- 用 docker-compose 起 Python 服务（Mock 模式可禁用 HMAC）
- Java 端启动 → 触发一次小规模日 K 采集 → 验证落库

---

## 9. 部署顺序

1. 先部署 Python 服务（不接流量，仅内网可达）
2. Java 端 `data-collector` 配置指向 Python URL，**新代码部署**
3. 灰度：
   - 先在测试环境跑通
   - 生产环境用「采集任务开关」逐步切换：手动触发 → 定时任务
4. 验证：观察 1 周无异常后，删除 Java 端废弃的 collector 文件

---

## 10. 总结

| 维度         | 改动                                        |
| ------------ | ------------------------------------------- |
| **domain**   | 新增 `port/DataCollectorPort` 和 `port/data/*` |
| **application** | CollectTask 改为依赖 Port               |
| **infrastructure** | 删 8 个 collector 类，新增 6 个 client/port/adapter |
| **interface** | MinuteKlineController 加 Redis 缓存，其他不变 |
| **DTO**      | 修复原违规（不再从下层返回 DTO）            |
| **依赖**     | 加 commons-codec，删 tushare/akshare 相关（如有） |
| **对外 API** | **完全兼容**，前端无需改动                    |

> 整个迁移对前端**零侵入**——这是设计的关键约束。

---

## 11. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-26 | -      | 初稿    |

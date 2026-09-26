# FastAPI → Spring MVC API 迁移对照

## 一、API 总览

### 1.1 路由清单

| 模块 | FastAPI 路径 | Spring MVC 路径 | 方法 |
|---|---|---|---|
| 健康检查 | `GET /health` | `GET /api/health` | - |
| K线查询 | `GET /api/klines/{symbol}` | `GET /api/klines/{symbol}` | KlineController |
| K线统计 | `GET /api/klines/{symbol}/stats` | `GET /api/klines/{symbol}/stats` | KlineController |
| 单条K线 | `GET /api/klines/{symbol}/{trade_date}` | `GET /api/klines/{symbol}/{tradeDate}` | KlineController |
| K线采集 | `POST /api/klines/collect` | `POST /api/klines/collect` | KlineController |
| 批量采集 | `POST /api/klines/collect/batch` | `POST /api/klines/collect/batch` | KlineController |
| 删除K线 | `DELETE /api/klines/{symbol}` | `DELETE /api/klines/{symbol}` | KlineController |
| 创建池 | `POST /api/pools` | `POST /api/pools` | PoolController |
| 池列表 | `GET /api/pools` | `GET /api/pools` | PoolController |
| 池详情 | `GET /api/pools/{pool_id}` | `GET /api/pools/{poolId}` | PoolController |
| 更新池 | `PATCH /api/pools/{pool_id}` | `PATCH /api/pools/{poolId}` | PoolController |
| 删除池 | `DELETE /api/pools/{pool_id}` | `DELETE /api/pools/{poolId}` | PoolController |
| 添加成员 | `POST /api/pools/{pool_id}/members` | `POST /api/pools/{poolId}/members` | PoolController |
| 删除成员 | `DELETE /api/pools/{pool_id}/members` | `DELETE /api/pools/{poolId}/members` | PoolController |
| 成员列表 | `GET /api/pools/{pool_id}/members` | `GET /api/pools/{poolId}/members` | PoolController |
| 股票在哪池 | `GET /api/pools/by-symbol/{symbol}` | `GET /api/pools/by-symbol/{symbol}` | PoolController |
| 发起操作 | `POST /api/pools/{pool_id}/operations` | `POST /api/pools/{poolId}/operations` | PoolController |
| 操作历史 | `GET /api/pools/{pool_id}/operations` | `GET /api/pools/{poolId}/operations` | PoolController |
| 操作详情 | `GET /api/operations/{op_id}` | `GET /api/operations/{opId}` | OperationController |
| 操作进度 | `GET /api/operations/{op_id}/progress` | `GET /api/operations/{opId}/progress` | OperationController |
| 取消操作 | `POST /api/operations/{op_id}/cancel` | `POST /api/operations/{opId}/cancel` | OperationController |
| 股票分析 | `GET /api/stocks/{symbol}/analysis` | `GET /api/stocks/{symbol}/analysis` | StockController |
| 股票详情 | `GET /api/stocks/{symbol}` | `GET /api/stocks/{symbol}` | StockController |
| 概念板块 | `GET /api/concepts` | `GET /api/concepts` | ConceptController |
| 概念详情 | `GET /api/concepts/{code}` | `GET /api/concepts/{code}` | ConceptController |
| 概念成员 | `GET /api/concepts/{code}/members` | `GET /api/concepts/{code}/members` | ConceptController |

## 二、核心 API 迁移对照

### 2.1 K线查询

**Python (FastAPI)**:
```python
@router.get("/klines/{symbol}", summary="查询K线")
async def get_klines(
    symbol: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(365, ge=1, le=3650),
    order_desc: bool = Query(True),
    service: KlineAppService = Depends(get_kline_service),
):
    request = KlineQueryRequest(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        order_desc=order_desc,
    )
    response = await service.get_klines(request)
    return R.ok(response.model_dump())
```

**Java (Spring MVC)**:
```java
@RestController
@RequestMapping("/api/klines")
@RequiredArgsConstructor
@Slf4j
public class KlineController {

    private final KlineService klineService;

    @GetMapping("/{symbol}")
    public ResponseEntity<ApiResponse<List<KlineVO>>> getKlines(
            @PathVariable String symbol,
            @RequestParam(required = false) @DateTimeFormat(iso = ISO.DATE) LocalDate startDate,
            @RequestParam(required = false) @DateTimeFormat(iso = ISO.DATE) LocalDate endDate,
            @RequestParam(defaultValue = "365") @Min(1) @Max(3650) Integer limit,
            @RequestParam(defaultValue = "true") Boolean orderDesc) {

        KlineQueryRequest request = KlineQueryRequest.builder()
            .symbol(symbol)
            .startDate(startDate)
            .endDate(endDate)
            .limit(limit)
            .orderDesc(orderDesc)
            .build();

        List<KlineVO> klines = klineService.getKlines(request);
        return ResponseEntity.ok(ApiResponse.ok(klines));
    }
}
```

### 2.2 K线采集

**Python (FastAPI)**:
```python
@router.post("/klines/collect", summary="采集K线", status_code=status.HTTP_201_CREATED)
async def collect_kline(
    request: KlineCollectRequest,
    service: KlineAppService = Depends(get_kline_service),
    fetcher: KlineFetcher = Depends(get_kline_fetcher),
):
    response = await service.collect(request, fetcher)
    return R.created(response.model_dump())
```

**Java (Spring MVC)**:
```java
@RestController
@RequestMapping("/api/klines")
@RequiredArgsConstructor
@Slf4j
public class KlineController {

    private final KlineService klineService;
    private final TushareCollector tushareCollector;

    @PostMapping("/collect")
    @ResponseStatus(HttpStatus.CREATED)
    public ResponseEntity<ApiResponse<KlineCollectVO>> collectKline(
            @Valid @RequestBody KlineCollectRequest request) {

        KlineCollectVO result = klineService.collect(request, tushareCollector);
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(ApiResponse.created(result));
    }

    @PostMapping("/collect/batch")
    @ResponseStatus(HttpStatus.CREATED)
    public ResponseEntity<ApiResponse<Map<String, KlineCollectVO>>> collectBatch(
            @RequestParam List<String> symbols,
            @RequestParam(defaultValue = "30") @Min(1) @Max(3650) Integer days) {

        Map<String, KlineCollectVO> results = klineService.collectBatch(symbols, days, tushareCollector);
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(ApiResponse.created(results));
    }
}
```

### 2.3 操作池 CRUD

**Python (FastAPI)**:
```python
@router.post("/pools", summary="创建池", status_code=status.HTTP_201_CREATED)
async def create_pool(
    request: PoolCreateRequest,
    service: StockPoolAppService = Depends(get_pool_service),
):
    pool = await service.create_pool(request)
    return created(pool.model_dump(), "创建成功")

@router.get("/pools", summary="池列表")
async def list_pools(
    include_archived: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.list_pools(include_archived=include_archived, limit=limit, offset=offset)
    return ok(result.model_dump())
```

**Java (Spring MVC)**:
```java
@RestController
@RequestMapping("/api/pools")
@RequiredArgsConstructor
@Slf4j
public class PoolController {

    private final StockPoolService stockPoolService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ResponseEntity<ApiResponse<PoolVO>> createPool(
            @Valid @RequestBody PoolCreateRequest request) {

        PoolVO pool = stockPoolService.createPool(request);
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(ApiResponse.created(pool, "创建成功"));
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PoolListVO>> listPools(
            @RequestParam(defaultValue = "false") Boolean includeArchived,
            @RequestParam(defaultValue = "100") @Min(1) @Max(500) Integer limit,
            @RequestParam(defaultValue = "0") @Min(0) Integer offset) {

        PoolListVO result = stockPoolService.listPools(includeArchived, limit, offset);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @GetMapping("/{poolId}")
    public ResponseEntity<ApiResponse<PoolDetailVO>> getPool(
            @PathVariable Long poolId) {

        PoolDetailVO pool = stockPoolService.getPool(poolId);
        return ResponseEntity.ok(ApiResponse.ok(pool));
    }

    @PatchMapping("/{poolId}")
    public ResponseEntity<ApiResponse<PoolVO>> updatePool(
            @PathVariable Long poolId,
            @Valid @RequestBody PoolUpdateRequest request) {

        PoolVO pool = stockPoolService.updatePool(poolId, request);
        return ResponseEntity.ok(ApiResponse.ok(pool, "更新成功"));
    }

    @DeleteMapping("/{poolId}")
    public ResponseEntity<ApiResponse<Void>> deletePool(
            @PathVariable Long poolId) {

        stockPoolService.deletePool(poolId);
        return ResponseEntity.ok(ApiResponse.ok(null, "删除成功"));
    }
}
```

### 2.4 池成员管理

**Python (FastAPI)**:
```python
@router.post("/pools/{pool_id}/members", summary="批量添加成员")
async def add_members(
    pool_id: int = Path(...),
    request: PoolAddMembersRequest = Body(...),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.add_members(pool_id, request)
    return ok(result.model_dump(), "添加完成")

@router.get("/pools/{pool_id}/members", summary="成员列表")
async def list_members(
    pool_id: int = Path(...),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: StockPoolAppService = Depends(get_pool_service),
):
    result = await service.list_members(pool_id, limit, offset)
    return ok(result.model_dump())
```

**Java (Spring MVC)**:
```java
@RestController
@RequestMapping("/api/pools")
@RequiredArgsConstructor
@Slf4j
public class PoolController {

    @PostMapping("/{poolId}/members")
    public ResponseEntity<ApiResponse<PoolAddMembersVO>> addMembers(
            @PathVariable Long poolId,
            @Valid @RequestBody PoolAddMembersRequest request) {

        PoolAddMembersVO result = stockPoolService.addMembers(poolId, request);
        return ResponseEntity.ok(ApiResponse.ok(result, "添加完成"));
    }

    @GetMapping("/{poolId}/members")
    public ResponseEntity<ApiResponse<PoolMemberListVO>> listMembers(
            @PathVariable Long poolId,
            @RequestParam(defaultValue = "100") @Min(1) @Max(1000) Integer limit,
            @RequestParam(defaultValue = "0") @Min(0) Integer offset) {

        PoolMemberListVO result = stockPoolService.listMembers(poolId, limit, offset);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @DeleteMapping("/{poolId}/members")
    public ResponseEntity<ApiResponse<Map<String, Object>>> removeMembers(
            @PathVariable Long poolId,
            @Valid @RequestBody PoolRemoveMembersRequest request) {

        int count = stockPoolService.removeMembers(poolId, request);
        return ResponseEntity.ok(ApiResponse.ok(
            Map.of("removed_count", count),
            "成功移除 " + count + " 个成员"
        ));
    }
}
```

### 2.5 池操作（采集任务）

**Python (FastAPI)**:
```python
@router.post("/pools/{pool_id}/operations", summary="发起池操作", status_code=status.HTTP_201_CREATED)
async def create_pool_operation(
    pool_id: int = Path(...),
    request: PoolKlineCollectRequest = Body(...),
    service: PoolOperationAppService = Depends(get_pool_op_service),
):
    result = await service.create_kline_collect_operation(request)
    return created(result.model_dump(), result.message)
```

**Java (Spring MVC)**:
```java
@RestController
@RequestMapping("/api/pools")
@RequiredArgsConstructor
@Slf4j
public class PoolController {

    private final PoolOperationService poolOperationService;

    @PostMapping("/{poolId}/operations")
    @ResponseStatus(HttpStatus.CREATED)
    public ResponseEntity<ApiResponse<PoolOperationVO>> createOperation(
            @PathVariable Long poolId,
            @Valid @RequestBody PoolKlineCollectRequest request) {

        PoolOperationVO result = poolOperationService.createKlineCollectOperation(poolId, request);
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(ApiResponse.created(result, result.getMessage()));
    }

    @GetMapping("/{poolId}/operations")
    public ResponseEntity<ApiResponse<PoolOperationListVO>> listOperations(
            @PathVariable Long poolId,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) Integer limit,
            @RequestParam(defaultValue = "0") @Min(0) Integer offset) {

        PoolOperationListVO result = poolOperationService.listOperations(poolId, limit, offset);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }
}
```

### 2.6 操作详情与进度

**Python (FastAPI)**:
```python
@router.get("/operations/{op_id}", summary="操作详情")
async def get_operation(op_id: int = Path(...), service: PoolOperationAppService = Depends(get_pool_op_service)):
    op = await service.get_operation(op_id)
    return ok(op.model_dump())

@router.get("/operations/{op_id}/progress", summary="操作进度")
async def get_operation_progress(op_id: int = Path(...), service: PoolOperationAppService = Depends(get_pool_op_service)):
    progress = await service.get_operation_progress(op_id)
    return ok(progress.model_dump())

@router.post("/operations/{op_id}/cancel", summary="取消操作")
async def cancel_operation(op_id: int = Path(...), service: PoolOperationAppService = Depends(get_pool_op_service)):
    op = await service.cancel_operation(op_id)
    return ok(op.model_dump(), "操作已取消")
```

**Java (Spring MVC)**:
```java
@RestController
@RequestMapping("/api/operations")
@RequiredArgsConstructor
@Slf4j
public class OperationController {

    private final PoolOperationService poolOperationService;

    @GetMapping("/{opId}")
    public ResponseEntity<ApiResponse<PoolOperationVO>> getOperation(
            @PathVariable Long opId) {

        PoolOperationVO op = poolOperationService.getOperation(opId);
        return ResponseEntity.ok(ApiResponse.ok(op));
    }

    @GetMapping("/{opId}/progress")
    public ResponseEntity<ApiResponse<PoolOperationProgressVO>> getProgress(
            @PathVariable Long opId) {

        PoolOperationProgressVO progress = poolOperationService.getOperationProgress(opId);
        return ResponseEntity.ok(ApiResponse.ok(progress));
    }

    @PostMapping("/{opId}/cancel")
    public ResponseEntity<ApiResponse<PoolOperationVO>> cancelOperation(
            @PathVariable Long opId) {

        PoolOperationVO op = poolOperationService.cancelOperation(opId);
        return ResponseEntity.ok(ApiResponse.ok(op, "操作已取消"));
    }
}
```

### 2.7 股票分析

**Python (FastAPI)**:
```python
# src/route/api/v1/stock_analysis.py
@router.get("/stocks/{symbol}/analysis", summary="股票归因分析")
async def get_stock_analysis(
    symbol: str,
    days: int = Query(365, ge=1, le=3650),
    service: StockAnalysisService = Depends(get_stock_analysis_service),
):
    result = await service.build(symbol, days)
    return R.ok(result.model_dump())
```

**Java (Spring MVC)**:
```java
@RestController
@RequestMapping("/api/stocks")
@RequiredArgsConstructor
@Slf4j
public class StockController {

    private final StockAnalysisService stockAnalysisService;

    @GetMapping("/{symbol}/analysis")
    public ResponseEntity<ApiResponse<StockAnalysisVO>> getStockAnalysis(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "365") @Min(1) @Max(3650) Integer days) {

        StockAnalysisVO result = stockAnalysisService.build(symbol, days);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }
}
```

## 三、请求/响应 DTO 对照

### 3.1 统一响应格式

**Python**:
```python
# route/schemas/response.py
class ApiResponse:
    code: int
    message: str
    data: Any

def ok(data, message="success"):
    return {"code": 200, "message": message, "data": data}

def created(data, message="created"):
    return {"code": 201, "message": message, "data": data}
```

**Java**:
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiResponse<T> {
    private int code;
    private String message;
    private T data;

    public static <T> ApiResponse<T> ok(T data) {
        return ApiResponse.<T>builder()
            .code(200)
            .message("success")
            .data(data)
            .build();
    }

    public static <T> ApiResponse<T> ok(T data, String message) {
        return ApiResponse.<T>builder()
            .code(200)
            .message(message)
            .data(data)
            .build();
    }

    public static <T> ApiResponse<T> created(T data) {
        return ApiResponse.<T>builder()
            .code(201)
            .message("created")
            .data(data)
            .build();
    }

    public static <T> ApiResponse<T> created(T data, String message) {
        return ApiResponse.<T>builder()
            .code(201)
            .message(message)
            .data(data)
            .build();
    }
}
```

### 3.2 K线相关 DTO

**Java**:
```java
// Request
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineQueryRequest {
    private String symbol;
    private LocalDate startDate;
    private LocalDate endDate;
    private Integer limit;
    private Boolean orderDesc;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineCollectRequest {
    private String symbol;
    @Min(1) @Max(3650)
    private Integer days;
}

// Response
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineVO {
    private LocalDate date;
    private String symbol;
    private String name;
    private Double open;
    private Double high;
    private Double low;
    private Double close;
    private Long volume;
    private Double amount;
    private Double changePct;
    // 技术指标...
    private Double ma5;
    private Double ma10;
    // ...
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineCollectVO {
    private String symbol;
    private Integer fetched;
    private Integer saved;
    private LocalDate startDate;
    private LocalDate endDate;
}
```

### 3.3 操作池相关 DTO

**Java**:
```java
// Request
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolCreateRequest {
    @NotBlank
    private String name;
    private String poolType;
    private String description;
    private String color;
    private String icon;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolUpdateRequest {
    private String name;
    private String description;
    private String color;
    private String icon;
    private Integer sortOrder;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolAddMembersRequest {
    @NotEmpty
    private List<String> symbols;
    private Boolean validateExists;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolRemoveMembersRequest {
    @NotEmpty
    private List<String> symbols;
}

// Response
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolVO {
    private Long id;
    private String name;
    private String poolType;
    private String description;
    private String color;
    private String icon;
    private Integer sortOrder;
    private Boolean isDefault;
    private Boolean isArchived;
    private Integer memberCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolDetailVO extends PoolVO {
    private List<PoolMemberVO> members;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolMemberVO {
    private String symbol;
    private String memo;
    private Integer sortOrder;
    private String name;
    private String industry;
    private String market;
    private Boolean isValid;
    private LocalDateTime addedAt;
}

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolListVO {
    private Integer total;
    private List<PoolVO> items;
}
```

## 四、异常映射

| Python 异常 | HTTP 状态码 | Java 异常 | HTTP 状态码 |
|---|---|---|---|
| `KlineNotFoundError` | 404 | `KlineNotFoundException` | 404 |
| `StockNotFoundError` | 404 | `StockNotFoundException` | 404 |
| `PoolNotFoundError` | 404 | `PoolNotFoundException` | 404 |
| `PoolOperationNotFoundError` | 404 | `PoolOperationNotFoundException` | 404 |
| `KlineDataError` | 400 | `KlineDataException` | 400 |
| `CollectionError` | 502 | `CollectionException` | 502 |
| `RequestValidationError` | 422 | `MethodArgumentNotValidException` | 422 |
| `PoolOperationConflictError` | 409 | `PoolOperationConflictException` | 409 |
| `DuplicatePoolMemberError` | 409 | `DuplicateMemberException` | 409 |

## 五、参数校验

**Python (Pydantic)**:
```python
from pydantic import BaseModel, Field

class KlineCollectRequest(BaseModel):
    symbol: str = Field(..., description="股票代码")
    days: int = Field(default=30, ge=1, le=3650)
```

**Java (Jakarta Validation)**:
```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineCollectRequest {
    @NotBlank(message = "股票代码不能为空")
    private String symbol;

    @Min(value = 1, message = "天数最少为1")
    @Max(value = 3650, message = "天数最多为3650")
    @Builder.Default
    private Integer days = 30;
}
```

## 六、OpenAPI 文档

**Python (FastAPI 自动生成)**:
```python
app = FastAPI(
    title="智能金融数据归因分析平台",
    description="DDD 架构 - 数据采集 + K线查询",
    version="2.0.0",
)
```

**Java (SpringDoc OpenAPI)**:
```java
@SpringBootApplication
@OpenAPIDefinition(
    info = @Info(
        title = "智能金融数据归因分析平台",
        description = "Java 21 + Spring Boot 3.3 重构版",
        version = "3.0.0"
    )
)
public class AttributionApplication {
    public static void main(String[] args) {
        SpringApplication.run(AttributionApplication.class, args);
    }
}
```

访问 `http://localhost:8000/swagger-ui.html` 查看 API 文档。

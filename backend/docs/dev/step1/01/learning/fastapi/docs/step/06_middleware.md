# Step 06: 中间件和异常处理

## 学习目标
掌握 FastAPI 中间件、请求拦截、全局异常处理

## 概念速览

```python
# 中间件
@app.middleware("http")
async def add_process_time_header(request, call_next):
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 异常处理
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(status_code=400, content={"error": str(exc)})
```

## 任务

### 任务 1: 基本中间件

创建 `demo_06_middleware.py`：

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time
import logging

app = FastAPI()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ 中间件 ============

# 1. 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求的日志"""
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"请求开始: {request.method} {request.url.path}")
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.time() - start_time
    
    # 记录响应信息
    logger.info(f"请求完成: {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    # 添加自定义响应头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# 2. 请求拦截中间件
@app.middleware("http")
async def check_api_key(request: Request, call_next):
    """API 密钥检查"""
    # 跳过健康检查和文档
    if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    # 检查 API 密钥（简化示例）
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"error": "缺少 API 密钥"}
        )
    
    # 模拟验证
    if api_key != "test-api-key":
        return JSONResponse(
            status_code=403,
            content={"error": "无效的 API 密钥"}
        )
    
    return await call_next(request)

# 3. CORS 中间件
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 异常处理器 ============

# 4. 自定义异常
class StockNotFoundException(Exception):
    """股票不存在异常"""
    def __init__(self, code: str):
        self.code = code
        self.message = f"股票 {code} 不存在"

class ValidationException(Exception):
    """验证异常"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message

# 5. 注册异常处理器
@app.exception_handler(StockNotFoundException)
async def stock_not_found_handler(request: Request, exc: StockNotFoundException):
    """处理股票不存在异常"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "stock_not_found",
            "message": exc.message,
            "code": exc.code
        }
    )

@app.exception_handler(ValidationException)
async def validation_error_handler(request: Request, exc: ValidationException):
    """处理验证异常"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "field": exc.field,
            "message": exc.message
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器（兜底）"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "服务器内部错误"
        }
    )
```

### 任务 2: 使用异常

```python
# ============ 示例路由 ============

@app.get("/")
def read_root():
    return {"message": "Hello"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# 使用自定义异常
@app.get("/stocks/{code}")
def get_stock(code: str):
    """获取股票，演示异常抛出"""
    valid_codes = ["600519", "000858", "600036"]
    
    if code not in valid_codes:
        raise StockNotFoundException(code)
    
    return {
        "code": code,
        "name": "贵州茅台" if code == "600519" else "其他",
        "price": 1500.0
    }

@app.post("/validate")
def validate_stock(code: str, price: float):
    """验证股票数据，演示验证异常"""
    if not code or len(code) != 6:
        raise ValidationException("code", "股票代码必须是6位")
    
    if price < 0:
        raise ValidationException("price", "价格不能为负")
    
    if price > 100000:
        raise ValidationException("price", "价格超出合理范围")
    
    return {"valid": True, "code": code, "price": price}
```

### 任务 3: 统一的响应格式

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class ResponseModel(Generic[T]):
    """统一响应模型"""
    def __init__(self, success: bool, data: T = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error

# 使用装饰器统一响应格式（简化版）
def unified_response(func):
    """统一响应格式的装饰器"""
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    return wrapper

@app.get("/api/stocks/{code}")
@unified_response
async def get_stock_api(code: str):
    """统一格式的 API"""
    if code == "invalid":
        raise ValueError("无效的股票代码")
    return {"code": code, "name": "贵州茅台"}
```

## 测试

```bash
# 测试中间件（记录日志）
curl http://localhost:8000/stocks/600519

# 测试 API 密钥（无密钥）
curl http://localhost:8000/api/stocks/600519

# 测试 API 密钥（有密钥）
curl -H "X-API-Key: test-api-key" http://localhost:8000/api/stocks/600519

# 测试异常
curl http://localhost:8000/stocks/999999
curl -X POST "http://localhost:8000/validate?code=123&price=-100"
```

## 下一步
阅读 `../docs/analysis/06_middleware.md` 深入理解

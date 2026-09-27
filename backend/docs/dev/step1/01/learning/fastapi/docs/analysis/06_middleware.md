# 中间件和异常处理详解

## 一、中间件概念

### 什么是中间件？

```
请求流程
    ↓
[中间件1] → 记录日志
    ↓
[中间件2] → 检查认证
    ↓
[中间件3] → CORS 处理
    ↓
[路由处理函数]
    ↓
[中间件3] → 处理响应
    ↓
[中间件2] → 处理响应
    ↓
[中间件1] → 处理响应
    ↓
    返回响应
```

### 中间件 vs 依赖注入

| 特性 | 中间件 | 依赖注入 (Depends) |
|------|--------|-------------------|
| 执行时机 | 每个请求都执行 | 按需执行 |
| 范围 | 全局 | 路由级别 |
| 用途 | 横切关注点 | 共享逻辑 |
| 例子 | 日志、CORS、认证 | 数据库会话、当前用户 |

## 二、中间件实现

### 基本结构

```python
@app.middleware("http")
async def middleware_name(request: Request, call_next):
    # 请求处理前的代码
    ...
    
    response = await call_next(request)
    
    # 响应处理后的代码
    ...
    
    return response
```

### 执行顺序

```python
# 中间件按添加顺序执行
app.add_middleware(A)  # 1. 最先添加，最后处理请求
app.add_middleware(B)  # 2. 第二添加
app.add_middleware(C)  # 3. 最后添加，最先处理请求

# 执行顺序：请求进入 C → B → A → 路由 → A → B → C 响应
```

## 三、常用中间件

### 1. 日志中间件

```python
import time
import logging

@app.middleware("http")
async def log_middleware(request: Request, call_next):
    start_time = time.time()
    
    # 记录请求
    logger.info(f"请求: {request.method} {request.url.path}")
    
    # 处理
    response = await call_next(request)
    
    # 记录响应
    duration = time.time() - start_time
    logger.info(f"响应: {response.status_code} - {duration:.3f}s")
    
    response.headers["X-Process-Time"] = str(duration)
    return response
```

### 2. 认证中间件

```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # 跳过公开路由
    if request.url.path in ["/", "/health", "/docs"]:
        return await call_next(request)
    
    # 检查认证
    token = request.headers.get("Authorization")
    if not token:
        return JSONResponse(
            status_code=401,
            content={"error": "未认证"}
        )
    
    # 验证 token...
    if not verify_token(token):
        return JSONResponse(
            status_code=403,
            content={"error": "无效的 token"}
        )
    
    return await call_next(request)
```

### 3. CORS 中间件

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许的域名
    allow_credentials=True,  # 允许携带凭证
    allow_methods=["*"],  # 允许的方法
    allow_headers=["*"],  # 允许的头
)
```

### 4. GZip 压缩中间件

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
# 响应大于 1000 字节时自动压缩
```

## 四、异常处理

### HTTPException

```python
from fastapi import HTTPException

@app.get("/stocks/{code}")
def get_stock(code: str):
    if code not in valid_codes:
        raise HTTPException(
            status_code=404,
            detail=f"股票 {code} 不存在"
        )
    return stock
```

### 自定义异常类

```python
class StockNotFoundError(Exception):
    def __init__(self, code: str):
        self.code = code
        self.message = f"股票 {code} 不存在"

@app.exception_handler(StockNotFoundError)
async def stock_not_found_handler(request: Request, exc: StockNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "stock_not_found",
            "code": exc.code,
            "message": exc.message
        }
    )

# 使用
@app.get("/stocks/{code}")
def get_stock(code: str):
    if code not in valid_codes:
        raise StockNotFoundError(code)
    return stock
```

### 全局异常处理器

```python
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "details": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "内部服务器错误"}
    )
```

## 五、响应模型与验证

### Pydantic 验证异常

```python
from pydantic import ValidationError

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "errors": errors
        }
    )
```

## 六、统一响应格式

### 方式1：装饰器

```python
from functools import wraps
from typing import TypeVar, Callable
from pydantic import BaseModel

T = TypeVar("T")

class Response(BaseModel):
    success: bool
    data: T | None = None
    error: str | None = None

def api_handler(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return wrapper

@app.get("/stocks/{code}")
@api_handler
async def get_stock(code: str):
    # 如果这里抛异常，会被装饰器捕获
    return {"code": code, "name": "贵州茅台"}
```

### 方式2：响应模型

```python
class SuccessResponse(BaseModel):
    success: bool = True
    data: Any

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: int = 400

@app.get("/stocks/{code}", response_model=SuccessResponse)
def get_stock(code: str):
    # 正常返回
    return {"data": stock}

@app.exception_handler(StockNotFoundError)
async def handler(request, exc):
    return {"success": False, "error": exc.message}
```

## 七、最佳实践

### 1. 异常分类

```python
# 业务异常
class BusinessException(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code

# 验证异常
class ValidationException(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message

# 认证异常
class AuthException(Exception):
    pass
```

### 2. 异常处理原则

```python
# 原则1：捕获具体异常
try:
    do_something()
except ValueError as e:
    handle_value_error(e)
except Exception:
    handle_other()

# 原则2：记录异常日志
@app.exception_handler(Exception)
async def handler(request, exc):
    logger.error(f"异常: {exc}", exc_info=True)
    return error_response()

# 原则3：不要吞掉异常
@app.exception_handler(Exception)
async def handler(request, exc):
    # ❌ 不要静默忽略
    pass
    
    # ✅ 返回合适的响应
    return JSONResponse(status_code=500, content={"error": "服务器错误"})
```

## 八、调试技巧

### 开发模式异常

```python
# 启用详细错误页面
app = FastAPI(debug=True)

# 或者设置环境变量
# export DEBUG=True
```

### 请求信息

```python
@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Path params: {request.path_params}")
    print(f"Query params: {dict(request.query_params)}")
    return await call_next(request)
```

## 常见问题

### 1. 中间件中的异常

```python
@app.middleware("http")
async def safe_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"中间件异常: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "中间件处理失败"}
        )
```

### 2. 响应后继续处理

```python
@app.middleware("http")
async def response_middleware(request: Request, call_next):
    response = await call_next(request)
    
    # 在响应发送后继续处理（如日志）
    # ⚠️ 注意：此时响应已发送给客户端
    
    return response
```

## 练习题

1. 实现请求日志中间件，记录请求方法、路径、响应状态码、处理时间
2. 实现 API 密钥认证中间件，公开路由跳过认证
3. 实现统一的错误响应格式
4. 实现请求限流中间件（限制 IP 每分钟请求次数）
5. 实现缓存中间件，缓存 GET 请求的响应

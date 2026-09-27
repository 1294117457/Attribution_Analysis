# 请求参数详解

## 一、参数类型总览

```
请求参数
├── 路径参数 (Path Parameters)  /items/{id}
├── 查询参数 (Query Parameters) /items?id=123
├── 请求头 (Headers)            Header 头
├── Cookie                      Cookie 头
└── 请求体 (Body)               JSON 数据
```

## 二、路径参数

### 基本语法

```python
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

### 类型转换

FastAPI 自动进行类型转换：

```python
@app.get("/items/{item_id}")
def read_item(item_id: int):  # 自动转为 int
    return {"item_id": item_id, "type": type(item_id).__name__}

# /items/123    → item_id = 123 (int)
# /items/abc    → 422 错误
# /items/12.34  → 422 错误
```

### 多个路径参数

```python
@app.get("/users/{user_id}/posts/{post_id}")
def read_post(user_id: int, post_id: int):
    return {"user_id": user_id, "post_id": post_id}
```

### 路径参数 vs 查询参数

```
路径参数：资源标识
  /users/123      → 获取 ID 为 123 的用户
  /stocks/600519  → 获取代码为 600519 的股票

查询参数：过滤/分页
  /users?role=admin&page=1   → 过滤和分页
  /stocks?market=sh&limit=10 → 筛选条件
```

## 三、查询参数

### 基本语法

```python
@app.get("/items")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

# /items?skip=0&limit=10
# /items?skip=20
```

### 参数顺序

必需参数放前面，可选参数放后面：

```python
# ✅ 正确：必需参数在前
@app.get("/users/{user_id}/items")
def get_user_items(user_id: int, limit: int = 10):
    pass

# ✅ 也正确：全部可选
@app.get("/items")
def get_items(limit: int = 10, offset: int = 0):
    pass
```

### 可选参数

```python
from typing import Optional

@app.get("/search")
def search(q: Optional[str] = None):
    if q:
        return {"query": q, "results": [...]}
    return {"query": None, "results": [...]}

# /search           → q = None
# /search?q=茅台    → q = "茅台"
```

### Python 3.10+ 语法

```python
# Python 3.10+ 可以用 str | None
@app.get("/search")
def search(q: str | None = None):
    pass
```

## 四、枚举参数

### 定义枚举

```python
from enum import Enum

class ModelName(str, Enum):
    ALBERT = "albert"
    BERT = "bert"
    GPT = "gpt"
```

### 使用枚举

```python
@app.get("/models/{model_name}")
def get_model(model_name: ModelName):
    if model_name == ModelName.GPT:
        return {"model": model_name, "version": "4.0"}
    return {"model": model_name}
```

### 与你的项目相关

```python
class DetectorType(str, Enum):
    PRICE = "price"
    VOLUME = "volume"
    NEWS = "news"

class Market(str, Enum):
    SH = "sh"  # 上交所
    SZ = "sz"  # 深交所
    BJ = "bj"  # 北交所
```

## 五、请求头参数

### Header 参数

```python
from fastapi import Header

@app.get("/headers")
def get_headers(
    user_agent: str = Header(None),  # 自动转换为 snake_case
    content_type: str = Header(None)
):
    return {"user_agent": user_agent}
```

### 自动转换

FastAPI 自动转换 HTTP 头为 Python 变量：

```python
# Header: X-Custom-Header
# 参数名: x_custom_header

@app.get("/custom")
def get_custom(x_custom_header: str = Header(None)):
    return {"header": x_custom_header}
```

### 禁用转换

```python
@app.get("/headers")
def get_headers(
    user_agent: str = Header(None, convert_underscores=False)
):
    return {"user_agent": user_agent}
```

## 六、Cookie 参数

### Cookie 参数

```python
from fastapi import Cookie

@app.get("/cookies")
def get_cookies(
    session_id: Optional[str] = Cookie(None),
    theme: str = Cookie("light")
):
    return {"session_id": session_id, "theme": theme}
```

## 七、参数验证

### Query 参数验证

```python
from fastapi import Query

@app.get("/items")
def read_items(
    q: str = Query(..., min_length=1, max_length=50),
    page: int = Query(1, ge=1),  # ge = greater or equal
    size: int = Query(10, ge=1, le=100)  # le = less or equal
):
    return {"q": q, "page": page, "size": size}
```

### Path 参数验证

```python
from fastapi import Path

@app.get("/items/{item_id}")
def read_item(
    item_id: int = Path(..., ge=1),  # 必须 >= 1
    category: str = Path(..., min_length=1)
):
    return {"item_id": item_id, "category": category}
```

### 常用验证器

| 验证器 | 含义 | 示例 |
|--------|------|------|
| `ge` | 大于等于 | `ge=1` |
| `gt` | 大于 | `gt=0` |
| `le` | 小于等于 | `le=100` |
| `lt` | 小于 | `lt=0` |
| `min_length` | 最小长度 | `min_length=1` |
| `max_length` | 最大长度 | `max_length=50` |
| `regex` | 正则匹配 | `regex="^固定格式"` |

## 八、综合示例

### 股票查询 API

```python
from typing import Optional, List
from fastapi import Query

class Market(str, Enum):
    SH = "sh"
    SZ = "sz"
    BJ = "bj"

class DetectorType(str, Enum):
    PRICE = "price"
    VOLUME = "volume"

@app.get("/api/v1/stocks")
def query_stocks(
    # 路径/查询参数
    market: Optional[Market] = None,
    
    # 过滤参数
    code: Optional[str] = Query(None, min_length=6, max_length=6),
    name: Optional[str] = Query(None, min_length=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, gt=0),
    
    # 分页参数
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    
    # 排序
    sort_by: str = Query("code"),
    order: str = Query("asc"),
    
    # 输出控制
    fields: Optional[str] = None,  # "code,name,price"
    include_index: bool = False
):
    """综合查询接口"""
    
    # 构建查询
    filters = []
    if code:
        filters.append(f"code={code}")
    if name:
        filters.append(f"name contains '{name}'")
    if min_price:
        filters.append(f"price >= {min_price}")
    
    return {
        "filters": filters,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": 100
        },
        "sort": {
            "field": sort_by,
            "order": order
        },
        "items": []
    }
```

## 九、调试技巧

### 打印所有参数

```python
@app.api_route("/debug", methods=["GET"])
async def debug_request(request: Request):
    return {
        "path_params": request.path_params,
        "query_params": dict(request.query_params),
        "headers": dict(request.headers)
    }
```

### 使用 Pydantic 模型组织参数

```python
from pydantic import BaseModel

class StockQuery(BaseModel):
    code: Optional[str]
    name: Optional[str]
    min_price: Optional[float] = None
    max_price: Optional[float] = None

@app.post("/stocks/query")
def query_stocks(query: StockQuery):
    # 更好的类型组织
    pass
```

## 常见问题

### 1. 路径和查询参数冲突

```python
# ❌ 不好：容易混淆
@app.get("/items")
def read_items(id: int = Path(...)):
    # 路径参数和查询参数同名
    pass

# ✅ 好：明确区分
@app.get("/items/{item_id}")
def read_item(item_id: int):  # 路径参数
    pass
```

### 2. 参数验证失败

```python
# /items/abc → 422 Unprocessable Entity
# FastAPI 返回详细错误信息

{
    "detail": [
        {
            "loc": ["path", "item_id"],
            "msg": "value is not a valid integer",
            "type": "type_error.integer"
        }
    ]
}
```

## 练习题

1. 创建一个「计算器」API，支持加减乘除（用路径参数表示操作类型）
2. 创建「股票搜索」API，支持按代码、名称、价格范围搜索
3. 创建「分页列表」API，支持 page、page_size、排序
4. 创建「请求头信息」API，返回客户端的 User-Agent、Accept-Language
5. 用枚举类型定义「涨跌状态」（up/down/flat）

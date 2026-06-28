# Step 02: 请求参数 - 路径参数、查询参数、请求头

## 学习目标
掌握 FastAPI 接收用户请求数据的各种方式

## 概念速览

```python
# 路径参数
@app.get("/items/{item_id}")
def read_item(item_id: int):
    pass

# 查询参数
@app.get("/items")
def read_items(skip: int = 0, limit: int = 10):
    pass

# 可选参数
@app.get("/search")
def search(q: str | None = None):
    pass
```

## 任务

### 任务 1: 路径参数

创建 `demo_02_params.py`：

```python
from fastapi import FastAPI
from typing import Optional

app = FastAPI()

# 1. 基本路径参数
@app.get("/stocks/{stock_code}")
def get_stock(stock_code: str):
    """获取单只股票信息"""
    return {
        "code": stock_code,
        "name": "贵州茅台",
        "price": 1500.0
    }

# 2. 带类型的路径参数
@app.get("/prices/{price}")
def get_price_level(price: float):
    """根据价格级别返回不同信息"""
    if price < 100:
        level = "低价股"
    elif price < 500:
        level = "中价股"
    else:
        level = "高价股"
    return {"price": price, "level": level}

# 3. 枚举类型参数
from enum import Enum

class Market(str, Enum):
    SH = "sh"
    SZ = "sz"
    BJ = "bj"

@app.get("/market/{market}")
def get_market(market: Market):
    """枚举类型的路径参数"""
    markets = {
        Market.SH: "上海证券交易所",
        Market.SZ: "深圳证券交易所",
        Market.BJ: "北京证券交易所"
    }
    return {"market": market, "name": markets[market]}

# 4. 路径参数验证
@app.get("/validate/code/{code}")
def validate_code(code: str):
    """验证股票代码格式"""
    errors = []
    
    if not code.isdigit():
        errors.append("代码必须是数字")
    if len(code) != 6:
        errors.append("代码必须是6位")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    return {"valid": True, "code": code}
```

### 任务 2: 查询参数

```python
# 5. 查询参数
@app.get("/stocks")
def list_stocks(
    market: str = "sh",      # 查询参数，默认值
    limit: int = 10,         # 分页限制
    offset: int = 0           # 偏移量
):
    """列出股票列表"""
    return {
        "market": market,
        "limit": limit,
        "offset": offset,
        "total": 100,
        "items": [
            {"code": "600519", "name": "贵州茅台"},
            {"code": "600036", "name": "招商银行"},
        ]
    }

# 6. 可选参数
@app.get("/search")
def search_stocks(
    q: Optional[str] = None,  # 可选查询
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    """搜索股票"""
    results = [
        {"code": "600519", "name": "贵州茅台", "price": 1500},
        {"code": "000858", "name": "五粮液", "price": 150},
    ]
    
    if q:
        results = [s for s in results if q in s["name"]]
    
    if min_price:
        results = [s for s in results if s["price"] >= min_price]
    
    if max_price:
        results = [s for s in results if s["price"] <= max_price]
    
    return {"query": q, "results": results}

# 7. 布尔类型参数
@app.get("/analyze")
def analyze_stocks(
    include_index: bool = False,  # 布尔查询参数
    detailed: bool = False
):
    """分析股票"""
    return {
        "include_index": include_index,
        "detailed": detailed,
        "message": f"include_index={include_index}, detailed={detailed}"
    }
```

### 任务 3: 请求头和 Cookie

```python
# 8. 请求头参数
@app.get("/headers")
def get_headers(
    user_agent: Optional[str] = None,
    authorization: Optional[str] = None
):
    """获取请求头信息"""
    return {
        "user_agent": user_agent,
        "has_auth": authorization is not None
    }

# 9. Cookie 参数
@app.get("/cookies")
def get_cookies(session_id: Optional[str] = None):
    """获取 Cookie"""
    return {
        "session_id": session_id,
        "logged_in": session_id is not None
    }
```

### 任务 4: 综合示例

```python
# 10. 综合示例：股票行情接口
@app.get("/api/v1/quote")
def get_quote(
    code: str,
    include_history: bool = False,
    days: int = 5
):
    """
    获取股票行情
    
    参数:
        code: 股票代码（如 600519）
        include_history: 是否包含历史数据
        days: 历史天数
    """
    base = {
        "code": code,
        "name": "贵州茅台" if code == "600519" else "未知",
        "price": 1500.0,
        "change": 2.5,
        "change_pct": 0.17,
        "volume": 1000000,
        "timestamp": "2024-01-15 14:30:00"
    }
    
    if include_history:
        base["history"] = [
            {"date": "2024-01-14", "close": 1495.0},
            {"date": "2024-01-13", "close": 1480.0},
            {"date": "2024-01-12", "close": 1470.0},
        ][:days]
    
    return base
```

## 测试

```bash
# 测试路径参数
curl http://localhost:8000/stocks/600519
curl http://localhost:8000/prices/1500.5
curl http://localhost:8000/market/sh
curl http://localhost:8000/validate/code/600519
curl http://localhost:8000/validate/code/abc

# 测试查询参数
curl "http://localhost:8000/stocks?market=sz&limit=5"
curl "http://localhost:8000/search?q=茅台&min_price=1000"
curl "http://localhost:8000/analyze?detailed=true"
```

## 参数类型对比

| 类型 | 示例 | 说明 |
|------|------|------|
| 路径参数 | `/items/{id}` | URL 路径中的值 |
| 查询参数 | `/items?id=123` | URL 问号后面的值 |
| 请求头 | Header 头 | HTTP 请求头 |
| Cookie | Cookie 头 | 浏览器 Cookie |

## 下一步
阅读 `../docs/analysis/02_path_params.md` 深入理解

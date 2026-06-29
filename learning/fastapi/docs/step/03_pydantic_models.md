# Step 03: 请求体 - Pydantic 模型

## 学习目标
掌握 Pydantic 模型定义、请求体验证、响应模型

## 概念速览

```python
from pydantic import BaseModel

# 定义模型
class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

# 使用模型
@app.post("/items")
def create_item(item: Item):
    return item
```

## 任务

### 任务 1: 基本 Pydantic 模型

创建 `demo_03_body.py`：

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()

# 1. 基本模型
class Stock(BaseModel):
    """股票模型"""
    code: str                    # 必需字段
    name: str                    # 必需字段
    price: float                 # 必需字段
    change: float = 0.0          # 带默认值的可选字段
    volume: Optional[int] = None # 可选字段

# 2. 使用模型
@app.post("/stocks")
def create_stock(stock: Stock):
    """创建股票（接收请求体）"""
    # FastAPI 自动验证输入
    return {
        "created": True,
        "stock": stock
    }

@app.get("/stocks/{code}")
def get_stock(code: str):
    """获取股票（返回模型）"""
    return Stock(
        code=code,
        name="贵州茅台",
        price=1500.0,
        change=2.5,
        volume=1000000
    )
```

### 任务 2: 嵌套模型

```python
# 3. 嵌套模型
class Address(BaseModel):
    city: str
    district: Optional[str] = None

class Company(BaseModel):
    """公司模型（嵌套 Address）"""
    name: str
    address: Address             # 嵌套另一个模型
    employees: List[str] = []    # 列表字段

@app.post("/companies")
def create_company(company: Company):
    return {"created": True, "company": company}

# 4. 列表类型
class StockPrice(BaseModel):
    """股票价格记录"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class StockHistory(BaseModel):
    """股票历史行情"""
    code: str
    name: str
    prices: List[StockPrice]  # 股票价格列表

@app.post("/stocks/history")
def get_history(history: StockHistory):
    """处理历史行情数据"""
    return {
        "code": history.code,
        "total_days": len(history.prices),
        "avg_price": sum(p.close for p in history.prices) / len(history.prices)
    }
```

### 任务 3: 字段验证

```python
from pydantic import Field, validator

class ValidatedStock(BaseModel):
    """带验证的股票模型"""
    
    # 基础验证
    code: str = Field(..., min_length=6, max_length=6)  # 必需，6位
    name: str = Field(..., min_length=1, max_length=50)
    price: float = Field(..., gt=0)  # 必须大于0
    
    # 可选字段
    change: float = Field(default=0.0, ge=-10, le=10)  # 涨跌限制在 -10% 到 10%
    volume: Optional[int] = Field(None, ge=0)  # 成交量非负
    
    # 自定义验证器
    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit():
            raise ValueError('股票代码必须是6位数字')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('股票名称不能为空')
        return v.strip()

@app.post("/validated/stocks")
def create_validated_stock(stock: ValidatedStock):
    """使用验证模型的接口"""
    return {"valid": True, "stock": stock}
```

### 任务 4: 响应模型

```python
from pydantic import BaseModel, ConfigDict

# 5. 响应模型（只返回需要的字段）
class UserIn(BaseModel):
    """输入模型（包含所有字段）"""
    username: str
    email: str
    password: str  # 敏感字段

class UserOut(BaseModel):
    """输出模型（排除敏感字段）"""
    username: str
    email: str
    # password 不在输出模型中

@app.post("/users", response_model=UserOut)
def create_user(user: UserIn):
    """创建用户，只返回非敏感信息"""
    # 这里应该保存到数据库
    return UserOut(username=user.username, email=user.email)

# 6. 配置模型
class ConfiguredStock(BaseModel):
    """配置化的模型"""
    code: str
    name: str
    
    model_config = ConfigDict(
        str_strip_whitespace=True,  # 自动去除空白
        from_attributes=True,        # 支持从 ORM 对象创建
        populate_by_name=True       # 允许使用字段名或别名
    )

# 7. 可枚举的字段
from enum import Enum

class StockMarket(str, Enum):
    SH = "sh"
    SZ = "sz"
    BJ = "bj"

class MarketStock(BaseModel):
    code: str
    market: StockMarket
    name: str

@app.post("/market/stocks")
def create_market_stock(stock: MarketStock):
    return stock
```

### 任务 5: 综合示例

```python
# 8. 综合示例：异常检测请求
class AnomalyDetectorRequest(BaseModel):
    """异常检测请求模型"""
    stock_code: str = Field(..., description="股票代码")
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    detection_type: List[str] = Field(
        default=["price"],
        description="检测类型：price/volume/news"
    )
    threshold: float = Field(default=2.0, ge=0, le=10, description="检测阈值")
    include_details: bool = Field(default=False, description="是否包含详细信息")
    
    @validator('start_date', 'end_date')
    def validate_date(cls, v):
        import re
        if not re.match(r'\d{4}-\d{2}-\d{2}', v):
            raise ValueError('日期格式必须是 YYYY-MM-DD')
        return v

class AnomalyResult(BaseModel):
    """异常检测结果"""
    code: str
    date: str
    type: str
    value: float
    threshold: float
    severity: str

class AnomalyDetectorResponse(BaseModel):
    """异常检测响应模型"""
    request_id: str
    code: str
    total_records: int
    anomalies_found: int
    anomalies: List[AnomalyResult]

@app.post("/api/v1/detect/anomaly", response_model=AnomalyDetectorResponse)
def detect_anomaly(request: AnomalyDetectorRequest):
    """执行异常检测"""
    # 模拟检测逻辑
    return AnomalyDetectorResponse(
        request_id="req_123456",
        code=request.stock_code,
        total_records=100,
        anomalies_found=3,
        anomalies=[
            AnomalyResult(
                code=request.stock_code,
                date="2024-01-10",
                type="price",
                value=5.5,
                threshold=request.threshold,
                severity="high"
            )
        ]
    )
```

## 测试

```bash
# 测试基本模型
curl -X POST "http://localhost:8000/stocks" \
  -H "Content-Type: application/json" \
  -d '{"code": "600519", "name": "贵州茅台", "price": 1500.0}'

# 测试嵌套模型
curl -X POST "http://localhost:8000/companies" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "茅台集团",
    "address": {"city": "贵阳", "district": "仁怀"},
    "employees": ["张三", "李四"]
  }'

# 测试验证失败（会返回422错误）
curl -X POST "http://localhost:8000/validated/stocks" \
  -H "Content-Type: application/json" \
  -d '{"code": "123", "name": "茅台", "price": 1500}'
```

## 下一步
阅读 `../docs/analysis/03_pydantic_models.md` 深入理解

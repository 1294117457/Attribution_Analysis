# Pydantic 模型详解

## 一、为什么需要 Pydantic？

### 不用 Pydantic 的问题

```python
# ❌ 手动验证，繁琐且容易出错
@app.post("/stocks")
def create_stock(data: dict):
    if "code" not in data:
        raise ValueError("缺少 code")
    if not isinstance(data.get("price"), (int, float)):
        raise ValueError("price 必须是数字")
    if data["price"] <= 0:
        raise ValueError("price 必须大于0")
    # ... 更多验证
    return data
```

### 用 Pydantic 的好处

```python
# ✅ 声明式验证，简洁可靠
class Stock(BaseModel):
    code: str
    price: float = Field(..., gt=0)  # 自动验证
```

## 二、模型定义

### 基本模型

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int
```

### 字段类型

```python
from typing import Optional, List, Dict, Any

class Example(BaseModel):
    # 基本类型
    name: str
    age: int
    price: float
    is_active: bool
    
    # 可选类型
    nickname: Optional[str] = None
    email: str | None = None  # Python 3.10+
    
    # 容器类型
    tags: List[str] = []
    scores: Dict[str, int] = {}
    
    # Any 类型
    metadata: Any = None
```

## 三、Field 详解

### Field 参数

```python
from pydantic import Field

class Stock(BaseModel):
    # 必需字段
    code: str = Field(...)
    
    # 带默认值的可选字段
    name: str = Field(default="未知")
    
    # 带验证的字段
    price: float = Field(
        ...,           # 必需（... 是必填标记）
        gt=0,          # greater than > 0
        ge=0,          # greater or equal >= 0
        lt=10000,      # less than < 10000
        le=10000,      # less or equal <= 10000
    )
    
    # 字符串验证
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )
    
    # 正则验证
    code: str = Field(
        ...,
        pattern=r"^\d{6}$"  # 必须是6位数字
    )
    
    # 别名
    stock_code: str = Field(..., alias="code")
    
    # 描述（用于文档）
    price: float = Field(..., description="股票价格")
    
    # 示例值
    price: float = Field(1500.0, description="股票价格")
```

### 常用验证器

| 参数 | 含义 | 示例 |
|------|------|------|
| `gt` | 大于 | `gt=0` |
| `ge` | 大于等于 | `ge=1` |
| `lt` | 小于 | `lt=100` |
| `le` | 小于等于 | `le=100` |
| `min_length` | 最小长度 | `min_length=1` |
| `max_length` | 最大长度 | `max_length=50` |
| `pattern` | 正则 | `pattern=r"^\d{6}$"` |
| `regex` | 正则（同上） | `regex=r"^\d{6}$"` |

## 四、验证器

### @validator

```python
from pydantic import validator

class Stock(BaseModel):
    code: str
    name: str
    price: float
    
    @validator('code')
    def validate_code(cls, v):
        """验证股票代码"""
        if not v.isdigit():
            raise ValueError('股票代码必须是数字')
        if len(v) != 6:
            raise ValueError('股票代码必须是6位')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """清理股票名称"""
        return v.strip()  # 去除首尾空格
    
    @validator('price')
    def validate_price(cls, v):
        """验证价格"""
        if v <= 0:
            raise ValueError('价格必须大于0')
        if v > 100000:
            raise ValueError('价格超出合理范围')
        return v
```

### @field_validator (Pydantic V2)

```python
# Pydantic V2 使用 @field_validator
from pydantic import field_validator

class Stock(BaseModel):
    code: str
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('股票代码必须是数字')
        return v
```

### 多个字段验证

```python
class DateRange(BaseModel):
    start_date: str
    end_date: str
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """验证日期范围"""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('结束日期必须大于开始日期')
        return v
```

### @root_validator

```python
from pydantic import root_validator

class Stock(BaseModel):
    open_price: float
    close_price: float
    change: float
    
    @root_validator
    def validate_change(cls, values):
        """验证涨跌计算"""
        open_p = values.get('open_price')
        close_p = values.get('close_price')
        change = values.get('change')
        
        if all([open_p, close_p, change]):
            expected_change = close_p - open_p
            if abs(change - expected_change) > 0.01:
                raise ValueError('涨跌数据不一致')
        
        return values
```

## 五、嵌套模型

### 基本嵌套

```python
class Address(BaseModel):
    city: str
    street: str

class Company(BaseModel):
    name: str
    address: Address  # 嵌套

# 使用
company = Company(
    name="茅台",
    address={"city": "贵阳", "street": "茅台路"}  # dict 自动转 Address
)
```

### 列表嵌套

```python
class Price(BaseModel):
    date: str
    close: float

class StockHistory(BaseModel):
    code: str
    prices: List[Price]  # Price 对象列表
```

### Dict 类型

```python
class Config(BaseModel):
    settings: Dict[str, Any]  # 任意键值对
    tags: Dict[str, List[str]]  # 嵌套

config = Config(
    settings={"debug": True, "timeout": 30},
    tags={"stock": ["茅台", "五粮液"]}
)
```

## 六、模型配置

### model_config

```python
class Stock(BaseModel):
    code: str
    name: str
    price: float
    
    model_config = ConfigDict(
        # 从 ORM 或 dataclass 创建
        from_attributes=True,
        
        # 去除首尾空白
        str_strip_whitespace=True,
        
        # 允许使用字段别名
        populate_by_name=True,
        
        # JSON schema 配置
        json_schema_extra={
            "example": {
                "code": "600519",
                "name": "贵州茅台",
                "price": 1500.0
            }
        }
    )
```

### BaseModel 的类属性

```python
class Stock(BaseModel):
    # 类级别的配置
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )
    
    # 字段定义
    code: str
    name: str = "未知"  # 默认值
```

## 七、输入输出模型分离

### 分离的好处

```python
class UserInput(BaseModel):
    """输入模型（允许所有字段）"""
    username: str
    email: str
    password: str  # 敏感字段
    bio: Optional[str] = None

class UserOutput(BaseModel):
    """输出模型（排除敏感字段）"""
    username: str
    email: str
    bio: Optional[str] = None
    # 没有 password 字段

@app.post("/users", response_model=UserOutput)
def create_user(user: UserInput):
    # 处理逻辑
    return UserOutput(
        username=user.username,
        email=user.email,
        bio=user.bio
    )
```

### 使用 response_model_exclude

```python
class User(BaseModel):
    username: str
    email: str
    password: str
    internal_id: str

@app.get("/users/{id}", response_model=User)
def get_user(id: str):
    # response_model_exclude=["password", "internal_id"]
    # 可以排除特定字段
    pass
```

## 八、枚举类型

```python
from enum import Enum

class StockMarket(str, Enum):
    SH = "sh"
    SZ = "sz"
    BJ = "bj"

class Stock(BaseModel):
    code: str
    market: StockMarket  # 枚举字段
    
# 使用
stock = Stock(code="600519", market=StockMarket.SH)
stock = Stock(code="600519", market="sh")  # 也可以用字符串
```

## 九、与其他工具集成

### 与 FastAPI 结合

```python
@app.post("/stocks")
def create_stock(stock: Stock):  # 自动验证请求体
    return stock

@app.get("/stocks", response_model=List[Stock])  # 自动序列化
def list_stocks():
    return [Stock(code="600519", name="贵州茅台", price=1500)]
```

### 与数据库 ORM 结合

```python
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class StockDB(Base):
    __tablename__ = "stocks"
    code = Column(String, primary_key=True)
    name = Column(String)
    price = Column(Integer)

class Stock(BaseModel):
    code: str
    name: str
    price: float
    
    model_config = ConfigDict(from_attributes=True)  # 从 ORM 创建

@app.get("/stocks/{code}", response_model=Stock)
def get_stock(code: str):
    stock_db = db.query(StockDB).filter_by(code=code).first()
    return Stock.model_validate(stock_db)  # ORM → Pydantic
```

## 十、常见问题

### 1. 日期时间处理

```python
from datetime import datetime
from pydantic import field_validator

class Event(BaseModel):
    timestamp: datetime
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v
```

### 2. 默认值问题

```python
class Example(BaseModel):
    # ❌ mutable default 问题
    items: List[str] = []  # 不好，列表是可变对象
    
    # ✅ 用 Field
    items: List[str] = Field(default_factory=list)
```

### 3. None vs 默认值

```python
class Example(BaseModel):
    # Optional[str] = None：可以传 None，也可以不传
    name: Optional[str] = None
    
    # str = None：效果类似
    name: str = None
```

## 练习题

1. 创建一个「用户注册」模型，包含用户名、邮箱、密码（密码长度6-20位）
2. 创建一个「订单」模型，包含订单号、商品列表、总价，验证总价等于商品价格之和
3. 创建一个嵌套的「公司」模型，包含部门列表，每个部门有员工列表
4. 用 Pydantic 模型重构你的股票分析数据模型
5. 创建一个支持 JSON 和 YAML 两种格式输入的模型

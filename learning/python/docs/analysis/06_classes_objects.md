# 类和对象详解

## 一、面向对象基础概念

### 生活中的类比

| 概念 | 生活中的例子 | 股票系统中的例子 |
|------|-------------|-----------------|
| 类 (Class) | "汽车"的设计图 | "股票"模板 |
| 对象 (Object) | 具体的某辆车 | 贵州茅台这只股票 |
| 属性 (Attribute) | 车的颜色、品牌 | 股票代码、价格 |
| 方法 (Method) | 车的启动、刹车 | 股票更新价格、计算涨跌 |

### 为什么要用面向对象？

```python
# 方式1：使用字典（函数式）
stock1 = {"code": "600519", "name": "贵州茅台", "price": 1500}
stock2 = {"code": "000858", "name": "五粮液", "price": 150}

def update_price(stock, new_price):
    stock["price"] = new_price

def get_change(stock):
    return stock["price"] - stock["open_price"]

# 问题：可以随便修改任何字段，没有约束
stock1["name"] = "假的股票"  # ❌ 没有校验

# 方式2：使用类（面向对象）
class Stock:
    def __init__(self, code, name, price):
        self.code = code      # 只读
        self.name = name      # 只读
        self.price = price
    
    def update_price(self, new_price):
        if new_price < 0:
            raise ValueError("价格不能为负")
        self.price = new_price

stock1 = Stock("600519", "贵州茅台", 1500)
stock1.update_price(1550)
# stock1.code = "000000"  # ❌ 难以限制，但比字典好
```

## 二、类的定义

### 基本结构

```python
class 类名:
    """类的文档字符串"""
    
    # 类属性（可选）
    类属性 = 值
    
    def __init__(self, 参数):
        """构造函数，创建对象时自动调用"""
        self.实例属性 = 参数
    
    def 方法(self, 参数):
        """实例方法，第一个参数总是 self"""
        return 结果
```

### self 是什么？

self 是**当前对象**的引用，类似于 Java/JS 中的 this：

```python
class Stock:
    def __init__(self, code, name):
        # self 是当前创建的股票对象
        self.code = code      # 给当前对象的 code 属性赋值
        self.name = name      # 给当前对象的 name 属性赋值
    
    def display(self):
        # self 是调用此方法的那个对象
        return f"{self.name}({self.code})"  # 访问当前对象的属性

stock = Stock("600519", "贵州茅台")
stock.display()  # self = stock
```

## 三、构造函数 __init__

```python
class Example:
    def __init__(self, a, b=10):
        """初始化方法"""
        self.a = a
        self.b = b
        self.result = a + b  # 可以计算初始值

obj = Example(5)      # a=5, b=10
obj = Example(5, 20) # a=5, b=20
```

### 不使用 __init__ 的写法

```python
class Stock:
    def __init__(self, code, name, price):
        self.code = code
        self.name = name
        self.price = price
    
    def set_price(self, price):
        """也可以用普通方法设置"""
        self.price = price

# 两种方式对比：
# __init__: 创建时必须提供
# set_xxx: 创建后可选设置
```

## 四、实例属性 vs 类属性

```python
class Stock:
    market = "A股"  # 类属性：所有实例共享
    
    def __init__(self, code, name, price):
        self.code = code    # 实例属性：每个实例独立
        self.name = name
        self.price = price

# 访问方式
Stock.market           # 通过类名访问
stock1.market          # 通过实例访问（不建议）
Stock.market = "美股"  # 修改类属性，所有实例都变
```

### 常见用途

```python
class Config:
    """配置类"""
    VERSION = "1.0.0"           # 版本号
    DEBUG = True                # 调试模式
    MAX_RETRIES = 3             # 最大重试次数

class Counter:
    """计数器类"""
    total = 0  # 类属性：记录总数
    
    def __init__(self):
        Counter.total += 1  # 每次创建实例，总数+1
```

## 五、特殊方法

### __str__ 和 __repr__

```python
class Stock:
    def __init__(self, code, name, price):
        self.code = code
        self.name = name
        self.price = price
    
    def __str__(self):
        """用户友好的字符串"""
        return f"{self.name}({self.code}): {self.price}"
    
    def __repr__(self):
        """开发者友好的字符串（可以重建对象）"""
        return f"Stock('{self.code}', '{self.name}', {self.price})"

stock = Stock("600519", "贵州茅台", 1500)

print(str(stock))    # 贵州茅台(600519): 1500
print(repr(stock))   # Stock('600519', '贵州茅台', 1500)

# 用于调试和日志
print(f"Debug: {repr(stock)}")
```

### __eq__ 比较

```python
class Stock:
    def __init__(self, code, price):
        self.code = code
        self.price = price
    
    def __eq__(self, other):
        """定义 == 比较"""
        if not isinstance(other, Stock):
            return False
        return self.code == other.code

stock1 = Stock("600519", 1500)
stock2 = Stock("600519", 1600)
stock3 = Stock("000858", 1500)

print(stock1 == stock2)  # True (代码相同)
print(stock1 == stock3)  # False (代码不同)
```

## 六、Python vs JavaScript 对比

| Python | JavaScript | 说明 |
|--------|------------|------|
| `class Foo:` | `class Foo { }` | 定义类 |
| `def __init__(self, x):` | `constructor(x) { }` | 构造函数 |
| `self.x` | `this.x` | 引用自身 |
| `def method(self):` | `method() { }` | 方法 |
| `self.x = value` | `this.x = value` | 赋值 |
| `@property` | getter/setter | 属性装饰器 |

```python
# Python
class Stock:
    def __init__(self, code, price):
        self.code = code
        self._price = price  # 私有（约定）
    
    @property
    def price(self):
        return self._price
    
    @price.setter
    def price(self, value):
        if value < 0:
            raise ValueError("价格不能为负")
        self._price = value
```

```javascript
// JavaScript
class Stock {
    #price;  // 私有字段（ES2022）
    
    constructor(code, price) {
        this.code = code;
        this.#price = price;
    }
    
    get price() {
        return this.#price;
    }
}
```

## 七、实战应用

### 数据模型类

```python
from datetime import datetime

class Stock:
    """股票数据模型"""
    
    def __init__(self, code, name, open_price, close_price, volume):
        self.code = code
        self.name = name
        self.open_price = open_price
        self.close_price = close_price
        self.volume = volume
        self.timestamp = datetime.now()
    
    @property
    def change(self):
        return self.close_price - self.open_price
    
    @property
    def change_pct(self):
        return (self.change / self.open_price) * 100
    
    def to_dict(self):
        """转换为字典"""
        return {
            "code": self.code,
            "name": self.name,
            "open": self.open_price,
            "close": self.close_price,
            "change": self.change,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self):
        sign = "+" if self.change > 0 else ""
        return f"{self.name}: {self.close_price} ({sign}{self.change_pct:.2f}%)"

# 使用
stock = Stock("600519", "贵州茅台", 1480, 1500, 100000)
print(stock)
print(stock.change_pct)
```

## 常见错误

### 1.忘记 self
```python
# ❌ 错误
def __init__(self, code, name):
    code = code      # 只是创建局部变量
    name = name

# ✅ 正确
def __init__(self, code, name):
    self.code = code
    self.name = name
```

### 2. 类属性和实例属性混淆
```python
class Counter:
    count = 0  # 类属性
    
    def __init__(self):
        self.count = 0  # 实例属性（同名）
```

## 练习题

1. 创建一个 `Student` 类，包含姓名、年龄、成绩属性
2. 给 `Student` 类添加计算平均成绩的方法
3. 创建一个 `Rectangle` 类，计算面积和周长
4. 创建一个 `BankAccount` 类，支持存款、取款、查询余额
5. 用类来重构股票分析代码

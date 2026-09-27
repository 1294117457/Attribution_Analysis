# 函数定义详解

## 一、为什么要用函数？

### 没有函数的问题

```python
# 问题1：重复代码
print("=== 贵州茅台 ===")
print("代码: 600519")
print("价格: 1500")
print("涨跌: +2.5%")

print("=== 五粮液 ===")
print("代码: 000858")
print("价格: 150")
print("涨跌: -1.2%")

# 问题2：修改困难
# 如果要改格式，需要改很多地方
```

### 使用函数的好处

```python
# 定义一次，多次使用
def print_stock(code, name, price, change):
    """打印股票信息"""
    sign = "+" if change > 0 else ""
    emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
    print(f"=== {name} ===")
    print(f"代码: {code}")
    print(f"价格: {price}")
    print(f"涨跌: {sign}{change}% {emoji}")

# 多次调用，代码简洁
print_stock("600519", "贵州茅台", 1500, 2.5)
print_stock("000858", "五粮液", 150, -1.2)
```

## 二、函数定义语法

```python
def 函数名(参数1, 参数2, ...):
    """文档字符串（可选但推荐）"""
    函数体
    return 返回值  # 可选
```

### 关键点

1. `def` 是定义函数的关键字
2. 函数名遵循变量命名规则（小写+下划线）
3. 括号内的参数是输入
4. `return` 是输出，没有 return 默认返回 None

## 三、参数详解

### 1. 位置参数

按顺序传递，必须提供：
```python
def greet(first_name, last_name):
    return f"{last_name}{first_name}"

greet("三", "张")  # "张三"
```

### 2. 默认参数

提供默认值，可省略：
```python
def greet(name, greeting="你好"):
    return f"{greeting}，{name}！"

greet("张三")           # "你好，张三！"
greet("李四", "早上好")  # "早上好，李四！"
```

**注意**：默认参数要放在非默认参数后面！

```python
# ❌ 错误
def greet(greeting="你好", name):
    pass

# ✅ 正确
def greet(name, greeting="你好"):
    pass
```

### 3. 关键字参数

用参数名指定，不依赖顺序：
```python
def create_user(name, age, city):
    return {"name": name, "age": age, "city": city}

create_user(age=25, name="张三", city="北京")  # 顺序无所谓
```

### 4. 不定长参数

处理不确定数量的参数：
```python
# *args：接收任意数量的位置参数（变成元组）
def sum_all(*numbers):
    print(f"收到 {len(numbers)} 个数字")
    return sum(numbers)

print(sum_all(1, 2, 3))      # 6
print(sum_all(1, 2, 3, 4, 5))  # 15

# **kwargs：接收任意数量的关键字参数（变成字典）
def print_info(**info):
    for key, value in info.items():
        print(f"{key}: {value}")

print_info(name="张三", age=25, city="北京")
```

### 5. 参数组合

```python
def func(req1, req2, *args, default="default", **kwargs):
    print(f"必选: {req1}, {req2}")
    print(f"默认: {default}")
    print(f"额外位置参数: {args}")
    print(f"额外关键字参数: {kwargs}")

func(1, 2, 3, 4, default="modified", name="张三", age=25)
# 输出:
# 必选: 1, 2
# 默认: modified
# 额外位置参数: (3, 4)
# 额外关键字参数: {'name': '张三', 'age': 25}
```

## 四、返回值详解

### 1. 单返回值

```python
def add(a, b):
    return a + b

result = add(3, 5)  # 8
```

### 2. 多返回值

Python 实际返回的是**元组**：
```python
def get_stats(numbers):
    return max(numbers), min(numbers), sum(numbers) / len(numbers)

# 解包赋值
highest, lowest, average = get_stats([1, 2, 3, 4, 5])

# 也可以作为一个元组接收
result = get_stats([1, 2, 3, 4, 5])  # (5, 1, 3.0)
```

### 3. 提前返回

```python
def find_stock(code, stocks):
    """查找股票，找到就返回"""
    for stock in stocks:
        if stock["code"] == code:
            return stock
    
    # 没找到，返回 None
    return None

stocks = [
    {"code": "600519", "name": "贵州茅台"},
    {"code": "000858", "name": "五粮液"},
]

result = find_stock("600519", stocks)
if result:
    print(f"找到: {result['name']}")
else:
    print("未找到")
```

### 4. 没有 return

没有 return 语句的函数返回 None：
```python
def say_hello(name):
    print(f"你好，{name}！")

result = say_hello("张三")  # 打印 "你好，张三！"
print(result)  # None
```

## 五、文档字符串

用三个引号包裹，说明函数用途：
```python
def calculate_change(open_price, close_price):
    """
    计算股票涨跌额和涨跌幅
    
    参数:
        open_price: 开盘价
        close_price: 收盘价
    
    返回:
        tuple: (涨跌额, 涨跌幅百分比)
    
    示例:
        >>> calculate_change(100, 105)
        (5, 5.0)
    """
    change = close_price - open_price
    change_pct = (change / open_price) * 100
    return change, change_pct
```

## 六、Python vs JavaScript 对比

| Python | JavaScript | 说明 |
|--------|------------|------|
| `def func():` | `function func() {}` | 定义函数 |
| `def func(a, b=1):` | `function func(a, b=1) {}` | 默认参数 |
| `func(*args)` | `func(...args)` | 不定长参数 |
| `return a, b` | `return [a, b]` | 多返回值 |
| `"""文档"""` | `/** 文档 */` | 文档注释 |

## 七、实战模式

### 模式1：配置函数

```python
# 把配置提取为函数参数
def fetch_data(url, method="GET", headers=None, timeout=30):
    # 默认值处理
    if headers is None:
        headers = {}
    
    # 实际逻辑
    print(f"{method} {url} (timeout={timeout}s)")
    return {"status": "ok"}

fetch_data("https://api.example.com/data")
fetch_data("https://api.example.com/users", "POST", timeout=60)
```

### 模式2：工厂函数

```python
# 根据条件返回不同的对象
def create_analyzer(analyzer_type):
    """创建分析器"""
    if analyzer_type == "price":
        return PriceAnalyzer()
    elif analyzer_type == "volume":
        return VolumeAnalyzer()
    else:
        raise ValueError(f"未知的分析器类型: {analyzer_type}")

analyzer = create_analyzer("price")
```

### 模式3：回调函数

```python
# 把函数作为参数传递
def process_data(data, transform):
    """对数据应用转换函数"""
    return [transform(item) for item in data]

prices = [100, 150, 200]
doubled = process_data(prices, lambda x: x * 2)  # [200, 300, 400]
formatted = process_data(prices, lambda x: f"¥{x}")  # ["¥100", "¥150", "¥200"]
```

## 常见错误

### 1. 默认参数用可变对象
```python
# ❌ 错误：默认参数被共享
def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item("a"))  # ['a']
print(add_item("b"))  # ['a', 'b']  # 应该是 ['b']！

# ✅ 正确：None 作为默认值
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### 2. 修改全局变量
```python
# ❌ 不好：隐式修改全局变量
counter = 0
def increment():
    counter += 1  # UnboundLocalError

# ✅ 正确：显式使用 global 或传参
counter = 0
def increment():
    global counter
    counter += 1
```

## 练习题

1. 写一个函数，计算 BMI（体质指数）：体重(kg) / 身高(m)²
2. 写一个函数，接收任意数量的数字，返回最大值和最小值
3. 写一个函数，根据股票代码返回交易所（上交所600/601/688，深交所000/001/002/003）
4. 写一个"计算器"函数，支持加、减、乘、除四种运算
5. 重构股票分析代码，把计算逻辑抽成函数

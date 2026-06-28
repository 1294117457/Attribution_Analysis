# 列表和字典详解

## 一、列表 (List)

### 什么是列表？

列表是一个**有序的、可变的**元素集合。你可以把它想象成一行储物柜，每个格子可以放一个值。

```python
# 列表的特点
fruits = ["苹果", "香蕉", "橙子"]
# 索引:    [0]    [1]    [2]
```

### 创建列表

```python
# 方式1：直接创建
empty = []                    # 空列表
numbers = [1, 2, 3, 4, 5]   # 数字列表
mixed = [1, "hello", True]   # 混合类型（不推荐）

# 方式2：列表推导式
squares = [x ** 2 for x in range(1, 6)]  # [1, 4, 9, 16, 25]

# 方式3：list() 函数
chars = list("hello")  # ['h', 'e', 'l', 'l', 'o']
nums = list(range(5)) # [0, 1, 2, 3, 4]
```

### 索引和切片

```python
prices = [100, 150, 200, 250, 300]

# 正向索引：从0开始
prices[0]   # 第一个: 100
prices[1]   # 第二个: 150
prices[4]   # 第五个: 300

# 负向索引：从-1开始（最后一个）
prices[-1]   # 最后一个: 300
prices[-2]   # 倒数第二个: 250

# 切片 [start:end]，不包含 end
prices[1:4]   # [150, 200, 250]
prices[:3]    # 从开头到索引2: [100, 150, 200]
prices[3:]    # 从索引3到结尾: [250, 300]
prices[:]     # 复制整个列表

# 步长切片
prices[::2]   # 每隔一个取: [100, 200, 300]
prices[::-1]  # 反转: [300, 250, 200, 150, 100]
```

### 列表操作

```python
fruits = ["苹果", "香蕉"]

# 添加
fruits.append("橙子")      # 末尾添加: ["苹果", "香蕉", "橙子"]
fruits.insert(1, "葡萄")   # 指定位置添加: ["苹果", "葡萄", "香蕉", "橙子"]
fruits.extend(["草莓", "西瓜"])  # 批量添加

# 删除
fruits.pop()               # 移除末尾: "西瓜"
fruits.pop(0)             # 移除指定位置
fruits.remove("香蕉")      # 移除指定值（第一个匹配）
del fruits[0]             # del 语句删除

# 修改
fruits[0] = "梨"          # 修改元素

# 查询
fruits.index("橙子")       # 查找索引
fruits.count("苹果")       # 计数
"香蕉" in fruits          # 是否存在: True
```

### 常用函数

```python
numbers = [3, 1, 4, 1, 5, 9, 2, 6]

len(numbers)    # 长度: 8
max(numbers)    # 最大值: 9
min(numbers)    # 最小值: 1
sum(numbers)    # 求和: 31
sorted(numbers) # 排序（返回新列表）
numbers.sort()  # 排序（原地修改）
```

## 二、字典 (Dict)

### 什么是字典？

字典是**键值对**的集合，通过键来访问值。就像真实的字典：通过拼音（键）查汉字（值）。

```python
person = {"name": "张三", "age": 25, "city": "北京"}
# 键:         "name"    "age"     "city"
# 值:          "张三"     25        "北京"
```

### 创建字典

```python
# 方式1：直接创建
person = {"name": "张三", "age": 25}

# 方式2：dict() 函数
person = dict(name="张三", age=25)

# 方式3：空字典
person = {}
person["name"] = "张三"

# 方式4：字典推导式
squares = {x: x**2 for x in range(1, 6)}  # {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}
```

### 访问字典

```python
stock = {"code": "600519", "name": "贵州茅台", "price": 1500}

# 访问值
stock["name"]              # "贵州茅台"
stock.get("code")          # "600519"

# 安全访问（键不存在时返回默认值）
stock.get("industry", "未知")  # "未知"（因为 industry 键不存在）

# ❌ 错误访问
stock["industry"]  # KeyError: 'industry'
```

### 字典操作

```python
stock = {"code": "600519", "name": "贵州茅台"}

# 添加/修改
stock["price"] = 1500      # 添加
stock["name"] = "五粮液"   # 修改已存在的键

# 删除
del stock["name"]          # 删除键值对
price = stock.pop("price") # 删除并返回值

# 清空
stock.clear()              # 变成空字典 {}
```

### 遍历字典

```python
person = {"name": "张三", "age": 25, "city": "北京"}

# 遍历键
for key in person:
    print(key)

# 遍历值
for value in person.values():
    print(value)

# 遍历键值对
for key, value in person.items():
    print(f"{key}: {value}")

# 转成列表
keys = list(person.keys())
values = list(person.values())
items = list(person.items())  # [("name", "张三"), ("age", 25), ...]
```

## 三、列表推导式 vs 字典推导式

### 列表推导式

```python
# 基本形式：[表达式 for 变量 in 可迭代对象]
squares = [x**2 for x in range(5)]  # [0, 1, 4, 9, 16]

# 带条件：[表达式 for 变量 in 可迭代对象 if 条件]
evens = [x for x in range(10) if x % 2 == 0]  # [0, 2, 4, 6, 8]

# 带 if-else：[表达式1 if 条件 else 表达式2 for 变量 in 可迭代对象]
labels = ["偶数" if x % 2 == 0 else "奇数" for x in range(5)]  # ["偶数", "奇数", "偶数", "奇数", "偶数"]
```

### 字典推导式

```python
# 基本形式：{键: 值 for 变量 in 可迭代对象}
prices = {"苹果": 5, "香蕉": 3, "橙子": 4}
double_prices = {k: v*2 for k, v in prices.items()}  # {"苹果": 10, "香蕉": 6, "橙子": 8}

# 带条件
filtered = {k: v for k, v in prices.items() if v > 3}  # {"苹果": 5, "橙子": 4}
```

## 四、嵌套结构

```python
# 列表中嵌套字典
stocks = [
    {"code": "600519", "name": "贵州茅台", "price": 1500},
    {"code": "000858", "name": "五粮液", "price": 150},
    {"code": "600036", "name": "招商银行", "price": 35},
]

# 访问嵌套数据
stocks[0]["name"]                    # "贵州茅台"
for stock in stocks:
    print(f"{stock['name']}: {stock['price']}")

# 字典中嵌套列表
person = {
    "name": "张三",
    "skills": ["Python", "JavaScript", "Go"],
    "contacts": {"phone": "123456", "email": "zhang@example.com"}
}

person["skills"][0]                 # "Python"
person["contacts"]["email"]          # "zhang@example.com"
```

## 五、在 FastAPI 中的应用

```python
# 请求体是字典
from pydantic import BaseModel

class Stock(BaseModel):
    code: str
    name: str
    price: float
    change: float

# 查询参数是列表
@router.get("/stocks")
async def get_stocks(codes: list[str]):  # list[str] 类型
    stocks = []
    for code in codes:
        stocks.append({"code": code, "name": get_name(code)})
    return stocks

# 响应是字典
return {
    "total": len(stocks),
    "items": stocks,
    "page": 1
}
```

## 六、Python vs JavaScript 对比

| Python | JavaScript | 说明 |
|--------|------------|------|
| `[]` | `[]` | 空列表/数组 |
| `{}` | `{}` | 空字典/对象 |
| `[1, 2, 3]` | `[1, 2, 3]` | 列表/数组 |
| `{"a": 1}` | `{"a": 1}` | 字典/对象 |
| `list[0]` | `arr[0]` | 访问元素 |
| `dict["key"]` | `obj.key` 或 `obj["key"]` | 访问值 |
| `list.append()` | `arr.push()` | 添加元素 |
| `list.keys()` | `Object.keys()` | 获取键 |
| `[x for x in list]` | `list.map(x => x)` | 映射 |

## 常见错误

### 1. 索引越界
```python
# ❌ 错误
nums = [1, 2, 3]
print(nums[3])  # IndexError: list index out of range

# ✅ 正确：先检查长度
if len(nums) > 3:
    print(nums[3])
```

### 2. 键不存在
```python
# ❌ 错误
person = {"name": "张三"}
print(person["age"])  # KeyError: 'age'

# ✅ 正确：用 get
print(person.get("age", 0))  # 0
```

### 3. 修改列表时迭代
```python
# ❌ 错误：边迭代边删除
nums = [1, 2, 3, 4, 5]
for n in nums:
    if n % 2 == 0:
        nums.remove(n)  # 可能漏掉元素

# ✅ 正确：遍历副本
for n in nums[:]:  # nums[:] 是副本
    if n % 2 == 0:
        nums.remove(n)
```

## 练习题

1. 创建股票列表，找出价格最高和最低的
2. 用列表推导式：生成 1-100 中所有能被 3 和 5 同时整除的数
3. 将两个列表合并成一个字典（一个当键，一个当值）
4. 统计一篇文章中每个单词出现的次数
5. 模拟购物车：添加商品、删除商品、修改数量、计算总价

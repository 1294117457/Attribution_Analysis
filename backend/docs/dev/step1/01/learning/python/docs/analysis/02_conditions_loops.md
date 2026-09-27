# 条件判断和循环详解

## 一、条件判断 (if/elif/else)

### 基本语法

```python
if 条件1:
    # 条件1成立时执行
    代码块
elif 条件2:
    # 条件2成立时执行
    代码块
else:
    # 所有条件都不成立时执行
    代码块
```

### 关键点

1. **缩进很重要**：Python 用缩进（4个空格）来区分代码块
2. **elif 是 else if 的缩写**：可以有多个 elif
3. **else 是可选的**：可以只有 if

### 条件表达式

```python
# 比较运算符
x == y      # 等于
x != y      # 不等于
x > y       # 大于
x < y       # 小于
x >= y      # 大于等于
x <= y      # 小于等于

# 逻辑运算符
x and y     # 且（两个都成立）
x or y      # 或（至少一个成立）
not x       # 非（取反）

# 身份运算符
x is y      # 是同一个对象
x is not y  # 不是同一个对象

# 成员运算符
x in y      # 在序列中
x not in y  # 不在序列中
```

### 陷阱：= 和 ==

```python
# ❌ 错误：这是赋值，不是比较
if x = 10:
    print("x是10")

# ✅ 正确：这是比较
if x == 10:
    print("x是10")
```

### 三元表达式（简写）

```python
# 普通写法
if x > 0:
    result = "正数"
else:
    result = "非正数"

# 简写：一行搞定
result = "正数" if x > 0 else "非正数"
```

## 二、for 循环

### 基本语法

```python
for 变量 in 序列:
    每次循环执行的代码
```

### range() 函数

```python
range(5)           # 0, 1, 2, 3, 4（不包含5）
range(1, 6)        # 1, 2, 3, 4, 5
range(0, 10, 2)    # 0, 2, 4, 6, 8（步长为2）
range(5, 0, -1)    # 5, 4, 3, 2, 1（倒序）
```

### 遍历各种类型

```python
# 遍历字符串
for char in "Python":
    print(char)  # P, y, t, h, o, n

# 遍历列表
fruits = ["苹果", "香蕉", "橙子"]
for fruit in fruits:
    print(fruit)

# 遍历字典
person = {"name": "张三", "age": 25}
for key in person:           # 只遍历键
    print(key)
for key, value in person.items():  # 遍历键值对
    print(f"{key}: {value}")
for value in person.values():      # 只遍历值
    print(value)
```

### enumerate() - 带索引遍历

```python
fruits = ["苹果", "香蕉", "橙子"]

for index, fruit in enumerate(fruits):
    print(f"{index}: {fruit}")
# 输出:
# 0: 苹果
# 1: 香蕉
# 2: 橙子
```

## 三、while 循环

### 基本语法

```python
while 条件:
    条件成立时执行的代码
```

### 特点
- 先判断条件，条件成立才执行
- 需要确保条件最终会变为 False，否则是死循环

```python
# 正确示例
count = 0
while count < 3:
    print(count)
    count += 1  # 很重要！确保最终会退出

# 危险示例：死循环
# while True:
#     print("永远执行")
```

## 四、break 和 continue

```python
# break：跳出整个循环
for i in range(10):
    if i == 5:
        break  # 遇到5就完全退出循环
    print(i, end=" ")
# 输出: 0 1 2 3 4

print()

# continue：跳过本次循环，继续下一次
for i in range(5):
    if i == 2:
        continue  # 跳过2，继续执行后面的循环
    print(i, end=" ")
# 输出: 0 1 3 4
```

## 五、Python vs JavaScript 对比

| Python | JavaScript | 说明 |
|--------|------------|------|
| `if x > 0:` | `if (x > 0) { }` | JS 需要括号和大括号 |
| `elif` | `else if` | Python 简写，JS 没简写 |
| `for x in list:` | `for (let x of list)` | 遍历方式类似 |
| `range(5)` | `[0,1,2,3,4]` 或 `Array.from` | 生成序列 |
| 缩进决定代码块 | 大括号决定代码块 | 缩进风格不同 |

```python
# Python
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
else:
    grade = "C"

for i in range(5):
    print(i)
```

```javascript
// JavaScript
if (score >= 90) {
    grade = "A";
} else if (score >= 80) {
    grade = "B";
} else {
    grade = "C";
}

for (let i = 0; i < 5; i++) {
    console.log(i);
}
```

## 六、实战应用

### 在 FastAPI 中的应用

```python
# 路径参数类型验证
@router.get("/stocks/{code}")
async def get_stock(code: str):
    # code 会自动从 URL 提取
    if code.startswith("6"):
        market = "上海"
    elif code.startswith("0") or code.startswith("3"):
        market = "深圳"
    else:
        market = "未知"
    return {"code": code, "market": market}
```

### 在数据处理中的应用

```python
# 筛选符合条件的股票
stocks = [
    {"code": "600519", "price": 1500, "change": 2.5},
    {"code": "000858", "price": 150, "change": -3.2},
    {"code": "600036", "price": 35, "change": 1.5},
]

# 筛选涨幅大于0的
rising_stocks = []
for stock in stocks:
    if stock["change"] > 0:
        rising_stocks.append(stock)

print(f"上涨股票数: {len(rising_stocks)}")
```

## 常见错误

### 1. 忘记冒号
```python
# ❌ 错误
if x > 0
    print(x)

# ✅ 正确
if x > 0:
    print(x)
```

### 2. 缩进不一致
```python
# ❌ 错误：缩进混乱
if x > 0:
    print(x)
  print("done")

# ✅ 正确：统一4个空格
if x > 0:
    print(x)
print("done")
```

### 3. 死循环
```python
# ❌ 错误：忘记更新条件
count = 0
while count < 5:
    print(count)
    # 忘记 count += 1

# ✅ 正确：更新条件
count = 0
while count < 5:
    print(count)
    count += 1
```

## 练习题

1. 写一个程序：根据分数输出等级（90+ A, 80+ B, 70+ C, 60+ D, 60以下 F）
2. 用 for 循环计算 1+2+3+...+100 的和
3. 遍历股票列表，找出价格最高的那只
4. 用 while 循环实现：不断让用户输入，直到输入 "quit" 为止

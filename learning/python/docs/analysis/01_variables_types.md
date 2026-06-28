# 变量和数据类型详解

## 为什么先学变量和数据类型？

变量是编程的**地基**。就像盖房子要先打地基一样，学编程先理解变量，就理解了：
- 数据存在哪里（变量名）
- 数据是什么（数据类型）
- 数据怎么用（操作和转换）

## 一、变量到底是什么？

### 生活中的类比

| 概念 | 生活类比 | 代码 |
|------|----------|------|
| 变量名 | 储物盒的标签 | `name` |
| 变量值 | 盒子里的东西 | `"五粮液"` |
| 变量类型 | 盒子的规格 | str 字符串 |

### Python 的变量特点

```python
# Python 是动态类型语言
name = "五粮液"    # 现在是字符串
name = 600519      # 可以随时变成整数
name = True        # 也可以变成布尔值
```

**对比 Java/TypeScript（静态类型）：**
```java
String name = "五粮液";  // 声明后不能改变类型
```

**对比 JavaScript（动态类型但需要 var/let）：**
```javascript
let name = "五粮液";  // 需要 let 声明
```

**Python 的简洁之处：** 直接赋值就是声明变量。

## 二、四种基本数据类型

### 1. 字符串 (str)

```python
# 三种写法都可以
name1 = "五粮液"
name2 = '五粮液'
name3 = """多行
字符串"""

# 常用操作
text = "贵州茅台 600519"
print(len(text))        # 长度: 11
print(text[0:4])        # 切片: "贵州茅台"
print(text.upper())     # 转大写
print(text.replace("贵州", "五粮液"))  # 替换
```

**在 FastAPI 中的应用：**
```python
@router.get("/stocks/{code}")
async def get_stock(code: str):  # code 是字符串类型
    return {"code": code}
```

### 2. 整数 (int)

```python
count = 100
negative = -50

# 运算
print(count + 10)   # 加: 110
print(count - 20)   # 减: 80
print(count * 2)    # 乘: 200
print(count / 3)    # 除: 33.33... (自动变浮点数)
print(count // 3)   # 整除: 33
print(count % 3)    # 取余: 1
print(count ** 2)   # 幂: 10000
```

### 3. 浮点数 (float)

```python
price = 150.5
rate = 0.025

# 精度问题（所有语言都有）
print(0.1 + 0.2)  # 0.30000000000000004

# 解决方案：用整数处理或 round()
result = 0.1 + 0.2
print(round(result, 2))  # 0.3
```

### 4. 布尔值 (bool)

```python
is_valid = True
is_empty = False

# 布尔运算
print(True and False)   # False
print(True or False)    # True
print(not True)         # False

# 常见用法：条件判断
if is_valid:
    print("数据有效")
```

## 三、类型转换

```python
# 常用转换
str(123)       # 123 → "123"
int("456")     # "456" → 456
float("7.5")   # "7.5" → 7.5
bool("")       # 空字符串 → False
bool("hello")  # 非空字符串 → True
bool(0)        # 0 → False
bool(1)        # 非零 → True
```

## 四、f-string 格式化（必须掌握！）

### 为什么用 f-string？

```python
name = "五粮液"
price = 150.5

# 方式1: 拼接（麻烦）
print("股票名称: " + name + ", 价格: " + str(price))

# 方式2: % 格式化（老式）
print("股票名称: %s, 价格: %.2f" % (name, price))

# 方式3: format()（还行）
print("股票名称: {}, 价格: {}".format(name, price))

# 方式4: f-string（现代、简洁）✅
print(f"股票名称: {name}, 价格: {price:.2f}")
```

### f-string 高级用法

```python
# 保留小数位
pi = 3.14159
print(f"π 保留两位: {pi:.2f}")  # 3.14

# 进制转换
num = 255
print(f"十六进制: {num:#x}")    # 0xff

# 字典访问
stock = {"code": "600519", "name": "贵州茅台"}
print(f"代码: {stock['code']}, 名称: {stock['name']}")

# 表达式
price = 100
print(f"上涨后: {price * 1.1}")  # 110.0
```

## 五、Python vs JavaScript 对比

| 特性 | Python | JavaScript |
|------|--------|------------|
| 变量声明 | 直接赋值 | 需要 `let`/`const` |
| 字符串 | 单引号或双引号 | 双引号或单引号 |
| 格式化 | f-string | 模板字符串 `${}` |
| 类型转换 | `int()`, `str()` | `parseInt()`, `String()` |

```python
# Python
name = "五粮液"
print(f"股票: {name}")

# JavaScript (对比理解)
let name = "五粮液";
console.log(`股票: ${name}`);
```

## 六、常见错误

### 1. 字符串引号不匹配
```python
# ❌ 错误
text = '五粮液"

# ✅ 正确
text = "五粮液"
text = '五粮液'
```

### 2. 类型错误
```python
# ❌ 错误：字符串和数字不能直接拼接
print("价格: " + 150.5)  # TypeError

# ✅ 正确：转换类型
print("价格: " + str(150.5))
```

## 练习题

1. 创建变量存储股票代码、名称、现价、涨跌，计算并打印涨跌幅
2. 将价格转换为字符串，拼接成 "600519 贵州茅台 1500.00元"
3. 用 f-string 格式化输出：保留2位小数、对齐显示

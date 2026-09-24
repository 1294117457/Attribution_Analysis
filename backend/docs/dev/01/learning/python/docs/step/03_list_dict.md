# Step 03: 列表和字典

## 学习目标
掌握 Python 最常用的两种容器类型：列表 (list) 和字典 (dict)

## 概念速览

```python
# 列表：有序的可变序列
fruits = ["苹果", "香蕉", "橙子"]
fruits[0]        # 访问
fruits.append("葡萄")  # 添加
fruits[1:3]      # 切片

# 字典：键值对
person = {"name": "张三", "age": 25}
person["name"]         # 访问
person["city"] = "北京"  # 添加
person.keys()         # 所有键
person.values()       # 所有值
```

## 任务

### 任务 1: 列表基础操作

创建 `demo_03_list.py`：

```python
# 1. 创建列表
prices = [150.5, 160.2, 148.0, 155.8]
print(f"价格列表: {prices}")

# 2. 访问元素（索引从0开始）
print(f"第一个价格: {prices[0]}")
print(f"最后一个价格: {prices[-1]}")

# 3. 切片
print(f"前两个: {prices[0:2]}")
print(f"最后两个: {prices[-2:]}")

# 4. 添加元素
prices.append(158.0)
print(f"添加后: {prices}")

# 5. 列表长度
print(f"共 {len(prices)} 个价格")
```

### 任务 2: 列表常用操作

```python
# 常用列表操作
numbers = [5, 2, 8, 1, 9]

# 排序
numbers.sort()
print(f"排序后: {numbers}")

# 反转
numbers.reverse()
print(f"反转后: {numbers}")

# 查找
print(f"最大值: {max(numbers)}")
print(f"最小值: {min(numbers)}")
print(f"求和: {sum(numbers)}")

# 判断元素是否存在
print(f"是否有5: {5 in numbers}")
print(f"是否有10: {10 in numbers}")
```

### 任务 3: 列表推导式（重要！）

```python
# 原始写法：生成1-10的平方
squares = []
for i in range(1, 11):
    squares.append(i ** 2)
print(f"平方列表: {squares}")

# 列表推导式：一行搞定
squares2 = [i ** 2 for i in range(1, 11)]
print(f"平方列表(推导式): {squares2}")

# 带条件的列表推导式：只取偶数的平方
even_squares = [i ** 2 for i in range(1, 11) if i % 2 == 0]
print(f"偶数平方: {even_squares}")

# 实战：筛选涨幅大于0的股票
changes = [2.5, -1.2, 0.8, -3.5, 1.0]
rising = [c for c in changes if c > 0]
print(f"上涨日: {rising}")
```

### 任务 4: 字典基础操作

```python
# 创建字典
stock = {
    "code": "600519",
    "name": "贵州茅台",
    "price": 1500.0,
    "change": 2.5,
    "volume": 100000
}

# 访问值
print(f"股票: {stock['name']}")
print(f"价格: {stock['price']}")

# 添加/修改
stock["turnover"] = 15000000000
stock["change"] = 3.0
print(f"更新后涨跌: {stock['change']}")

# 获取值的安全方式
print(f"行业: {stock.get('industry', '未知')}")  # 不存在返回默认值

# 遍历字典
print("\n遍历字典:")
for key in stock:
    print(f"  {key}: {stock[key]}")
```

### 任务 5: 字典推导式

```python
# 原始写法
prices = {"苹果": 5, "香蕉": 3, "橙子": 4}
discounted = {}
for fruit, price in prices.items():
    discounted[fruit] = price * 0.9
print(f"打折后: {discounted}")

# 字典推导式
discounted2 = {fruit: price * 0.9 for fruit, price in prices.items()}
print(f"打折后(推导式): {discounted2}")
```

## 运行验证

```bash
python demo_03_list.py
```

## 下一步
阅读 `../docs/analysis/03_list_dict.md` 深入理解

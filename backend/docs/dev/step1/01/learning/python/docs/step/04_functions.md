# Step 04: 函数定义

## 学习目标
理解函数的定义、参数、返回值，以及如何组织代码

## 概念速览

```python
# 基本函数
def 函数名(参数):
    """文档字符串"""
    函数体
    return 返回值

# 函数调用
结果 = 函数名(实参)
```

## 任务

### 任务 1: 基本函数

创建 `demo_04_functions.py`：

```python
# 1. 无参数函数
def say_hello():
    """打招呼"""
    print("你好！")

say_hello()

# 2. 有参数函数
def greet(name):
    """向指定名字打招呼"""
    print(f"你好，{name}！")

greet("张三")
greet("李四")

# 3. 有返回值的函数
def add(a, b):
    """返回两数之和"""
    return a + b

result = add(3, 5)
print(f"3 + 5 = {result}")
```

### 任务 2: 参数类型

```python
# 1. 默认参数
def greet(name, greeting="你好"):
    """带默认参数"""
    return f"{greeting}，{name}！"

print(greet("张三"))           # 使用默认值
print(greet("李四", "早上好"))  # 覆盖默认值

# 2. 关键字参数
def create_stock(code, name, price):
    return {"code": code, "name": name, "price": price}

# 位置参数
stock1 = create_stock("600519", "贵州茅台", 1500)

# 关键字参数（顺序可以颠倒）
stock2 = create_stock(price=150, name="五粮液", code="000858")

# 混合使用
stock3 = create_stock("600036", price=35, name="招商银行")

print(f"股票1: {stock1}")
print(f"股票2: {stock2}")
print(f"股票3: {stock3}")
```

### 任务 3: 函数返回值

```python
# 1. 单返回值
def get_change_type(change_pct):
    """判断涨跌类型"""
    if change_pct > 5:
        return "大涨"
    elif change_pct > 0:
        return "小涨"
    elif change_pct == 0:
        return "平"
    else:
        return "跌"

print(get_change_type(6))   # 大涨
print(get_change_type(2))    # 小涨

# 2. 多返回值（实际返回元组）
def get_stock_stats(prices):
    """返回最高价、最低价、均价"""
    return max(prices), min(prices), sum(prices) / len(prices)

highest, lowest, average = get_stock_stats([100, 150, 120, 180])
print(f"最高: {highest}, 最低: {lowest}, 均价: {average:.2f}")
```

### 任务 4: 实战函数

```python
# 实战：计算股票涨跌
def calculate_change(open_price, close_price):
    """计算涨跌额和涨跌幅"""
    change = close_price - open_price
    change_pct = (change / open_price) * 100
    return change, change_pct

def format_stock_info(code, name, open_price, close_price):
    """格式化股票信息"""
    change, change_pct = calculate_change(open_price, close_price)
    
    emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
    sign = "+" if change > 0 else ""
    
    return {
        "code": code,
        "name": name,
        "open": open_price,
        "close": close_price,
        "change": f"{sign}{change:.2f}",
        "change_pct": f"{sign}{change_pct:.2f}%",
        "emoji": emoji
    }

# 测试
stock = format_stock_info("600519", "贵州茅台", 1480, 1500)
print(f"{stock['emoji']} {stock['name']}({stock['code']})")
print(f"开盘: {stock['open']}, 收盘: {stock['close']}")
print(f"涨跌: {stock['change']} ({stock['change_pct']})")
```

## 运行验证

```bash
python demo_04_functions.py
```

## 下一步
阅读 `../docs/analysis/04_functions.md` 深入理解

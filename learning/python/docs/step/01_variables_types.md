# Step 01: 变量和数据类型

## 学习目标
理解 Python 中的基本数据类型：字符串、数字、布尔值

## 概念速览

```
Python 数据类型
├── 字符串 str  → "Hello" / 'Hello'
├── 整数   int  → 42, -5, 0
├── 浮点数 float → 3.14, -0.5
└── 布尔值 bool → True, False
```

## 任务

### 任务 1: 创建变量并打印

创建 `demo_01_basics.py`，输入以下代码并运行：

```python
# 1. 字符串
name = "五粮液"
print(f"股票名称: {name}")

# 2. 数字
price = 150.5
print(f"当前价格: {price}")

# 3. 整数
volume = 10000
print(f"成交量: {volume}")

# 4. 布尔值
is_anomaly = True
print(f"是否异常: {is_anomaly}")
```

### 任务 2: 尝试修改和运算

在同一个文件添加：

```python
# 5. 数值运算
new_price = price * 1.1  # 上涨10%
print(f"上涨10%后价格: {new_price}")

# 6. 类型转换
price_str = str(price)      # 数字转字符串
volume_float = float(volume)  # 整数转浮点数
print(f"转换后: {price_str}, {volume_float}")
```

### 任务 3: f-string 格式化（重要！）

```python
# f-string 是 Python 最常用的格式化方式
stock = {
    "code": "000858",
    "name": "五粮液",
    "price": 150.5,
    "change": 2.5
}

# 用 f-string 输出
print(f"{stock['name']}({stock['code']}): {stock['price']}元, 涨跌{stock['change']}%")
```

## 运行验证

```bash
python demo_01_basics.py
```

预期输出：
```
股票名称: 五粮液
当前价格: 150.5
成交量: 10000
是否异常: True
上涨10%后价格: 165.55
转换后: 150.5, 10000.0
五粮液(000858): 150.5元, 涨跌2.5%
```

## 下一步
阅读 `../docs/analysis/01_variables_types.md` 深入理解

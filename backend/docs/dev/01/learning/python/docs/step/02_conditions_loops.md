# Step 02: 条件判断和循环

## 学习目标
掌握 Python 的条件判断 (if/elif/else) 和循环 (for/while)

## 概念速览

```python
# 条件判断
if 条件:
    成立时执行
elif 另一个条件:
    另一个成立时执行
else:
    都不成立时执行

# for 循环
for 变量 in 序列:
    每次循环执行的代码

# while 循环
while 条件:
    条件成立时循环执行
```

## 任务

### 任务 1: 基本条件判断

创建 `demo_02_conditions.py`：

```python
# 根据涨跌判断市场状态
change_pct = 2.5

if change_pct > 5:
    print("🚀 大涨！涨幅超过5%")
elif change_pct > 0:
    print("📈 小幅上涨")
elif change_pct == 0:
    print("➖ 横盘")
elif change_pct > -5:
    print("📉 小幅下跌")
else:
    print("💥 大跌！跌幅超过5%")
```

### 任务 2: 多条件组合

```python
# and / or / not
price = 1500.0
volume = 100000
change_pct = 2.5

# 条件1: 价格适中 (100 < price < 2000)
# 条件2: 成交量放大 (> 50000)
# 条件3: 涨幅为正

if (100 < price < 2000) and (volume > 50000) and (change_pct > 0):
    print("✅ 符合条件的股票")
else:
    print("❌ 不符合条件")

# 或者用 not
if not (100 < price < 2000):
    print("价格不在合理范围")
```

### 任务 3: for 循环

```python
# 遍历列表
stocks = ["贵州茅台", "五粮液", "招商银行"]

for stock in stocks:
    print(f"股票: {stock}")

# 遍历数字序列
print("\n1-10 的数字:")
for i in range(1, 11):
    print(i, end=" ")
print()

# 遍历字典
stock_info = {
    "code": "600519",
    "name": "贵州茅台",
    "price": 1500.0,
    "change": 2.5
}

print("\n遍历字典:")
for key, value in stock_info.items():
    print(f"  {key}: {value}")
```

### 任务 4: while 循环

```python
# while 循环
count = 0
while count < 5:
    print(f"计数: {count}")
    count += 1

print("循环结束")

# break 和 continue
print("\n带 break 的循环:")
for i in range(10):
    if i == 5:
        break  # 遇到5就停止
    print(i, end=" ")
print()

print("\n带 continue 的循环:")
for i in range(5):
    if i == 2:
        continue  # 跳过2
    print(i, end=" ")
print()
```

## 运行验证

```bash
python demo_02_conditions.py
```

## 知识点预告

| 概念 | 含义 |
|------|------|
| `range(1, 11)` | 生成 1-10 的数字序列 |
| `range(5)` | 生成 0-4 的数字序列 |
| `dict.items()` | 返回键值对元组列表 |
| `break` | 跳出整个循环 |
| `continue` | 跳过本次循环 |

## 下一步
阅读 `../docs/analysis/02_conditions_loops.md` 深入理解

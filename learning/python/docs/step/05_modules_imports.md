# Step 05: 模块和导入

## 学习目标
理解模块的概念，学会使用 import 导入模块

## 概念速览

```python
# 导入整个模块
import os
os.getcwd()

# 从模块导入特定内容
from datetime import datetime
datetime.now()

# 给模块起别名
import pandas as pd

# 导入时起别名
from utils import fetch_data as fetch
```

## 任务

### 任务 1: 使用标准库模块

创建 `demo_05_modules.py`：

```python
# 1. 使用 datetime 模块
from datetime import datetime, timedelta

now = datetime.now()
print(f"当前时间: {now}")
print(f"格式化: {now.strftime('%Y-%m-%d %H:%M:%S')}")

# 计算时间差
yesterday = now - timedelta(days=1)
print(f"昨天: {yesterday.strftime('%Y-%m-%d')}")

# 2. 使用 json 模块
import json

data = {
    "code": "600519",
    "name": "贵州茅台",
    "price": 1500.0,
    "changes": [2.5, -1.2, 3.0]
}

# 字典转 JSON 字符串
json_str = json.dumps(data, ensure_ascii=False, indent=2)
print(f"JSON: {json_str}")

# JSON 字符串转字典
parsed = json.loads(json_str)
print(f"解析后: {parsed['name']}")

# 3. 使用 os 模块
import os

print(f"当前目录: {os.getcwd()}")
print(f"列出文件: {os.listdir('.')}")

# 4. 使用 random 模块
import random

# 随机整数
print(f"随机整数: {random.randint(1, 100)}")

# 随机选择
stocks = ["贵州茅台", "五粮液", "招商银行"]
print(f"随机选择: {random.choice(stocks)}")

# 随机打乱
random.shuffle(stocks)
print(f"打乱后: {stocks}")
```

### 任务 2: 创建自己的模块

首先创建一个工具模块 `utils.py`：

```python
# utils.py - 工具函数模块
"""工具函数集合"""

def calculate_change(open_price, close_price):
    """计算涨跌额和涨跌幅"""
    change = close_price - open_price
    change_pct = (change / open_price) * 100
    return change, change_pct

def format_stock(code, name, price, change):
    """格式化股票信息"""
    sign = "+" if change > 0 else ""
    emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
    return f"{emoji} {name}({code}): {price} ({sign}{change}%)"

def is_valid_code(code):
    """验证股票代码"""
    if not code:
        return False
    if not code.isdigit():
        return False
    if len(code) != 6:
        return False
    return True

# 模块级别变量
VERSION = "1.0.0"
```

然后在 `demo_05_modules.py` 中使用：

```python
# 5. 导入自定义模块
import utils

# 调用模块中的函数
change, pct = utils.calculate_change(1480, 1500)
print(f"涨跌: {change:.2f}, 涨跌幅: {pct:.2f}%")

print(utils.format_stock("600519", "贵州茅台", 1500, 2.5))
print(utils.is_valid_code("600519"))  # True
print(utils.is_valid_code("60051"))   # False
print(utils.VERSION)
```

### 任务 3: 使用 from...import 语法

```python
# 只导入需要的函数（推荐）
from utils import calculate_change, format_stock

# 直接使用，不需要加模块名前缀
change, pct = calculate_change(1480, 1500)
print(format_stock("600519", "贵州茅台", 1500, 2.5))

# 导入时起别名
from utils import is_valid_code as check_code
print(check_code("600519"))

# 导入所有（不推荐，容易命名冲突）
# from utils import *
```

### 任务 4: 使用 pathlib 处理文件路径

```python
from pathlib import Path

# Path 对象操作
base_path = Path(".")

# 路径拼接
data_dir = base_path / "data"
print(f"数据目录: {data_dir}")

# 创建目录
data_dir.mkdir(exist_ok=True)

# 检查文件是否存在
config_file = base_path / "config.json"
print(f"配置文件存在: {config_file.exists()}")

# 列出文件
for file in base_path.iterdir():
    if file.is_file():
        print(f"文件: {file.name}")
```

## 运行验证

```bash
python demo_05_modules.py
```

## 下一步
阅读 `../docs/analysis/05_modules_imports.md` 深入理解

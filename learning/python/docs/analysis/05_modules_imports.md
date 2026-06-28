# 模块和导入详解

## 一、什么是模块？

### 模块的概念

模块就是一个 **.py 文件**。把代码分到不同的文件中，方便管理和复用。

```
项目结构
├── main.py           # 主程序
├── utils.py          # 工具模块
├── models.py         # 数据模型模块
└── config.py         # 配置模块
```

### 模块 vs 包

| 概念 | 定义 | 文件 |
|------|------|------|
| 模块 (Module) | 一个 .py 文件 | `utils.py` |
| 包 (Package) | 包含 `__init__.py` 的文件夹 | `utils/__init__.py` |

```
模块示例
├── config.py              # 模块
└── utils/
    ├── __init__.py        # 包
    ├── file_utils.py      # 子模块
    └── string_utils.py    # 子模块
```

## 二、导入语法

### 1. import 语句

```python
# 导入整个模块
import os
import json
import random

# 使用：模块名.函数名
os.getcwd()
json.dumps({})
random.choice([1, 2, 3])

# 给模块起别名
import pandas as pd
import numpy as np
```

### 2. from...import 语句

```python
# 导入特定内容
from datetime import datetime, timedelta
from json import dumps, loads
from random import choice, randint

# 使用：直接调用，不需要模块前缀
datetime.now()
choice([1, 2, 3])
```

### 3. import...as 语句

```python
# 给导入的内容起别名
from datetime import datetime as dt
from json import dumps as json_encode, loads as json_decode

dt.now()
```

### 导入方式对比

```python
# 方式1：import 模块
import json
json.dumps(data)

# 方式2：from 模块 import 内容
from json import dumps
dumps(data)

# 方式3：from 模块 import *
from json import *
# ⚠️ 不推荐：可能和本地变量冲突

# 方式4：起别名
import json as js
js.dumps(data)
```

## 三、Python 的模块搜索路径

当你 `import xxx` 时，Python 按以下顺序查找：

```python
import sys
print(sys.path)
# 输出类似：
# [
#     '',                    # 当前目录
#     '/usr/lib/python3.11', # Python 安装目录
#     '/usr/local/lib',       # 第三方库
#     ...
# ]
```

### 常用技巧

```python
import sys
import os

# 添加自定义路径
sys.path.insert(0, '/path/to/your/module')

# 或者用相对路径（推荐）
from . import utils  # 导入同目录的 utils
from .. import config  # 导入上级目录的 config
```

## 四、__init__.py 文件

### 作用

1. 标记文件夹为 Python 包
2. 控制模块的导出内容
3. 初始化包

```python
# utils/__init__.py

# 方式1：导出所有子模块
from .file_utils import *
from .string_utils import *

# 方式2：选择性导出（推荐）
from .file_utils import read_file, write_file
from .string_utils import clean_text, truncate

# 方式3：定义 __all__
__all__ = ['read_file', 'write_file', 'clean_text']
```

### 使用包

```python
# 从包导入
from utils import read_file, write_file

# 或者
from utils.utils import read_file  # 从 utils/utils.py 导入
```

## 五、常用标准库

### 1. os - 操作系统

```python
import os

os.getcwd()              # 当前目录
os.listdir('.')          # 列出文件
os.mkdir('data')         # 创建目录
os.makedirs('a/b/c')     # 递归创建
os.remove('file.txt')     # 删除文件
os.path.join('a', 'b')   # 路径拼接
os.path.exists('x')      # 检查存在
os.path.isfile('x')      # 是否文件
os.path.isdir('x')       # 是否目录
```

### 2. json - JSON 处理

```python
import json

# Python 对象 → JSON 字符串
json.dumps({'a': 1})                    # '{"a": 1}'
json.dumps({'a': 1}, indent=2)           # 格式化
json.dumps({'a': 1}, ensure_ascii=False) # 中文不转义

# JSON 字符串 → Python 对象
json.loads('{"a": 1}')                   # {'a': 1}

# 文件操作
with open('data.json', 'w') as f:
    json.dump(data, f, indent=2)

with open('data.json', 'r') as f:
    data = json.load(f)
```

### 3. datetime - 日期时间

```python
from datetime import datetime, timedelta, date

# 当前时间
now = datetime.now()
today = date.today()

# 格式化
now.strftime('%Y-%m-%d')      # "2024-01-15"
now.strftime('%Y-%m-%d %H:%M:%S')  # "2024-01-15 14:30:00"

# 解析
datetime.strptime('2024-01-15', '%Y-%m-%d')

# 时间计算
later = now + timedelta(days=7)
earlier = now - timedelta(hours=2)
```

### 4. pathlib - 路径操作（现代方式）

```python
from pathlib import Path

# 创建路径
p = Path('data') / 'stocks' / '600519.csv'

# 操作
p.exists()          # 是否存在
p.is_file()          # 是否文件
p.is_dir()           # 是否目录
p.parent             # 父目录
p.stem               # 文件名（不含扩展名）
p.suffix             # 扩展名

# 创建目录
p.mkdir(parents=True, exist_ok=True)

# 读写文件
p.write_text('hello')
p.read_text()
```

### 5. random - 随机数

```python
import random

random.randint(1, 10)       # 随机整数 [1, 10]
random.random()             # [0, 1) 浮点数
random.choice([1, 2, 3])    # 随机选择
random.sample([1,2,3,4,5], 3)  # 随机抽样
random.shuffle([1,2,3,4,5])    # 原地打乱
```

## 六、实战应用

### 1. 配置文件模块

```python
# config.py
import os

class Config:
    """应用配置"""
    
    # 数据库
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'stocks')
    
    # API
    API_KEY = os.getenv('API_KEY', '')
    API_TIMEOUT = 30
    
    # 数据目录
    DATA_DIR = Path('data')
    CACHE_DIR = DATA_DIR / 'cache'

# 使用
from config import Config
print(Config.DB_HOST)
```

### 2. 数据处理模块

```python
# data_processor.py
from pathlib import Path
import json

class DataProcessor:
    """数据处理器"""
    
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def save(self, filename, data):
        """保存数据到 JSON 文件"""
        filepath = self.data_dir / f"{filename}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath
    
    def load(self, filename):
        """从 JSON 文件加载数据"""
        filepath = self.data_dir / f"{filename}.json"
        if not filepath.exists():
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

# 使用
from data_processor import DataProcessor
processor = DataProcessor('my_data')
processor.save('test', {'hello': 'world'})
data = processor.load('test')
```

## 七、__name__ == '__main__'

```python
# utils.py

def helper():
    return "helper"

# 测试代码：只在直接运行此文件时执行
if __name__ == '__main__':
    print("测试 utils 模块")
    print(helper())
    print("测试完成")
```

```bash
# 直接运行
python utils.py  # 会执行测试代码

# 作为模块导入
python main.py   # 不会执行 utils.py 中的测试代码
```

**作用**：区分"直接运行"和"被导入"两种场景。

## 常见错误

### 1. 循环导入
```python
# a.py
from b import func_b  # b 还没加载完

# b.py
from a import func_a  # a 还没加载完
# ❌ 死循环

# 解决：重构代码结构，或延迟导入
```

### 2. 找不到模块
```python
# ❌ 错误
import mymodule  # 不在 sys.path 中

# ✅ 正确：确认模块位置
import sys
print(sys.path)  # 检查路径
# 或确保模块在正确位置
```

## 练习题

1. 创建 `stock_utils.py` 模块，包含计算涨跌、判断是否涨停等功能
2. 用 `pathlib` 重写一个文件夹的创建、文件读写操作
3. 创建一个配置模块，从环境变量读取配置
4. 用 `json` 模块实现一个简单的数据存储和加载

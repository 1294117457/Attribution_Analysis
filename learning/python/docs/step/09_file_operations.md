# Step 09: 文件操作

## 学习目标
掌握 Python 文件读写操作：文本文件、JSON 文件

## 概念速览

```python
# 读取文件
with open("file.txt", "r") as f:
    content = f.read()

# 写入文件
with open("file.txt", "w") as f:
    f.write("hello")

# JSON 文件
import json
with open("data.json", "r") as f:
    data = json.load(f)
```

## 任务

### 任务 1: 基本文件读写

创建 `demo_09_files.py`：

```python
# 1. 写入文本文件
print("=== 写入文件 ===")
with open("test_write.txt", "w", encoding="utf-8") as f:
    f.write("第一行内容\n")
    f.write("第二行内容\n")
    f.write("第三行内容\n")
print("写入完成！")

# 2. 读取文本文件
print("\n=== 读取文件 ===")
with open("test_write.txt", "r", encoding="utf-8") as f:
    # 方式1: 读取全部
    content = f.read()
    print("全部内容:")
    print(content)

# 3. 逐行读取
print("\n=== 逐行读取 ===")
with open("test_write.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(f"行: {line.rstrip()}")

# 4. 读取为行列表
print("\n=== 读取为列表 ===")
with open("test_write.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
    print(f"共 {len(lines)} 行")
    for i, line in enumerate(lines):
        print(f"  {i+1}: {line.rstrip()}")
```

### 任务 2: JSON 文件操作

```python
import json

# 1. 写入 JSON 文件
print("=== 写入 JSON ===")
stock_data = {
    "code": "600519",
    "name": "贵州茅台",
    "price": 1500.0,
    "changes": [2.5, -1.2, 3.0, 0.5, -0.8],
    "is_valid": True,
    "tags": ["白酒", "龙头", "蓝筹"]
}

with open("stock.json", "w", encoding="utf-8") as f:
    json.dump(stock_data, f, ensure_ascii=False, indent=2)
print("JSON 写入完成！")

# 2. 读取 JSON 文件
print("\n=== 读取 JSON ===")
with open("stock.json", "r", encoding="utf-8") as f:
    loaded_data = json.load(f)
    
print(f"股票: {loaded_data['name']}")
print(f"价格: {loaded_data['price']}")
print(f"近期涨跌: {loaded_data['changes']}")

# 3. JSON 字符串互转
print("\n=== JSON 字符串互转 ===")
json_str = json.dumps(stock_data, ensure_ascii=False)
print(f"转字符串: {json_str[:100]}...")

parsed = json.loads(json_str)
print(f"解析回来: {parsed['name']}")
```

### 任务 3: CSV 文件操作

```python
import csv

# 写入 CSV
print("=== 写入 CSV ===")
stocks = [
    ["代码", "名称", "价格", "涨跌"],
    ["600519", "贵州茅台", "1500", "2.5%"],
    ["000858", "五粮液", "150", "-1.2%"],
    ["600036", "招商银行", "35", "0.8%"],
]

with open("stocks.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(stocks)
print("CSV 写入完成！")

# 读取 CSV
print("\n=== 读取 CSV ===")
with open("stocks.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)
```

### 任务 4: 使用 pathlib

```python
from pathlib import Path

# 1. 路径操作
print("=== 路径操作 ===")
base = Path(".")
print(f"当前目录: {base.resolve()}")

# 2. 创建目录
data_dir = base / "data"
data_dir.mkdir(exist_ok=True)
print(f"创建目录: {data_dir}")

# 3. 读写文件
test_file = data_dir / "test.txt"
test_file.write_text("测试内容")
content = test_file.read_text()
print(f"读写测试: {content}")

# 4. 检查文件
print(f"\n文件存在: {test_file.exists()}")
print(f"是文件: {test_file.is_file()}")
print(f"是目录: {test_file.is_dir()}")
print(f"文件大小: {test_file.stat().st_size} 字节")

# 5. 列出目录内容
for item in base.iterdir():
    if item.is_file():
        print(f"文件: {item.name}")
```

## 运行验证

```bash
python demo_09_files.py
cat stocks.csv
cat stock.json
```

## 知识点回顾

| 方法 | 用途 |
|------|------|
| `open()` | 打开文件 |
| `with open()` | 自动关闭文件 |
| `f.read()` | 读取全部 |
| `f.readlines()` | 读取为行列表 |
| `f.write()` | 写入 |
| `json.dump()` | 写入 JSON |
| `json.load()` | 读取 JSON |
| `Path()` | 路径对象 |

## 下一步
阅读 `../docs/analysis/09_file_operations.md` 深入理解

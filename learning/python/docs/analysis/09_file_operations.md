# 文件操作详解

## 一、文件操作基础

### 为什么需要文件操作？

```python
# 程序运行结束后，数据消失
stocks = [{"code": "600519", "name": "贵州茅台"}]
# 程序结束，数据没了

# 文件可以持久化保存数据
save_to_file(stocks)  # 保存到文件
# 程序结束，数据还在
loaded = load_from_file()  # 下次运行时读取
```

### 文件操作模式

| 模式 | 说明 | 如果文件存在 | 如果文件不存在 |
|------|------|-------------|--------------|
| `r` | 读取 | 读取 | 报错 |
| `w` | 写入 | **覆盖** | 创建 |
| `a` | 追加 | 末尾添加 | 创建 |
| `x` | 创建写入 | 报错 | 创建 |
| `r+` | 读写 | 读写 | 报错 |
| `w+` | 读写 | **覆盖** | 创建 |

### 编码问题

```python
# 始终指定编码，避免乱码
with open("file.txt", "r", encoding="utf-8") as f:
    pass

# encoding 常用值
# - utf-8: 通用编码（推荐）
# - gbk: 中文 Windows 常用
# - latin-1: 兼容性编码
```

## 二、文本文件操作

### 读取文件

```python
# 方式1: 读取全部
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()  # 字符串

# 方式2: 读取一行
with open("file.txt", "r", encoding="utf-8") as f:
    first_line = f.readline()  # 第一行

# 方式3: 读取所有行
with open("file.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()  # 列表

# 方式4: 遍历文件对象
with open("file.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.rstrip())  # rstrip() 去掉换行符
```

### 写入文件

```python
# 写入（覆盖）
with open("file.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n")
    f.write("第二行\n")

# 追加（末尾添加）
with open("file.txt", "a", encoding="utf-8") as f:
    f.write("追加的内容\n")
```

### 常用文件方法

```python
f.read()          # 读取全部
f.read(n)         # 读取 n 个字符
f.readline()      # 读取一行
f.readlines()     # 读取所有行，返回列表
f.write(s)        # 写入字符串
f.writelines(lst) # 写入字符串列表
f.seek(n)         # 移动指针到 n
f.tell()          # 返回当前位置
f.close()         # 关闭文件
```

## 三、with 语句

with 语句自动管理资源：

```python
# ❌ 不用 with：需要手动关闭
f = open("file.txt", "r")
try:
    content = f.read()
finally:
    f.close()

# ✅ 用 with：自动关闭
with open("file.txt", "r") as f:
    content = f.read()
# 文件已自动关闭
```

## 四、JSON 文件操作

### JSON 格式

```json
{
    "name": "贵州茅台",
    "price": 1500,
    "changes": [2.5, -1.2, 3.0],
    "is_valid": true
}
```

### 写入 JSON

```python
import json

data = {
    "code": "600519",
    "name": "贵州茅台",
    "price": 1500.0,
    "changes": [2.5, -1.2, 3.0]
}

# 写入文件
with open("stock.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 转为字符串
json_str = json.dumps(data, ensure_ascii=False, indent=2)
```

### 读取 JSON

```python
# 从文件读取
with open("stock.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 从字符串解析
json_str = '{"name": "茅台"}'
data = json.loads(json_str)
```

### json.dump/dumps 参数

```python
json.dump(obj, file, ensure_ascii=False, indent=2)
json.dumps(obj, ensure_ascii=False, indent=2)

# ensure_ascii=False: 中文不转义 (\u8fd0)
# indent=2: 格式化输出
```

## 五、CSV 文件操作

### 读取 CSV

```python
import csv

# 读取为列表
with open("stocks.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)

# 读取为字典
with open("stocks.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row["代码"], row["名称"])
```

### 写入 CSV

```python
# 写入列表
with open("stocks.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["代码", "名称", "价格"])  # 标题行
    writer.writerow(["600519", "贵州茅台", "1500"])  # 数据行

# 写入字典
with open("stocks.csv", "w", encoding="utf-8", newline="") as f:
    fieldnames = ["代码", "名称", "价格"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow({"代码": "600519", "名称": "贵州茅台", "价格": "1500"})
```

### 为什么需要 newline=""？

```python
# Windows 上不加 newline="" 可能导致空行
with open("file.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["A", "B"])
```

## 六、pathlib 模块

pathlib 是现代的路径操作方式：

```python
from pathlib import Path

# 创建路径
p = Path("data") / "stocks" / "600519.csv"
print(p)  # data/stocks/600519.csv

# 路径属性
p.name        # "600519.csv" (文件名)
p.stem        # "600519" (不含扩展名)
p.suffix      # ".csv" (扩展名)
p.parent      # Path("data/stocks") (父目录)

# 判断
p.exists()    # 是否存在
p.is_file()  # 是否是文件
p.is_dir()   # 是否是目录

# 创建目录
Path("data").mkdir(parents=True, exist_ok=True)

# 读写文件
p.write_text("hello")
p.read_text()
```

### pathlib vs os.path

| pathlib | os.path |
|---------|---------|
| `Path("a/b/c")` | `os.path.join("a", "b", "c")` |
| `p.exists()` | `os.path.exists(p)` |
| `p.is_file()` | `os.path.isfile(p)` |
| `p.parent` | `os.path.dirname(p)` |
| `p.name` | `os.path.basename(p)` |
| `p.mkdir()` | `os.makedirs()` |

## 七、实战应用

### 1. 保存股票数据

```python
import json
from pathlib import Path
from datetime import datetime

def save_stock_data(code, data):
    """保存股票数据到 JSON 文件"""
    data_dir = Path("data/stocks")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = data_dir / f"{code}.json"
    
    # 读取现有数据（如果有）
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {"code": code, "records": []}
    
    # 添加新记录
    existing["records"].append({
        "timestamp": datetime.now().isoformat(),
        "data": data
    })
    
    # 保存
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def load_stock_data(code):
    """加载股票数据"""
    filepath = Path(f"data/stocks/{code}.json")
    if not filepath.exists():
        return None
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
```

### 2. 批量处理文件

```python
from pathlib import Path

def process_all_stocks():
    """处理所有股票数据文件"""
    data_dir = Path("data/stocks")
    
    if not data_dir.exists():
        print("数据目录不存在")
        return
    
    # 遍历所有 JSON 文件
    for filepath in data_dir.glob("*.json"):
        print(f"处理: {filepath.name}")
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 处理数据...
        process_data(data)
```

## 八、Python vs JavaScript 对比

| Python | JavaScript (Node.js) | 说明 |
|--------|---------------------|------|
| `open("f", "r")` | `fs.readFileSync()` | 读取文件 |
| `with open() as f:` | `fs.createReadStream()` | 文件流 |
| `json.dump()` | `JSON.stringify()` | 序列化 |
| `json.load()` | `JSON.parse()` | 反序列化 |
| `pathlib.Path` | `path` / `fs.path` | 路径操作 |

## 常见错误

### 1. 文件未找到
```python
# ❌ 错误
with open("不存在.txt") as f:
    pass

# ✅ 正确：先检查
from pathlib import Path
if Path("不存在.txt").exists():
    with open("不存在.txt") as f:
        pass
```

### 2. 忘记关闭文件
```python
# ❌ 错误
f = open("file.txt", "w")
f.write("hello")
# 如果这里出错，文件没关闭

# ✅ 正确：用 with
with open("file.txt", "w") as f:
    f.write("hello")
# 自动关闭
```

### 3. 编码问题
```python
# ❌ 可能乱码
with open("中文文件.txt", "w") as f:
    f.write("中文内容")

# ✅ 正确：指定编码
with open("中文文件.txt", "w", encoding="utf-8") as f:
    f.write("中文内容")
```

## 练习题

1. 写一个程序，读取一个文本文件，统计行数、单词数、字符数
2. 实现一个简单的日志记录器，写入日志文件
3. 用 JSON 保存和加载股票数据
4. 读取 CSV 文件，计算每只股票的平均价格
5. 用 pathlib 实现文件的增删改查操作

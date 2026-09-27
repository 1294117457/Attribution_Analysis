# Step 08: 异常处理

## 学习目标
掌握 Python 的异常处理机制：try/except/finally

## 概念速览

```python
try:
    # 可能出错的代码
    result = risky_operation()
except 错误类型 as e:
    # 处理错误
    print(f"出错了: {e}")
else:
    # 没有出错时执行
    print("成功！")
finally:
    # 不管成功失败都执行
    cleanup()
```

## 任务

### 任务 1: 基本异常处理

创建 `demo_08_exceptions.py`：

```python
# 1. 除零错误
print("=== 除零错误 ===")
try:
    result = 10 / 0
    print(f"结果: {result}")
except ZeroDivisionError as e:
    print(f"捕获错误: {e}")
    print("除数不能为0！")

# 2. 索引错误
print("\n=== 索引错误 ===")
try:
    fruits = ["苹果", "香蕉", "橙子"]
    print(fruits[10])  # 越界
except IndexError as e:
    print(f"捕获错误: {e}")
    print(f"列表只有 {len(fruits)} 个元素")

# 3. 键错误
print("\n=== 键错误 ===")
try:
    stock = {"code": "600519", "name": "贵州茅台"}
    print(stock["price"])  # 键不存在
except KeyError as e:
    print(f"捕获错误: {e}")
    print("键不存在！")

print("\n程序继续执行...")
```

### 任务 2: 多异常处理

```python
# 多异常类型
print("=== 多异常处理 ===")
def parse_stock_code(code):
    """解析股票代码"""
    if not code:
        raise ValueError("股票代码不能为空")
    if not code.isdigit():
        raise TypeError("股票代码必须是数字")
    if len(code) != 6:
        raise ValueError("股票代码必须是6位")
    return code

test_codes = ["600519", "", "abc", "60051", "600519"]

for code in test_codes:
    try:
        result = parse_stock_code(code)
        print(f"✓ {code} -> 有效")
    except ValueError as e:
        print(f"✗ {code} -> 值错误: {e}")
    except TypeError as e:
        print(f"✗ {code} -> 类型错误: {e}")
```

### 任务 3: else 和 finally

```python
# else: 没有异常时执行
# finally: 无论是否有异常都执行
print("\n=== else 和 finally ===")

def read_stock_price(filename):
    """读取股票价格"""
    try:
        with open(filename, 'r') as f:
            price = float(f.read().strip())
            return price
    except FileNotFoundError:
        print(f"文件 {filename} 不存在")
        return None
    except ValueError:
        print(f"文件内容不是有效数字")
        return None
    else:
        print("读取成功，没有异常")
    finally:
        print("清理资源（如果需要）")

# 测试
read_stock_price("test.txt")  # 文件不存在
read_stock_price("demo_01_basics.py")  # 不是数字
```

### 任务 4: 主动抛出异常

```python
# raise 语句
print("\n=== 主动抛出异常 ===")

def validate_stock(code, name, price):
    """验证股票数据"""
    errors = []
    
    if not code:
        errors.append("股票代码不能为空")
    elif len(code) != 6:
        errors.append("股票代码必须是6位")
    
    if not name:
        errors.append("股票名称不能为空")
    
    if price <= 0:
        errors.append("价格必须大于0")
    
    # 如果有错误，抛出异常
    if errors:
        raise ValueError(f"验证失败: {'; '.join(errors)}")
    
    return {"code": code, "name": name, "price": price}

# 测试
try:
    stock = validate_stock("", "贵州茅台", 1500)
except ValueError as e:
    print(f"验证失败: {e}")

try:
    stock = validate_stock("600519", "贵州茅台", -100)
except ValueError as e:
    print(f"验证失败: {e}")

try:
    stock = validate_stock("600519", "贵州茅台", 1500)
    print(f"验证通过: {stock}")
except ValueError as e:
    print(f"验证失败: {e}")
```

## 运行验证

```bash
python demo_08_exceptions.py
```

## 下一步
阅读 `../docs/analysis/08_exception_handling.md` 深入理解

# 异常处理详解

## 一、为什么需要异常处理？

### 没有异常处理的代码

```python
# ❌ 问题：出错时程序直接崩溃
price = float(input("输入价格: "))
print(f"价格是 {price}")

# 用户输入 "abc" → 程序崩溃
# Traceback (most recent call last):
#   File "demo.py", line 1, in <module>
#     price = float("abc")
# ValueError: could not convert string to float: 'abc'
```

### 使用异常处理

```python
# ✅ 好处：程序不会崩溃，可以优雅处理错误
try:
    price = float(input("输入价格: "))
    print(f"价格是 {price}")
except ValueError:
    print("请输入有效的数字")
```

## 二、异常处理语法

### 基本结构

```python
try:
    # 可能出错的代码
    risky_code()
except 错误类型:
    # 处理错误
    handle_error()
```

### 完整结构

```python
try:
    # 尝试执行的代码
    result = divide(10, 0)
except ZeroDivisionError:
    # 处理特定错误
    print("不能除以0")
except Exception as e:
    # 捕获所有其他错误
    print(f"发生错误: {e}")
else:
    # try 块没有异常时执行
    print("执行成功！")
finally:
    # 无论是否有异常都执行
    cleanup()
```

### 执行流程

```
try:
    代码执行...
except:        ← 如果出错，跳到这里
    处理错误
else:          ← 如果没出错
    成功处理
finally:       ← 始终执行
    清理
```

## 三、常见异常类型

| 异常类型 | 说明 | 示例 |
|----------|------|------|
| `ZeroDivisionError` | 除数为零 | `10 / 0` |
| `ValueError` | 值不合法 | `int("abc")` |
| `TypeError` | 类型错误 | `"1" + 1` |
| `IndexError` | 索引越界 | `list[100]` |
| `KeyError` | 键不存在 | `dict["no_key"]` |
| `FileNotFoundError` | 文件不存在 | `open("不存在.txt")` |
| `AttributeError` | 属性不存在 | `obj.no_attr` |
| `Exception` | 所有异常的基类 | 通用捕获 |

### 异常继承关系

```
Exception (基类)
├── ValueError
│   └── ZeroDivisionError
├── TypeError
├── LookupError
│   ├── IndexError
│   └── KeyError
└── ...
```

## 四、捕获多个异常

### 方式1：多个 except

```python
try:
    result = parse_data(user_input)
except ValueError:
    print("数据格式错误")
except KeyError:
    print("缺少必要字段")
except Exception as e:
    print(f"未知错误: {e}")
```

### 方式2：元组形式

```python
try:
    result = parse_data(user_input)
except (ValueError, KeyError, TypeError) as e:
    print(f"数据错误: {e}")
```

### 方式3：捕获所有异常

```python
try:
    risky_operation()
except Exception as e:
    # 记录日志
    print(f"错误: {e}")
    # 重新抛出或处理
    raise  # 重新抛出
```

## 五、主动抛出异常

### raise 语句

```python
# 抛出异常
raise ValueError("错误信息")

# 抛出带原因
raise ValueError("错误信息") from cause

# 示例
def validate_age(age):
    if age < 0:
        raise ValueError("年龄不能为负")
    if age > 150:
        raise ValueError("年龄超出合理范围")
    return age
```

### 自定义异常

```python
# 定义自定义异常
class StockError(Exception):
    """股票相关错误基类"""
    pass

class InvalidCodeError(StockError):
    """无效的股票代码"""
    pass

class PriceOutOfRangeError(StockError):
    """价格超出范围"""
    pass

# 使用自定义异常
def validate_stock(code, price):
    if not code or len(code) != 6:
        raise InvalidCodeError(f"无效的股票代码: {code}")
    if price < 0 or price > 100000:
        raise PriceOutOfRangeError(f"价格超出合理范围: {price}")
    return True
```

## 六、异常处理的最佳实践

### 1. 不要过度捕获

```python
# ❌ 不好：捕获所有异常
try:
    do_something()
except:
    pass

# ✅ 好：只捕获可能发生的异常
try:
    do_something()
except ValueError:
    handle_value_error()
```

### 2. 具体异常优先

```python
# ❌ 不好：先捕获通用异常
try:
    parse()
except Exception:
    handle()

# ✅ 好：先捕获具体异常
try:
    parse()
except ValueError:
    handle_value_error()
except Exception:
    handle_other()
```

### 3. 记录异常信息

```python
import logging

try:
    risky_operation()
except Exception as e:
    logging.error(f"操作失败: {e}", exc_info=True)
    # exc_info=True 会记录完整的堆栈信息
```

### 4. 清理资源

```python
# ✅ 使用 finally 确保清理
file = None
try:
    file = open("data.txt")
    data = file.read()
finally:
    if file:
        file.close()

# ✅ 更简洁：with 语句（推荐）
with open("data.txt") as file:
    data = file.read()
# 自动关闭文件
```

## 七、with 语句

with 语句自动管理资源，确保正确关闭：

```python
# 文件操作
with open("data.txt", "w") as f:
    f.write("hello")
# 自动关闭

# 数据库连接
with get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM stocks")
        results = cursor.fetchall()
# 自动提交/回滚/关闭

# 锁
with threading.Lock():
    shared_resource += 1
# 自动释放锁
```

## 八、Python vs JavaScript 对比

| Python | JavaScript | 说明 |
|--------|------------|------|
| `try/except` | `try/catch` | 捕获异常 |
| `raise` | `throw` | 抛出异常 |
| `except Error as e:` | `catch (e) { }` | 获取异常 |
| `else` | 无 | try 成功时执行 |
| `finally` | `finally` | 始终执行 |

```python
# Python
try:
    result = divide(10, 2)
except ZeroDivisionError:
    print("不能除以0")
else:
    print("计算成功")
finally:
    cleanup()
```

```javascript
// JavaScript
try {
    const result = divide(10, 2);
} catch (e) {
    console.log("错误: " + e.message);
} finally {
    cleanup();
}
```

## 九、实战应用

### API 请求异常处理

```python
import requests

def fetch_stock_data(code):
    """获取股票数据"""
    try:
        response = requests.get(f"https://api.example.com/stock/{code}", timeout=5)
        response.raise_for_status()  # HTTP 错误也抛出异常
        return response.json()
    except requests.Timeout:
        print(f"请求超时: {code}")
        return None
    except requests.HTTPError as e:
        print(f"HTTP错误: {e}")
        return None
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError:
        print(f"JSON解析失败")
        return None
```

### 数据验证异常处理

```python
def parse_stock_data(raw_data):
    """解析股票数据"""
    try:
        if not raw_data:
            raise ValueError("数据为空")
        
        data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
        
        return {
            "code": data["code"],
            "name": data["name"],
            "price": float(data["price"])
        }
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON格式错误: {e}")
    except KeyError as e:
        raise ValueError(f"缺少字段: {e}")
    except (TypeError, ValueError) as e:
        raise ValueError(f"数据类型错误: {e}")
```

## 常见错误

### 1. 吞掉所有异常
```python
# ❌ 不好
try:
    do_something()
except:
    pass  # 静默忽略

# ✅ 好
try:
    do_something()
except SpecificError:
    handle_error()
```

### 2. 在 except 中使用未定义的变量
```python
# ❌ 错误
try:
    result = int(user_input)
except ValueError:
    print(f"无效输入: {undefined_var}")  # 可能会出错

# ✅ 正确
except ValueError as e:
    print(f"无效输入: {e}")  # e 是异常对象
```

## 练习题

1. 写一个函数，处理用户输入数字，进行除法运算，捕获所有可能的异常
2. 创建一个 `validate_stock()` 函数，验证股票代码、名称、价格，抛出合适的异常
3. 用异常处理改写之前的文件读写代码
4. 实现一个带重试的 API 调用（失败自动重试3次）
5. 创建一个自定义异常类，在股票数据处理中使用

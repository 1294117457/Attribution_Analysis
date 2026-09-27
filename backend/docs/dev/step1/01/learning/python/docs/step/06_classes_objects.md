# Step 06: 类和对象

## 学习目标
理解面向对象编程的基本概念：类、对象、属性、方法

## 概念速览

```python
# 定义类
class 类名:
    def __init__(self, 参数):  # 构造函数
        self.属性 = 参数
    
    def 方法(self):
        """实例方法"""

# 创建对象
对象 = 类名(参数)
对象.方法()
```

## 任务

### 任务 1: 基本类定义

创建 `demo_06_class.py`：

```python
# 1. 定义股票类
class Stock:
    """股票类"""
    
    def __init__(self, code, name, price):
        """初始化股票信息"""
        self.code = code
        self.name = name
        self.price = price
        self.open_price = price
    
    def update_price(self, new_price):
        """更新价格"""
        self.price = new_price
    
    def get_change(self):
        """获取涨跌额"""
        return self.price - self.open_price
    
    def get_change_pct(self):
        """获取涨跌幅"""
        return (self.get_change() / self.open_price) * 100
    
    def display(self):
        """显示股票信息"""
        change = self.get_change()
        sign = "+" if change > 0 else ""
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        return f"{emoji} {self.name}({self.code}): {self.price} ({sign}{change:.2f})"

# 2. 创建对象
stock = Stock("600519", "贵州茅台", 1500)
print(stock.display())

# 3. 调用方法
stock.update_price(1550)
print(f"涨跌额: {stock.get_change():.2f}")
print(f"涨跌幅: {stock.get_change_pct():.2f}%")
print(stock.display())
```

### 任务 2: 带默认值的类

```python
class StockWithDefault:
    """带默认值的股票类"""
    
    def __init__(self, code, name, price=0.0, change=0.0):
        self.code = code
        self.name = name
        self.price = price
        self.change = change
    
    def update(self, price, change):
        """更新价格和涨跌"""
        self.price = price
        self.change = change
    
    def __str__(self):
        """字符串表示"""
        sign = "+" if self.change > 0 else ""
        return f"{self.name}({self.code}): {self.price} ({sign}{self.change}%)"
    
    def __repr__(self):
        """调试表示"""
        return f"Stock('{self.code}', '{self.name}', {self.price}, {self.change})"

# 测试
stock1 = StockWithDefault("600519", "贵州茅台")
stock2 = StockWithDefault("000858", "五粮液", 150.0, 2.5)

print(stock1)
print(stock2)
print(repr(stock1))
```

### 任务 3: 类属性 vs 实例属性

```python
class Stock:
    """股票类"""
    
    # 类属性：所有实例共享
    market = "A股"
    exchange = "上交所"
    
    def __init__(self, code, name, price):
        # 实例属性：每个实例独立
        self.code = code
        self.name = name
        self.price = price
    
    def display(self):
        return f"[{self.market}] {self.name}: {self.price}"

# 测试
stock1 = Stock("600519", "贵州茅台", 1500)
stock2 = Stock("000858", "五粮液", 150)

# 类属性：类名.属性 或 实例.属性
print(Stock.market)      # A股
print(stock1.market)    # A股
print(stock2.market)    # A股

# 修改类属性会影响所有实例
Stock.market = "中国A股"
print(stock1.market)    # 中国A股
print(stock2.market)    # 中国A股

# 修改实例属性不影响其他实例
stock1.market = "美股"
print(stock1.market)    # 美股
print(stock2.market)    # 中国A股（不受影响）
```

## 运行验证

```bash
python demo_06_class.py
```

## 下一步
阅读 `../docs/analysis/06_classes_objects.md` 深入理解

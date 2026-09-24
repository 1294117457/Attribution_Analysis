# Step 07: 继承和多态

## 学习目标
理解类的继承和方法重写

## 概念速览

```python
# 父类
class Animal:
    def speak(self):
        pass

# 子类
class Dog(Animal):  # 括号内写父类名
    def speak(self):  # 重写父类方法
        return "汪汪"

# 创建子类对象
dog = Dog()
dog.speak()  # "汪汪"
```

## 任务

### 任务 1: 基本继承

创建 `demo_07_inheritance.py`：

```python
# 1. 基础类（父类）
class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        return "..."
    
    def info(self):
        return f"{self.name}: {self.speak()}"

# 2. 子类
class Dog(Animal):
    def speak(self):
        return "汪汪！"

class Cat(Animal):
    def speak(self):
        return "喵喵~"

class StockAnalyzer(Animal):  # 继承自 Animal
    def speak(self):
        return "📈 涨了！"

# 3. 创建对象
dog = Dog("旺财")
cat = Cat("咪咪")
analyzer = StockAnalyzer("茅台分析器")

print(dog.info())
print(cat.info())
print(analyzer.info())
```

### 任务 2: 调用父类方法

```python
class Stock:
    """股票基类"""
    
    def __init__(self, code, name, price):
        self.code = code
        self.name = name
        self.price = price
    
    def get_info(self):
        return f"{self.name}({self.code}): {self.price}"

class StockWithChange(Stock):
    """带涨跌的股票类"""
    
    def __init__(self, code, name, price, open_price):
        # 调用父类构造函数
        super().__init__(code, name, price)
        # 新增属性
        self.open_price = open_price
    
    def get_change(self):
        return self.price - self.open_price
    
    def get_change_pct(self):
        return (self.get_change() / self.open_price) * 100
    
    # 重写父类方法
    def get_info(self):
        # 调用父类方法 + 扩展
        base_info = super().get_info()
        change = self.get_change()
        sign = "+" if change > 0 else ""
        return f"{base_info} ({sign}{change:.2f})"

# 测试
stock = Stock("600519", "贵州茅台", 1500)
print(stock.get_info())

stock2 = StockWithChange("600519", "贵州茅台", 1550, 1500)
print(stock2.get_info())
```

### 任务 3: 多态

```python
class Shape:
    """形状基类"""
    def area(self):
        raise NotImplementedError("子类必须实现 area 方法")

class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    def area(self):
        return self.width * self.height

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius
    
    def area(self):
        return 3.14159 * self.radius ** 2

class Triangle(Shape):
    def __init__(self, base, height):
        self.base = base
        self.height = height
    
    def area(self):
        return 0.5 * self.base * self.height

# 多态：同一种接口，不同实现
shapes = [
    Rectangle(10, 5),
    Circle(5),
    Triangle(10, 5)
]

for shape in shapes:
    print(f"{shape.__class__.__name__}: 面积 = {shape.area():.2f}")
```

## 运行验证

```bash
python demo_07_inheritance.py
```

## 下一步
阅读 `../docs/analysis/07_inheritance_polymorphism.md` 深入理解

# 继承和多态详解

## 一、什么是继承？

继承是一种**复用代码**的方式，子类可以继承父类的属性和方法。

```python
# 父类
class Animal:
    def __init__(self, name):
        self.name = name

# 子类：自动拥有父类的所有属性和方法
class Dog(Animal):
    pass  # 空类，但已经继承了 Animal

dog = Dog("旺财")
print(dog.name)  # "旺财" - 继承自父类
```

### 类继承关系

```
Animal (父类/基类)
├── Dog (子类)
├── Cat (子类)
└── Bird (子类)
```

## 二、super() 函数

super() 用于调用父类的方法：

```python
class Stock:
    def __init__(self, code, name, price):
        self.code = code
        self.name = name
        self.price = price

class StockWithVolume(Stock):
    def __init__(self, code, name, price, volume):
        # 调用父类的 __init__
        super().__init__(code, name, price)
        # 新增属性
        self.volume = volume
```

### 不使用 super() 的写法（不推荐）

```python
class StockWithVolume(Stock):
    def __init__(self, code, name, price, volume):
        # 手动复制代码 ❌ 不好
        self.code = code
        self.name = name
        self.price = price
        # 新增属性
        self.volume = volume
```

## 三、方法重写 (Override)

子类可以重写父类的方法：

```python
class Animal:
    def speak(self):
        return "..."

class Dog(Animal):
    def speak(self):  # 重写
        return "汪汪"

class Cat(Animal):
    def speak(self):  # 重写
        return "喵喵"
```

### 调用父类被重写的方法

```python
class Stock:
    def get_info(self):
        return f"{self.name}: {self.price}"

class StockWithChange(Stock):
    def get_info(self):
        # 先调用父类方法
        base = super().get_info()
        # 再添加额外信息
        return f"{base}, 涨跌: {self.change}"
```

## 四、多态 (Polymorphism)

同一个方法调用，不同对象有不同行为：

```python
class Shape:
    def area(self):
        raise NotImplementedError

class Rectangle(Shape):
    def area(self):
        return self.width * self.height

class Circle(Shape):
    def area(self):
        return 3.14 * self.radius ** 2

# 多态：同一接口
shapes = [Rectangle(10, 5), Circle(3)]
for shape in shapes:
    print(shape.area())  # 自动调用正确的 area()
```

## 五、抽象类 (Abstract Class)

抽象类不能直接实例化，子类必须实现抽象方法：

```python
from abc import ABC, abstractmethod

class Animal(ABC):  # 必须继承 ABC
    @abstractmethod
    def speak(self):  # 抽象方法
        pass

# ❌ 不能实例化抽象类
# animal = Animal()  # TypeError

# ✅ 子类必须实现抽象方法
class Dog(Animal):
    def speak(self):  # 必须实现
        return "汪汪"

dog = Dog()  # 可以
```

### 为什么要用抽象类？

```python
# 没有抽象类
class Shape:
    def area(self):
        return 0  # 默认实现，但子类可能忘记重写

# 抽象类强制子类实现
class Shape(ABC):
    @abstractmethod
    def area(self):
        pass  # 不实现，强制子类实现
```

## 六、多继承

Python 支持多继承（不推荐，容易混乱）：

```python
class A:
    def method(self):
        return "A"

class B:
    def method(self):
        return "B"

class C(A, B):  # 继承 A 和 B
    pass

c = C()
print(c.method())  # "A" - 先继承的优先
```

### MRO (Method Resolution Order)

```python
class C(A, B):
    pass

print(C.__mro__)  # 查看方法查找顺序
```

## 七、Python vs JavaScript 对比

| Python | JavaScript | 说明 |
|--------|------------|------|
| `class Dog(Animal):` | `class Dog extends Animal {}` | 继承语法 |
| `super().__init__(args)` | `super(args)` | 调用父类构造函数 |
| `super().method()` | `super.method()` | 调用父类方法 |
| `@abstractmethod` | `abstract method()` | 抽象方法 |

## 八、实战应用

### 基础检测器 → 具体检测器

```python
from abc import ABC, abstractmethod

class BaseDetector(ABC):
    """检测器基类"""
    
    def __init__(self, name):
        self.name = name
        self.results = []
    
    @abstractmethod
    def detect(self, data):
        """检测逻辑，子类必须实现"""
        pass
    
    def save_result(self, result):
        self.results.append(result)
    
    def get_results(self):
        return self.results

class PriceDetector(BaseDetector):
    """价格异常检测器"""
    
    def detect(self, data):
        """实现价格检测"""
        anomalies = []
        for item in data:
            if abs(item['change']) > 10:
                anomalies.append(item)
        return anomalies

class VolumeDetector(BaseDetector):
    """成交量异常检测器"""
    
    def detect(self, data):
        """实现成交量检测"""
        anomalies = []
        avg_volume = sum(d['volume'] for d in data) / len(data)
        for item in data:
            if item['volume'] > avg_volume * 3:
                anomalies.append(item)
        return anomalies

# 使用
price_detector = PriceDetector("价格异常")
volume_detector = VolumeDetector("成交量异常")

# 多态：同一接口
for detector in [price_detector, volume_detector]:
    result = detector.detect(sample_data)
    print(f"{detector.name}: 发现 {len(result)} 个异常")
```

## 常见问题

### 1. 调用父类方法的时机
```python
class Child(Parent):
    def __init__(self, extra):
        # ❌ 太早调用
        super().__init__()
        self.extra = extra  # 可能用到父类属性
        
        # ✅ 先设置自己的属性
        self.extra = extra
        # ✅ 再调用父类
        super().__init__()
```

### 2. 多继承的方法冲突
```python
# 不推荐多继承，优先用组合
class A:
    def method(self):
        return "A"

class B:
    def method(self):
        return "B"

class C(A, B):  # 如果 A 和 B 都有 method()，优先用 A
    pass
```

## 练习题

1. 创建 `Animal` 基类，派生出 `Dog`, `Cat` 子类
2. 创建 `Vehicle` 基类，`Car` 和 `Bike` 子类，共用启动/停止方法
3. 用抽象类实现不同类型的检测器
4. 创建一个继承链：`Person` → `Employee` → `Manager`
5. 用继承重构股票分析代码，创建基础股票类和增强股票类

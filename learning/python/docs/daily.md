##### var

```
python中，也是可以直接定义变量，无需定义类型
	比如name="abc",count=123,price=123.456,is_valid=true
同时f-string使用重要，这里f就是format的意思对吗，
 	print(f"name:{name}",
 	print(f"abc{count}"),
 	print(f"{stock['code']}")
```

##### loop

```
 for,while,if-else,range,break,continue
```

##### module

```
import
from import
from import as 

_init_.py
	_all_=[]
```

##### object-class

##### inheritance

```
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

多态指的是方法，
	同一个方法，传入基类相同的不同object，实现不同的方法

```

##### exception

```
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

##### file

```
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
    
file,json,csv,path
```


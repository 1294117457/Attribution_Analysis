# 快速入门详解

## 一、FastAPI 是什么？

### 定位

| 框架 | 语言 | 特点 | 适用场景 |
|------|------|------|----------|
| FastAPI | Python | 高性能、自动文档 | ML/数据服务、REST API |
| Express | Node.js | 简洁、灵活 | Web 应用、API |
| Spring Boot | Java | 企业级、功能全 | 企业应用 |
| Flask | Python | 轻量、灵活 | 小型应用、脚本 |

### 为什么选 FastAPI？

```
FastAPI 的优势
├── 🚀 性能高：基于 Starlette，接近 Node/Go
├── 📝 自动文档：Swagger/ReDoc 开箱即用
├── ✅ 类型安全：Pydantic + 类型提示
├── 🔄 异步支持：原生 async/await
└── 🛠️ 生态好：可以复用所有 Python 库
```

## 二、基本结构解析

```python
from fastapi import FastAPI

app = FastAPI()  # ① 创建应用实例

@app.get("/")   # ② 装饰器定义路由
def read_root(): # ③ 处理函数
    return {"message": "Hello World"}  # ④ 返回 JSON
```

### 每一步做了什么？

```
① FastAPI() 
   → 创建 ASGI 应用实例
   → 配置了路由、错误处理、文档生成

② @app.get("/")
   → 装饰器将函数注册为路由
   → GET 方法，路径 "/"
   → 也可以用 @app.post(), @app.put(), @app.delete()

③ def read_root()
   → 异步函数（可以加 async）
   → FastAPI 会自动调用这个函数处理请求

④ return {...}
   → Python 字典自动转为 JSON 响应
   → Content-Type: application/json
```

## 三、路由装饰器详解

```python
# GET 请求
@app.get("/path")
def get_handler():
    pass

# POST 请求
@app.post("/path")
def post_handler():
    pass

# PUT 请求
@app.put("/path")
def put_handler():
    pass

# DELETE 请求
@app.delete("/path")
def delete_handler():
    pass

# OPTIONS / PATCH 等
@app.options("/path")
@app.patch("/path")
```

## 四、运行方式

### 方式1：命令行

```bash
uvicorn main:app --reload
# main: 应用所在的模块名
# app: FastAPI 实例名
# --reload: 开发模式自动重载
```

### 方式2：代码中运行

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("demo_01_hello:app", reload=True)
```

### 方式3：使用 FastAPI CLI

```bash
fastapi dev demo_01_hello.py
```

## 五、自动文档原理

FastAPI 基于你的类型提示自动生成 OpenAPI 文档：

```
请求/响应类型提示
      ↓
Pydantic 模型
      ↓
OpenAPI Schema
      ↓
Swagger UI / ReDoc
```

### Swagger UI (推荐)

地址：`http://localhost:8000/docs`

特点：
- 可以直接在线测试 API
- 可以填写参数并执行
- 显示请求/响应示例

### ReDoc

地址：`http://localhost:8000/redoc`

特点：
- 文档展示更美观
- 适合阅读和分享

## 六、响应格式

### 返回字典 → JSON

```python
@app.get("/")
def read_root():
    return {"key": "value"}
# → {"key": "value"}
```

### 返回列表 → JSON 数组

```python
@app.get("/items")
def read_items():
    return ["苹果", "香蕉", "橙子"]
# → ["苹果", "香蕉", "橙子"]
```

### 返回字符串

```python
@app.get("/text")
def read_text():
    return "Hello"
# → "Hello"
```

### 返回 Pydantic 模型

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

@app.get("/item")
def read_item():
    return Item(name="苹果", price=5.0)
# → {"name": "苹果", "price": 5.0}
```

## 七、async vs 同步函数

### 同步函数（普通）

```python
@app.get("/sync")
def read_sync():
    # 同步操作
    return {"type": "sync"}
```

### 异步函数

```python
@app.get("/async")
async def read_async():
    # 异步操作
    await some_async_operation()
    return {"type": "async"}
```

### 什么时候用 async？

```python
# ✅ 用 async 的情况
@app.get("/fetch")
async def fetch_data():
    # I/O 操作：请求外部 API
    response = await httpx.get("https://api.example.com")
    return response.json()

# ✅ 用 sync 的情况
@app.get("/calculate")
def calculate():
    # CPU 计算
    result = heavy_computation()
    return {"result": result}
```

### 小技巧

如果不确定，用普通函数就行。FastAPI 会自动处理：

```python
# 这两种写法效果一样
@app.get("/a")
def handler():
    return {}

@app.get("/b")
async def handler():
    return {}
```

## 八、调试技巧

### 1. 打印日志

```python
import logging

logging.basicConfig(level=logging.INFO)

@app.get("/")
def read_root():
    logging.info("收到请求")
    return {"message": "Hello"}
```

### 2. 查看请求信息

```python
from fastapi import Request

@app.get("/")
async def read_root(request: Request):
    print(f"请求路径: {request.url}")
    print(f"请求方法: {request.method}")
    print(f"客户端IP: {request.client}")
    return {"message": "Hello"}
```

### 3. 常见错误

```python
# ❌ 错误：忘记 return
@app.get("/")
def no_return():
    print("Hello")  # 没有返回值

# ✅ 正确
@app.get("/")
def with_return():
    return {"message": "Hello"}
```

## 九、与你的项目对比

```python
# 你的项目 app/main.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy"}

# 这是标准的 FastAPI 结构！
```

```javascript
// Node.js Express 对比
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.json({ message: 'Hello' });
});
```

## 练习题

1. 创建 API，返回当前服务器时间
2. 创建一个计算器 API，支持加、减、乘、除
3. 创建股票信息 API，返回固定的几只股票数据
4. 查看自动生成的 OpenAPI 文档：`/openapi.json`
5. 尝试用不同的 HTTP 方法定义多个路由

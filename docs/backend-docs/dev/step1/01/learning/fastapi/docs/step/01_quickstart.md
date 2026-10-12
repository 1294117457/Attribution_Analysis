# Step 01: 快速入门 - Hello World

## 学习目标
创建第一个 FastAPI 应用，理解基本结构

## 概念速览

```python
from fastapi import FastAPI

app = FastAPI()  # 创建应用实例

@app.get("/")     # 装饰器定义路由
def read_root():
    return {"message": "Hello World"}
```

## 任务

### 任务 1: 创建 Hello World

创建 `demo_01_hello.py`：

```python
from fastapi import FastAPI

# 创建 FastAPI 实例
app = FastAPI()

# 定义 GET 路由
@app.get("/")
def read_root():
    """根路径 - 返回欢迎信息"""
    return {
        "message": "欢迎使用股票分析 API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# 定义更多路由
@app.get("/health")
def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

@app.get("/hello/{name}")
def say_hello(name: str):
    """路径参数示例"""
    return {"message": f"你好，{name}！"}

# 运行服务器
# uvicorn demo_01_hello:app --reload
```

### 任务 2: 启动和测试

**启动服务器：**

```bash
uvicorn demo_01_hello:app --reload
```

**测试 API：**

```bash
# 测试根路径
curl http://localhost:8000/

# 测试健康检查
curl http://localhost:8000/health

# 测试路径参数
curl http://localhost:8000/hello/张三

# 测试带查询参数
curl "http://localhost:8000/hello/李四?name_extra=附加信息"
```

### 任务 3: 打开自动文档

FastAPI 自动生成交互式文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 知识点

| 概念 | 说明 |
|------|------|
| `@app.get("/")` | 定义 GET 请求路由 |
| `def read_root():` | 处理函数，返回 JSON |
| `uvicorn` | ASGI 服务器，运行 FastAPI |
| `--reload` | 修改代码自动重载 |

## 常见 HTTP 方法

| 方法 | 用途 | 示例 |
|------|------|------|
| GET | 获取数据 | `@app.get("/items")` |
| POST | 创建数据 | `@app.post("/items")` |
| PUT | 更新数据 | `@app.put("/items")` |
| DELETE | 删除数据 | `@app.delete("/items")` |

## 下一步
阅读 `../docs/analysis/01_quickstart.md` 深入理解

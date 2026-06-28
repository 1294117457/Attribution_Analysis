# FastAPI 基础学习路径

## 学习目标
掌握 FastAPI 框架，能够构建 Web API 服务

## 前置知识
- Python 基础（变量、函数、类、异常处理）
- HTTP 协议基础概念
- RESTful API 设计原则

## 学习顺序

### 第一阶段：核心基础（Day 1）

| Step | 标题 | 内容 | 预计时间 |
|------|------|------|----------|
| 01 | 快速入门 | Hello World + 路由 | 30分钟 |
| 02 | 请求参数 | 路径参数、查询参数 | 40分钟 |
| 03 | 请求体 | Pydantic 模型 | 40分钟 |

### 第二阶段：数据库集成（Day 2）

| Step | 标题 | 内容 | 预计时间 |
|------|------|------|----------|
| 04 | 数据库连接 | SQLAlchemy 基础 | 50分钟 |
| 05 | CRUD 操作 | 数据库增删改查 | 50分钟 |

### 第三阶段：进阶特性（Day 3）

| Step | 标题 | 内容 | 预计时间 |
|------|------|------|----------|
| 06 | 中间件和异常 | 全局处理 | 40分钟 |
| 07 | 认证授权 | 基础安全 | 50分钟 |
| 08 | 项目结构 | 工程化组织 | 40分钟 |

## 学习方法
1. 先阅读 `docs/step/` 中的指导
2. 启动开发服务器观察效果
3. 用 curl 或 Postman 测试 API
4. 对照 `docs/analysis/` 理解原理

## 运行环境

```bash
cd learning/fastapi
source ../venv/bin/activate  # 激活虚拟环境
uvicorn demo_01:app --reload  # 启动开发服务器
```

## API 测试

```bash
# 测试 Hello World
curl http://localhost:8000/

# 测试带参数
curl http://localhost:8000/items/1?q=hello

# 测试文档
open http://localhost:8000/docs
open http://localhost:8000/redoc
```

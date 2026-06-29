# Backend 开发文档

## 概述

智能金融数据归因分析平台后端开发指南，以**数据采集**为核心展开。

---

## 文档结构

```
docs/backend/
├── README.md              # 本文档
│
├── data/                  # 数据采集模块 (核心)
│   ├── README.md          # data 模块概览
│   ├── step/              # 开发步骤
│   │   ├── 01_env_setup.md        # 环境配置
│   │   ├── 02_core_setup.md       # core 模块
│   │   ├── 03_database_setup.md   # 数据库配置
│   │   ├── 04_app_setup.md        # app 模块
│   │   ├── 05_data_module.md      # data 模块
│   │   └── 06_detector_module.md  # 异常检测
│   │
│   └── code/               # 完整代码文件
│       ├── .env.example
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── types.py
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── dependencies.py
│       │   ├── database/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   └── connection.py
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   └── stock.py
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   └── stock_service.py
│       │   └── api/
│       │       ├── __init__.py
│       │       ├── router.py
│       │       └── v1/
│       │           ├── __init__.py
│       │           ├── stocks.py
│       │           └── health.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── akshare_client.py
│       │   ├── schemas.py
│       │   ├── service.py
│       │   └── storage.py
│       └── detector/
│           ├── __init__.py
│           ├── base.py
│           ├── price_detector.py
│           ├── volume_detector.py
│           └── service.py
│
├── ml/                    # ML 模块 (待开发)
│
└── rag/                   # RAG 模块 (待开发)
```

---

## 开发顺序

### 第一阶段：基础框架

| 步骤 | 文档 | 内容 |
|------|------|------|
| 1 | [环境配置](./data/step/01_env_setup.md) | Python 环境、依赖安装、.env |
| 2 | [Core 模块](./data/step/02_core_setup.md) | 配置、类型定义 |
| 3 | [数据库配置](./data/step/03_database_setup.md) | SQLAlchemy 模型、连接 |
| 4 | [App 模块](./data/step/04_app_setup.md) | FastAPI 入口、API 路由 |
| 5 | [Data 模块](./data/step/05_data_module.md) | AkShare 数据采集 |
| 6 | [Detector 模块](./data/step/06_detector_module.md) | 异常检测 |

---

## 当前状态

```
✅ 完成
├── 环境配置
├── Core 模块基础
├── 数据库连接
└── App 模块骨架

⏳ 进行中
└── Data 数据采集模块

📋 待开发
├── 异常检测模块
├── ML 模块
└── RAG 模块
```

---

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入数据库信息
```

### 3. 启动服务

```bash
cd backend
uvicorn app.main:app --reload
```

### 4. 访问 API

```
http://localhost:8000/docs  # Swagger 文档
http://localhost:8000/health  # 健康检查
```

---

## 相关链接

- [系统架构](../architecture.md)
- [API 文档](../api.md)
- [数据源说明](../data-source.md)

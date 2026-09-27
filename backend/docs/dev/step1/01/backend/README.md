# Backend 开发文档

## 概述

智能金融数据归因分析平台后端开发指南，**当前阶段只开发数据采集功能**。

---

## 目录结构

```
docs/backend/
├── README.md              # 本文档
│
└── data/                  # 数据采集模块
    ├── README.md          # data 模块概览
    ├── step/              # 开发步骤
    │   ├── 01_env_setup.md        # 环境配置
    │   ├── 02_core_setup.md       # core 模块
    │   ├── 03_database_setup.md   # 数据库配置
    │   ├── 04_app_setup.md        # app 模块
    │   ├── 05_data_module.md      # data 数据采集
    │   └── 06_detector_module.md  # 异常检测
    │
    └── code/               # 完整代码文件
        ├── .env.example
        ├── requirements.txt
        ├── core/
        ├── app/
        ├── data/
        └── detector/
```

---

## 开发顺序

| 步骤 | 文档 | 内容 |
|------|------|------|
| 1 | `data/step/01_env_setup.md` | 安装依赖、配置 .env |
| 2 | `data/step/02_core_setup.md` | core 模块（配置、类型） |
| 3 | `data/step/03_database_setup.md` | 数据库连接、ORM 模型 |
| 4 | `data/step/04_app_setup.md` | FastAPI 入口、API 路由 |
| 5 | `data/step/05_data_module.md` | AkShare 数据采集 |
| 6 | `data/step/06_detector_module.md` | 异常检测（价格/成交量） |

---

## 当前状态

```
✅ 进行中
└── 数据采集模块开发

📋 后续开发（暂不进行）
├── ML 模块（机器学习预测）
└── RAG 模块（知识检索）
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

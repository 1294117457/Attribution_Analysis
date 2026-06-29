# Backend 模块文档索引

## 概述

本文档描述智能金融数据归因分析平台的后端模块开发。

---

## 模块列表

### 1. Core 模块
**定位**：核心共享层，所有其他模块的基础

**文档**：
- [开发步骤](./core/step/01_create_core.md) - 创建 core 模块
- [设计分析](./core/analysis/01_core_design.md) - 核心设计详解

**内容**：
- 全局配置管理
- 基础枚举/类型定义
- 核心领域模型（Stock, Anomaly, Attribution）

---

### 2. App 模块
**定位**：FastAPI 应用层，提供 API 接口

**文档**：
- [开发步骤](./app/step/01_create_app.md) - 创建 app 模块
- [设计分析](./app/analysis/01_app_design.md) - API 设计详解

**内容**：
- FastAPI 入口和路由
- 数据库 ORM 模型
- 业务服务封装
- API DTO 定义

---

### 3. Data 模块
**定位**：数据采集层

**文档**：
- [开发步骤](./data/step/01_create_data.md) - 创建 data 模块
- [设计分析](./data/analysis/01_data_design.md) - 数据采集设计详解

**内容**：
- AkShare 数据获取
- 股票采集器
- 新闻采集器
- 数据解析和转换

---

### 4. ML 模块
**定位**：机器学习层

**文档**：
- [ML 开发步骤](./ml/step/01_create_ml.md) - 创建 ml 模块
- [异常检测开发步骤](./ml/step/01_create_detector.md) - 异常检测实现
- [ML 设计分析](./ml/analysis/01_ml_design.md) - ML 设计详解
- [异常检测设计分析](./ml/analysis/01_detector_design.md) - 异常检测设计详解

**内容**：
- 异常检测（Z-Score、IQR、波动率）
- 价格预测（LSTM、XGBoost）
- 情感分类（VADER）
- 技术指标计算

---

### 5. RAG 模块
**状态**：待开发

**计划内容**：
- Embedding 处理
- 向量存储（PGVector）
- 知识检索

---

### 6. Graph 模块
**状态**：待开发

**计划内容**：
- LangGraph 工作流
- Agent 节点定义
- 工具封装

---

## 开发顺序

### 第一阶段：基础框架
1. **Core** → 定义配置和类型
2. **App** → FastAPI 骨架
3. **Data** → 数据采集

### 第二阶段：核心功能
4. **ML/Detector** → 异常检测
5. **ML/Classifier** → 情感分析
6. **ML/Predictor** → 价格预测

### 第三阶段：高级功能
7. **RAG** → 知识检索
8. **Graph** → 工作流编排

---

## 目录结构

```
backend/
├── core/                    ✅ 完成
│   ├── step/
│   └── analysis/
│
├── app/                     ✅ 完成
│   ├── step/
│   └── analysis/
│
├── data/                    ✅ 完成
│   ├── step/
│   └── analysis/
│
├── ml/                      ✅ 完成
│   ├── step/
│   │   ├── 01_create_ml.md
│   │   └── 01_create_detector.md
│   └── analysis/
│       ├── 01_ml_design.md
│       └── 01_detector_design.md
│
├── rag/                     ⏳ 待开发
│
└── graph/                   ⏳ 待开发
    └── analysis/
```

---

## 快速开始

### 1. 创建 Core 模块

```bash
cd backend
mkdir -p core/models
touch core/__init__.py core/config.py core/types.py
touch core/models/__init__.py core/models/stock.py core/models/anomaly.py core/models/attribution.py
```

参考：[core/step/01_create_core.md](./core/step/01_create_core.md)

### 2. 创建 App 模块

```bash
mkdir -p app/api app/models app/database/models app/services app/scripts
```

参考：[app/step/01_create_app.md](./app/step/01_create_app.md)

### 3. 创建 Data 模块

```bash
mkdir -p data/models data/fetchers data/collectors data/parsers data/scripts
```

参考：[data/step/01_create_data.md](./data/step/01_create_data.md)

### 4. 创建 ML 模块

```bash
mkdir -p ml/models ml/detector ml/predictor ml/classifier ml/features ml/scripts
```

参考：
- [ml/step/01_create_ml.md](./ml/step/01_create_ml.md)
- [ml/step/01_create_detector.md](./ml/step/01_create_detector.md)

---

## 依赖关系

```
core (最底层)
  ↑
  ├── app
  ├── data
  ├── ml
  ├── rag
  └── graph

无循环依赖！
```

---

## 相关链接

- [系统架构](../architecture.md)
- [API 文档](../api.md)
- [数据源说明](../data-source.md)
- [部署指南](../deployment.md)

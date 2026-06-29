# 数据采集模块文档

## 模块概述

```
data 模块负责：
1. 从 AkShare 获取 A 股 K 线数据
2. 存储到 PostgreSQL 数据库
3. 提供数据查询接口
```

---

## 子模块

| 子模块 | 职责 |
|--------|------|
| `akshare_client` | AkShare 数据获取 |
| `schemas` | 数据模型定义 |
| `service` | 业务逻辑 |
| `storage` | 数据库存储 |

---

## 数据流

```
AkShare API
    │
    ▼
akshare_client (获取数据)
    │
    ▼
schemas (验证/转换)
    │
    ▼
service (业务逻辑)
    │
    ▼
storage (存储到 DB)
    │
    ▼
PostgreSQL
```

---

## 相关文档

- [环境配置](./step/01_env_setup.md)
- [开发步骤](./step/05_data_module.md)
- [代码文件](../code/data/)

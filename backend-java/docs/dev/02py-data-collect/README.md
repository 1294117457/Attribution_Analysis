# 02 Python 数据采集服务 · 开发文档

> 将 `backend-java` 工程中的**数据采集相关功能**下沉到独立 Python 服务 `data-collector` 的整体设计与实施文档。
> 评审稿，待讨论。

---

## 一、文档索引

| #   | 文档                                            | 主题                              | 谁看     |
| --- | ----------------------------------------------- | --------------------------------- | -------- |
| 00  | [00-overview.md](./00-overview.md)             | **整体架构 + 安全设计 + 调用链路** | 全员     |
| 01  | [01-python-architecture.md](./01-python-architecture.md) | Python 服务内部架构、模块划分、采集器实现 | Python 开发 |
| 02  | [02-data-objects.md](./02-data-objects.md)     | Python 端 DataObject / 接口契约设计 | Python + Java 联调人 |
| 03  | [03-java-simplify.md](./03-java-simplify.md)   | Java 工程精简后的架构、Port/Adapter、调用方式 | Java 开发 |
| 04  | [04-interface-contract.md](./04-interface-contract.md) | 跨服务 HTTP 接口清单与契约（保留/废弃/新增） | 前后端联调 |
| 05  | [05-migration-plan.md](./05-migration-plan.md) | 迁移计划（分阶段、回滚策略、验收标准） | 全员 |

---

## 二、阅读顺序

```
架构师 / PM   →  00 → 03 → 05
Python 开发   →  00 → 01 → 02 → 04 → 05
Java 开发     →  00 → 03 → 04 → 05
前端开发      →  04 → 00（了解链路，不直接调 Python）
运维          →  00 → 05（部署/扩容/告警）
```

---

## 三、TL;DR

- **目标**：把 `backend-java` 中所有 `infrastructure/adapter/collector/**` 采集逻辑（含 tushare HTTP、东方财富 HTTP、新浪 HTTP、akshare 概念等）全部迁出，独立为 `data-collector` (FastAPI) 服务。
- **Java 端**：删除原 collector 包，仅保留 `domain/port/DataCollectorPort`（输出端口）+ `infrastructure/adapter/collector/PythonDataCollectorAdapter`（HTTP 调用实现）。其余 Service / Repository / Controller 不变。
- **Python 端**：FastAPI 单进程，路由按数据源分模块（`/klines/*` `/basic/*` `/fundamentals/*` `/capital/*` `/concepts/*`），内部用 `Collector` 抽象 + fallback 链。
- **接口契约**：见 `04-interface-contract.md`。Java 端只调 Python 的 `/collect/*`（批量）与 `/query/*`（即时查询）。
- **安全**：服务间走**内网** + **共享密钥（HMAC 签名）** + **IP 白名单**；前端 → Java 走原 JWT。
- **进度/任务追踪**：依然在 Java 侧（PostgreSQL + Redis），Python 只做无状态计算。

---

## 四、与其他文档的关系

| 文档                                               | 关系                                        |
| -------------------------------------------------- | ------------------------------------------- |
| `../../design/architecture/README.md`              | Java 工程架构规范（Port/Adapter 概念引用此） |
| `../../design/architecture/04-interface-spec.md`   | Java 对前端暴露的接口规范（保持不变）         |
| `../../design/api/04-README.md`                    | Java API 设计规范（保持不变）               |
| `../01api/04-architecture-refactor.md`             | Java 工程内部 DTO / 包结构重构（背景文档）  |
| `../00rebuild/04-data-collection.md`               | 数据采集原始设计（**已被本套文档替代**）    |
| `../00rebuild/05-api-migration.md`                 | Python → Java 接口迁移总览（本套是其延伸）  |

---

## 五、维护原则

1. **跨服务契约变更必须先改 `04-interface-contract.md`，再改代码**（双发版本、灰度）
2. **Python 服务无状态**——任何写操作（任务进度、缓存）都落 Java 侧
3. **采集源（tushare/akshare/pytdx）变化时，先更新 `01-python-architecture.md §4 fallback 矩阵`**
4. **每次新增/废弃 HTTP 接口必须在 `04-interface-contract.md` 的版本记录里登记**

---

## 六、状态

| 状态       | 时间       |
| ---------- | ---------- |
| 初稿完成   | 2026-09-26 |
| 待评审     | -          |
| 评审通过   | -          |
| 实施完成   | -          |

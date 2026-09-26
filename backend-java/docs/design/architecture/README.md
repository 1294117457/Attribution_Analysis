# backend-java 设计规范

> Attribution Analysis 后端的设计规范集合。

## 文档索引

| 文档 | 内容 | 谁看 |
|------|------|------|
| [00-overview.md](./00-overview.md) | 总统架构、依赖铁律、模块包结构、DTO 边界 | 新人 / 全员 |
| [01-domain-spec.md](./01-domain-spec.md) | entity / vo / repository / DomainService / DomainVO 边界 | 写领域层的人 |
| [02-application-spec.md](./02-application-spec.md) | AppService / Command-Query-Result / DTO 边界 | 写用例的人 |
| [03-infrastructure-spec.md](./03-infrastructure-spec.md) | Adapter / Persistence / Query / Config / Exception | 写外部实现的人 |
| [04-interface-spec.md](./04-interface-spec.md) | Controller / DTO / 入参出参 / 异常处理 | 写 API 的人 |

## 阅读顺序

```
新人    →  00 → 01 → 02 → 03 → 04
写业务  →  00 → 01 → 02
写接口  →  00 → 04
写外部  →  00 → 03
```

## 与其他文档的关系

| 文档 | 位置 | 目的 |
|------|------|------|
| [../../DDD.md](../../DDD.md) | docs/DDD.md | 概念入门（DDD 是什么） |
| [../rebuild/](../rebuild/) | docs/rebuild/ | 重构路线图与技术栈 |
| `design/`（本目录） | docs/design/ | 落地规范（在我们项目里怎么写） |

## 维护原则

1. **每改一处规范，对应代码也要改**（规范不能脱离实现）
2. **正反例都写**（只写"要怎么做"不够，还要写"为什么不能那样做"）
3. **季度 review 一次**（过时规范及时清理）

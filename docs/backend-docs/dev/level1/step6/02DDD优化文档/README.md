# DDD 优化文档

> 本目录包含 backend 目录结构 DDD 优化的完整方案与实施文档。

---

## 1. 背景

当前 backend 目录存在以下问题：

1. **目录爆炸**：`domain/` 下每个 entity 单独一个目录（25+ 个），难以维护
2. **BO 错位**：BO（应用层数据载体）放在 `domain/` 下，违反 DDD 分层
3. **Converter 冗余**：中央化 Converter 转换类，转换方法与类型分离
4. **Domain Service 散乱**：`domain/service/` 与 entity 平级，混在一起

## 2. 目标

1. ✅ Domain 层按领域模型聚合（`entities/<name>/`）
2. ✅ BO 移到 Application 层（`application/bo/`）
3. ✅ 转换方法分散到各自的类型（`from_` 类方法）
4. ✅ Domain Service 独立目录（`domain/services/`）

## 3. 文档清单

| 序号 | 文档 | 内容 |
|:--|:--|:--|
| 01 | [01-目录结构重组方案.md](01-目录结构重组方案.md) | 总体方案、原则、目标目录结构 |
| 02 | [02-实施清单.md](02-实施清单.md) | 具体迁移操作（文件级别） |
| 03 | [03-转换方法规范.md](03-转换方法规范.md) | `from_` 类方法详细规范 |
| 04 | [04-验收清单.md](04-验收清单.md) | 26 条 AC 验收标准 |

## 4. 推荐阅读顺序

```
[01-目录结构重组方案]  →  [02-实施清单]  →  [03-转换方法规范]  →  [04-验收清单]
       ↓                       ↓                    ↓                    ↓
     了解目标                学习操作              编写代码             验证完成
```

## 5. 关键变更总览

### 5.1 目录变化

| 当前 | 目标 |
|:--|:--|
| `domain/kline/entity.py` | `domain/entities/kline/entity.py` |
| `domain/kline/vo.py` | `domain/entities/kline/vo.py` |
| `domain/kline/repository.py` | `domain/entities/kline/repository.py` |
| `domain/kline/bo.py` | `application/bo/kline.py` |
| `domain/service/` | `domain/services/` |
| `application/converter/` | **删除** |

### 5.2 转换方法分布

```
Entity    →  from_bo(bo)              # 接受 Application 输入
BO        →  from_entity(entity)      # 接受 Domain 输出
VO        →  from_entity(entity)      # 投影构造
Model     →  from_entity(entity)      # 持久化入
         ←  to_entity()              # 持久化出
DTO       →  from_entity(entity)      # 接口层输出
```

### 5.3 目录数对比

| 层级 | 当前 | 目标 | 改善 |
|:--|:--|:--|:--|
| `domain/` 直接子目录 | ~25 个 | 3 个 | **-88%** |
| 单个领域模型文件数 | 分散在多处 | 3 个文件在 `entities/*/` | **内聚** |

## 6. 与 DDD 规范的关系

本方案严格遵循 [`docs/backend-docs/config/DDD.md`](../../config/DDD.md) 定义的：

- **四层职责**：route / application / domain / infrastructure
- **依赖方向**：严格自上而下
- **domain 零外部依赖**：仅 stdlib
- **port 抽象**：application 通过 port 使用外部能力

## 7. 实施状态

| Phase | 状态 | 备注 |
|:--|:--|:--|
| Phase 1：market 重构 | ⏳ 待开始 | 22 个聚合根 |
| Phase 2：concept 重构 | ⏳ 待开始 | 2 个聚合根 |
| Phase 3：collect 重构 | ⏳ 待开始 | 1 个 domain service |
| Phase 4：验证 | ⏳ 待开始 | 26 条 AC |

## 8. 相关文档

| 文档 | 内容 |
|:--|:--|
| [`docs/backend-docs/config/DDD.md`](../../config/DDD.md) | DDD 架构规范（基础） |
| [`docs/backend-docs/dev/step6/01隔离上下文/`](../01隔离上下文/) | 上下文隔离方案（前序） |
| [`docs/backend-docs/dev/step5/03collect优化/`](../../step5/03collect优化/) | collect 优化（前序） |

## 9. 反馈

如对本方案有任何问题或建议，请在 PR 中评论或联系架构组。

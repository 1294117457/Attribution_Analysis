# 04protocol — 采集器协议层重构

## 文档索引

| 文档 | 内容 |
|------|------|
| [01_problem_analysis.md](./01_problem_analysis.md) | 当前架构问题诊断：超级接口违反 ISP、硬编码工厂函数、PytdxFetcher 游离在外 |
| [02_refactor_plan.md](./02_refactor_plan.md) | **主线重构方案**：协议拆分 + 注册中心 + 路由层改造 + 测试策略 + 错误处理 + 并发安全 |
| [03_akshare_extension.md](./03_akshare_extension.md) | **后续扩展**：AKShare 概念板块采集器（独立排期，非本次重构范围） |

## 重构目标

将 `infrastructure/collectors/` 中散落的 5 处硬编码工厂函数统一为**注册中心 + 小协议**模式，使：

- 数据源可按数据类型切换（Tushare 日K / AKShare 概念 / Pytdx 分钟）
- 新增数据源只需实现对应 Protocol + 注册，无需修改 route / service 层
- `PytdxFetcher` 纳入统一协议体系

## 实施顺序

```
阶段 1（基础设施）→ 阶段 2（Service）→ 阶段 3（路由层）→ 阶段 4（清理）
```

详见 [02_refactor_plan.md](./02_refactor_plan.md) 第五节。

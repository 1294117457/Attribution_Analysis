# AKShare 概念采集器扩展方案

> 编写日期：2026-09-24
> 所属阶段：04protocol 重构方案的后续扩展，非本次重构的一部分
>
> 本文档独立于 [02_refactor_plan.md](./02_refactor_plan.md)，便于单独 Review 和排期。

---

## 一、背景与目标

### 1.1 为什么需要 AKShare

当前系统数据来源：

| 数据类型 | 数据源 | 积分要求 | 说明 |
|---------|-------|---------|------|
| 日K线 | Tushare Pro | 需要（2000分够用） | 主力数据源 |
| 分钟K线 | Pytdx（通达信） | 免费 | 透传不落库 |
| 股票基本信息 | Tushare Pro | 需要 | 与日K共用 |
| 日频估值 | Tushare Pro | 需要 | 与日K共用 |
| **概念板块** | ❌ 暂无 | — | 归因分析需要 |

概念板块数据是"归因分析"的关键维度（行业/概念维度的超额收益归因），但 Tushare 对概念板块数据的积分要求较高。AKShare 提供免费的概念板块数据，可作为补充数据源。

### 1.2 AKShare 适合做什么

| AKShare 能力 | 是否使用 | 原因 |
|-------------|---------|------|
| 东方财富概念板块 | ✅ 使用 | 免费，数据全 |
| 同花顺概念板块 | ✅ 使用 | 免费，数据全 |
| 股票实时行情 | ❌ 不使用 | Tushare 够用 |
| 宏观经济数据 | ❌ 不使用 | 非本项目范围 |

---

## 二、目录结构

```
infrastructure/collectors/
├── protocols.py          ← KlineFetcher / MinuteKlineFetcher / ...
├── registry.py           ← 注册中心
├── interfaces.py          ← CollectParams / FetcherProtocol（过渡态）
├── base.py               ← BaseCollector
├── tushare/
│   ├── fetcher.py        ← TushareFetcher
│   └── parser.py
├── pytdx/
│   ├── fetcher.py        ← PytdxFetcher
│   └── parser.py
└── akshare/              ← 新增
    ├── __init__.py
    ├── fetcher.py        ← AKShareConceptFetcher
    └── parser.py         ← 解析东方财富/同花顺概念数据
```

---

## 三、协议实现

### 3.1 ConceptFetcher 协议（已在 protocols.py 定义）

```python
@runtime_checkable
class ConceptFetcher(Protocol):
    """概念板块采集"""
    def fetch_concept_list(self) -> list[Any]: ...
    def fetch_concept_stocks(self, concept_name: str) -> list[Any]: ...

    @property
    def source_name(self) -> str: ...
```

### 3.2 AKShareConceptFetcher 实现

```python
# infrastructure/collectors/akshare/fetcher.py
"""
AKShare 概念板块采集器

数据来源：
- 东方财富概念板块（stock_board_concept_name_em）
- 同花顺概念板块（stock_board_industry_cons_ths）

特点：
- 免费，无需 token
- 数据来源于第三方，可能有延迟
- 适合作为 Tushare 的补充，不作为主数据源
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.protocols import ConceptFetcher
from infrastructure.collectors.akshare.parser import ConceptParser

logger = logging.getLogger(__name__)


class AKShareConceptFetcher(BaseCollector):
    """AKShare 概念板块采集器"""

    def __init__(self) -> None:
        super().__init__()
        self._ensure_deps()

    def _ensure_deps(self) -> None:
        """延迟导入 akshare，避免未安装时影响主流程"""
        try:
            import akshare  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "需要安装 akshare：pip install akshare"
            )

    @property
    def source_name(self) -> str:
        return "akshare"

    def fetch_concept_list(self) -> list[Any]:
        """获取概念板块列表（东方财富）"""
        import akshare as ak
        try:
            df = ak.stock_board_concept_name_em()
            return ConceptParser.parse_list(df)
        except Exception as e:
            self._log("warning", f"获取概念板块列表失败: {e}")
            return []

    def fetch_concept_stocks(self, concept_name: str) -> list[Any]:
        """获取概念板块成分股（同花顺）"""
        import akshare as ak
        try:
            df = ak.stock_board_concept_cons_ths(symbol=concept_name)
            return ConceptParser.parse_stocks(df)
        except Exception as e:
            self._log("warning", f"获取概念 {concept_name} 成分股失败: {e}")
            return []
```

### 3.3 解析器

```python
# infrastructure/collectors/akshare/parser.py

from __future__ import annotations

import pandas as pd
from typing import Any


class ConceptListBO:
    """概念板块列表 BO"""
    def __init__(self, name: str, code: str, count: int, avg_price: float | None):
        self.name = name
        self.code = code
        self.stock_count = count
        self.avg_price = avg_price


class ConceptStockBO:
    """概念板块成分股 BO"""
    def __init__(self, symbol: str, name: str, rank: int, price: float | None):
        self.symbol = symbol
        self.name = name
        self.rank = rank
        self.price = price


class ConceptParser:
    """AKShare 概念数据解析器"""

    @staticmethod
    def parse_list(df: pd.DataFrame) -> list[ConceptListBO]:
        if df is None or df.empty:
            return []
        # 东方财富概念板块字段：板块名称、代码、股票数、平均价格等
        results = []
        for _, row in df.iterrows():
            try:
                results.append(ConceptListBO(
                    name=str(row.get("板块名称", "")),
                    code=str(row.get("板块代码", "")),
                    count=int(row.get("股票数", 0)),
                    avg_price=float(row["平均价格"]) if pd.notna(row.get("平均价格")) else None,
                ))
            except Exception:
                continue
        return results

    @staticmethod
    def parse_stocks(df: pd.DataFrame) -> list[ConceptStockBO]:
        if df is None or df.empty:
            return []
        # 同花顺成分股字段：股票代码、股票名称、排序、现价等
        results = []
        for idx, row in df.iterrows():
            try:
                results.append(ConceptStockBO(
                    symbol=str(row.get("代码", "")),
                    name=str(row.get("名称", "")),
                    rank=int(idx) + 1,
                    price=float(row["最新价"]) if pd.notna(row.get("最新价")) else None,
                ))
            except Exception:
                continue
        return results
```

---

## 四、注册到 Registry

```python
# infrastructure/collectors/registry.py 中的 setup_default_registry()

def setup_default_registry() -> FetcherRegistry:
    reg = get_registry()

    # ... 原有 Tushare / Pytdx 注册 ...

    # ── ConceptFetcher ──────────────────────────────────
    # AKShareFetcher 无状态（每次调用发 HTTP 请求），适合单例
    try:
        from infrastructure.collectors.akshare import AKShareConceptFetcher
        akshare_concept = AKShareConceptFetcher()
        reg.register_instance(ConceptFetcher, akshare_concept)
        reg.register_factory(ConceptFetcher, AKShareConceptFetcher)
    except RuntimeError as e:
        # akshare 未安装时跳过，不影响主流程
        import logging
        logging.getLogger(__name__).warning(f"AKShare 未安装，概念板块采集不可用: {e}")

    return reg
```

---

## 五、使用示例

```python
# application/concept_service.py（新增）

from infrastructure.collectors.protocols import ConceptFetcher
from infrastructure.collectors.registry import get_registry


class ConceptAppService:
    def get_all_concepts(self) -> list[ConceptListResponse]:
        fetcher: ConceptFetcher = get_registry().get(ConceptFetcher)
        concepts = fetcher.fetch_concept_list()
        return [ConceptListResponse(...) for c in concepts]

    def get_concept_stocks(self, concept_name: str) -> list[ConceptStockResponse]:
        fetcher: ConceptFetcher = get_registry().get(ConceptFetcher)
        stocks = fetcher.fetch_concept_stocks(concept_name)
        return [ConceptStockResponse(...) for s in stocks]
```

---

## 六、实施前提

1. **完成 [02_refactor_plan.md](./02_refactor_plan.md) 阶段 1**：registry 和 protocols.py 已存在
2. **安装 akshare**：`pip install akshare`（加入 `requirements.txt`）
3. **数据库准备**：概念板块数据是否落库待定（可能仅透传，不落库）

---

## 七、风险与限制

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| AKShare 数据源不稳定 | 概念归因结果波动 | 作为补充，Tushare 仍是主数据源 |
| HTTP 请求延迟 | 接口响应慢 | 加超时（5s），超时降级返回空 |
| 数据格式变更 | 解析失败 | 版本锁定 + 解析异常捕获 |
| akshare 依赖缺失 | import 失败 | try/except 包裹，log warning 不抛异常 |

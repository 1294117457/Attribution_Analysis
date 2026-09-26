"""data-collector: A股数据采集微服务（FastAPI）。

负责从 tushare / akshare / eastmoney / sina / pytdx 等上游数据源拉取股票行情、财务、
概念、资金等数据，通过 HMAC 签名接口暴露给 backend-java 工程。

**当前阶段（Phase 1）**：
- 不直连数据库（仅采集 + 内存组装明细 + HTTP 返回 JSON）
- 业务侧入库仍在 backend-java 工程完成

**Phase 2 计划**：
- 引入 SQLAlchemy + pandas_ta，Python 一条龙（采集 + 入库 + 算指标）
"""

__version__ = "0.1.0"

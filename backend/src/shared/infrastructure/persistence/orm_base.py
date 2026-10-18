"""SQLAlchemy 声明基类

分两个 Base，对应两个物理库（attribution_db / raw_data_db）：
- AttribBase: 业务库（用户/角色/权限/股票池/采集元数据/采集 job）
- RawBase:   采集库（5 个面的原始数据：tech/capital/fundamental/...）
- Base:      兼容旧 import（= AttribBase），过渡期使用
"""

from sqlalchemy.orm import DeclarativeBase


class AttribBase(DeclarativeBase):
    """业务库 ORM 基类（attribution_db）

    包含：用户、角色、权限、股票池、采集元数据、采集 job
    """
    pass


class RawBase(DeclarativeBase):
    """采集库 ORM 基类（raw_data_db）

    包含：tech_* / capital_* / fundamental_* / news_* / sentiment_*
    """
    pass


# 向后兼容（旧代码 from .orm_base import Base）
Base = AttribBase

"""别名：adj_factor -> base_adj_factor（service 引用 AdjFactorDB）。"""
from models.base_adj_factor import BaseAdjFactorDB

AdjFactorDB = BaseAdjFactorDB

__all__ = ["AdjFactorDB", "BaseAdjFactorDB"]

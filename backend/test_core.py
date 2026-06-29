# test_core.py
from core import get_settings, MarketType, AnomalyType

# 测试配置
settings = get_settings()
print(f"DATABASE_URL: {settings.DATABASE_URL}")

# 测试枚举
print(f"MarketType.SH: {MarketType.SH}")
print(f"AnomalyType.PRICE_SPIKE: {AnomalyType.PRICE_SPIKE}")

print("✅ Core 模块配置成功!")
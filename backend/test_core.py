"""测试核心配置"""

from app.config import get_settings

settings = get_settings()
print(f"DATABASE_URL: {settings.DATABASE_URL}")
print(f"REDIS_URL: {settings.REDIS_URL}")
print(f"API_V1_PREFIX: {settings.API_V1_PREFIX}")
print("✅ 配置加载成功!")

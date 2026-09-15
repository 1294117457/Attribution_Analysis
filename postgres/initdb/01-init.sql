# =============================================================
# 数据库初始化脚本
# 仅在 PostgreSQL 容器首次启动时执行
# =============================================================

-- 启用常用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 输出确认
DO $$
BEGIN
    RAISE NOTICE 'Attribution database initialized at %', NOW();
END $$;

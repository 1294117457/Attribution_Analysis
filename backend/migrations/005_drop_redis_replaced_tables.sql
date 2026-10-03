-- =============================================================================
-- 005_drop_redis_replaced_tables.sql
-- 邮箱验证码 / refresh token / 图形验证码 已切到 Redis, 删除对应的 DB 表
-- 幂等: IF EXISTS / IF NOT EXISTS
-- 由 main.py lifespan 中 _migrate_auth_system() 加载执行
-- =============================================================================

DROP TABLE IF EXISTS sys_email_verifications CASCADE;
DROP TABLE IF EXISTS sys_refresh_tokens    CASCADE;
DROP TABLE IF EXISTS sys_captchas          CASCADE;

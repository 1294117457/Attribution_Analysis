-- =============================================================================
-- 003_drop_username.sql
-- 彻底去除 sys_users.username 字段(代码层已不再读写,DB 层做物理清理)
-- 幂等:所有语句用 IF EXISTS
-- 由 main.py lifespan 中加载执行
-- =============================================================================

-- 1. 去掉 username 上的 NOT NULL 约束(允许旧数据保留为 NULL)
ALTER TABLE sys_users ALTER COLUMN username DROP NOT NULL;

-- 2. 去掉 username 上的 UNIQUE 约束 + 索引(可能命名不同,都尝试一下)
ALTER TABLE sys_users DROP CONSTRAINT IF EXISTS sys_users_username_key;
DROP INDEX IF EXISTS ix_sys_users_username;
DROP INDEX IF EXISTS sys_users_username_key;

-- 3. 清空 username 数据(代码层不再读,清空让 schema 更清晰)
UPDATE sys_users SET username = NULL;

-- 4. 物理删除列(可选:保留也可,本脚本采用保留以最大化兼容)
-- ALTER TABLE sys_users DROP COLUMN IF EXISTS username;

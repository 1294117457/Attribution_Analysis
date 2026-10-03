-- =============================================================================
-- 006_add_role_perm_unique.sql
-- 修复 sys_role_permissions / sys_user_roles 缺唯一约束的问题
-- 之前 002_auth_system.sql 的 INSERT ... ON CONFLICT (role_id, permission_id)
-- 因无 UNIQUE 约束 → 失败,子句 #15/#16/#17 全部 skip
-- 现象: 角色权限未初始化,无权限用户登录后查不到任何 perm code
-- 修复: 用 ALTER TABLE ... ADD CONSTRAINT (PG 支持 IF NOT EXISTS 9.6+ via
--   pg_constraint 查重 + PG 9.5+ 触发器函数方案;为兼容老 PG,用 INFORMATION_SCHEMA
--   查重 + 动态拼接 SQL 的方式。简洁起见这里用纯 DDL:
--   - 先查 pg_constraint,不存在则 ADD CONSTRAINT
-- 由 main.py lifespan 中 _migrate_auth_system() 加载执行
-- 注意: ON CONFLICT (col) DO NOTHING 只认 unique constraint / exclusion
--   constraint,不认 UNIQUE INDEX,所以必须用 ADD CONSTRAINT
-- =============================================================================

-- 1. 清理 sys_role_permissions 重复行(只保留 id 最小的那行)
DELETE FROM sys_role_permissions a
USING sys_role_permissions b
WHERE a.role_id = b.role_id
  AND a.permission_id = b.permission_id
  AND a.id > b.id;

-- 2. 补 sys_role_permissions 唯一约束(用 ALTER TABLE)
ALTER TABLE sys_role_permissions
    ADD CONSTRAINT uq_sys_role_permissions_role_perm
    UNIQUE (role_id, permission_id);

-- 3. 清理 sys_user_roles 重复行
DELETE FROM sys_user_roles a
USING sys_user_roles b
WHERE a.user_id = b.user_id
  AND a.role_id = b.role_id
  AND a.id > b.id;

-- 4. 补 sys_user_roles 唯一约束
ALTER TABLE sys_user_roles
    ADD CONSTRAINT uq_sys_user_roles_user_role
    UNIQUE (user_id, role_id);

-- =============================================================================
-- 002_auth_system.sql
-- 登录鉴权 + RBAC 系统 6 张 sys_* 表
-- 幂等：所有语句用 IF NOT EXISTS / ON CONFLICT DO NOTHING
-- 由 main.py lifespan 中 _migrate_auth_system() 加载执行
-- =============================================================================

-- ── 1. sys_users ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sys_users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(128) NOT NULL UNIQUE,
    password_hash   VARCHAR(128) NOT NULL,
    nickname        VARCHAR(64),
    avatar_url      VARCHAR(256),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN      NOT NULL DEFAULT FALSE,
    last_login_at   TIMESTAMP,
    last_login_ip   VARCHAR(64),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sys_users_email        ON sys_users (email);
CREATE INDEX IF NOT EXISTS ix_sys_users_is_active    ON sys_users (is_active);

-- ── 2. sys_roles ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sys_roles (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(64) NOT NULL UNIQUE,
    name            VARCHAR(64) NOT NULL,
    description     TEXT,
    is_system       BOOLEAN     NOT NULL DEFAULT FALSE,
    sort_order      INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ── 3. sys_permissions ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sys_permissions (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(64) NOT NULL UNIQUE,
    resource        VARCHAR(64) NOT NULL,
    action          VARCHAR(32) NOT NULL,
    name            VARCHAR(64) NOT NULL,
    description     TEXT,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sys_permissions_resource ON sys_permissions (resource);

-- ── 4. sys_user_roles ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sys_user_roles (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES sys_users(id) ON DELETE CASCADE,
    role_id         INTEGER NOT NULL REFERENCES sys_roles(id) ON DELETE CASCADE,
    granted_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    granted_by      INTEGER REFERENCES sys_users(id) ON DELETE SET NULL,
    CONSTRAINT uq_sys_user_roles UNIQUE (user_id, role_id)
);

CREATE INDEX IF NOT EXISTS ix_sys_user_roles_user_id ON sys_user_roles (user_id);
CREATE INDEX IF NOT EXISTS ix_sys_user_roles_role_id ON sys_user_roles (role_id);

-- ── 5. sys_role_permissions ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sys_role_permissions (
    id              SERIAL PRIMARY KEY,
    role_id         INTEGER NOT NULL REFERENCES sys_roles(id) ON DELETE CASCADE,
    permission_id   INTEGER NOT NULL REFERENCES sys_permissions(id) ON DELETE CASCADE,
    CONSTRAINT uq_sys_role_permissions UNIQUE (role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS ix_sys_role_permissions_role_id       ON sys_role_permissions (role_id);
CREATE INDEX IF NOT EXISTS ix_sys_role_permissions_permission_id ON sys_role_permissions (permission_id);

-- 内置角色
INSERT INTO sys_roles (code, name, description, is_system, sort_order) VALUES
    ('admin',  '管理员',   '系统管理员,拥有全部权限',                TRUE,  10),
    ('member', '正式会员', '注册即获得,拥有常用数据的查看和操作权限',  FALSE, 20),
    ('viewer', '只读访客', '仅可查看大盘与公开数据',                  FALSE, 30)
ON CONFLICT (code) DO NOTHING;

-- 内置权限 (14 核心 + user:delete + role:delete = 16)
INSERT INTO sys_permissions (code, resource, action, name, description) VALUES
    -- 股票
    ('stock:read',       'stock', 'read',       '查看股票',           '查看股票基础信息'),
    ('stock:write',      'stock', 'write',      '编辑股票',       '创建/更新/删除股票'),
    -- K 线
    ('kline:read',       'kline', 'read',       '查看 K 线',           '查看 K 线与技术指标'),
    ('kline:write',      'kline', 'write',      '采集 K 线',         '触发 K 线采集与重算'),
    -- 操作池
    ('pool:read',        'pool',  'read',       '查看操作池',         '查看操作池与池内股票'),
    ('pool:write',       'pool',  'write',      '管理操作池',         '创建/编辑/删除操作池'),
    -- 采集管理
    ('collect:read',     'collect', 'read',     '查看采集任务',     '查看采集任务与计划'),
    ('collect:write',    'collect', 'write',    '管理采集任务',     '触发/调度采集任务'),
    -- 概念
    ('concept:read',     'concept', 'read',     '查看概念',           '查看概念板块/行情'),
    -- 板块
    ('sector:read',      'sector', 'read',      '查看板块行情',     '查看板块行情'),
    -- 账户(本模块新增)
    ('user:read',        'user',   'read',      '查看用户',           '查看用户列表/详情'),
    ('user:write',       'user',   'write',     '管理用户',           '启用/禁用/重置密码/分配角色'),
    ('user:delete',      'user',   'delete',    '删除用户',     '物理删除用户'),
    -- 角色与权限
    ('role:read',        'role',   'read',      '查看角色',           '查看角色与权限列表'),
    ('role:write',       'role',   'write',     '管理角色',           '编辑角色与权限绑定'),
    ('role:delete',      'role',   'delete',    '删除角色',     '删除自定义角色')
ON CONFLICT (code) DO NOTHING;

-- 角色-权限绑定
-- admin：全部 16 个
INSERT INTO sys_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM   sys_roles r, sys_permissions p
WHERE  r.code = 'admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- member：常用 6 个
INSERT INTO sys_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM   sys_roles r, sys_permissions p
WHERE  r.code = 'member'
       AND p.code IN (
            'stock:read', 'kline:read', 'kline:write',
            'pool:read', 'pool:write', 'collect:read'
       )
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- viewer：只读 4 个
INSERT INTO sys_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM   sys_roles r, sys_permissions p
WHERE  r.code = 'viewer'
       AND p.code IN (
            'stock:read', 'kline:read', 'pool:read', 'concept:read'
       )
ON CONFLICT (role_id, permission_id) DO NOTHING;
--
-- PR1 / D0 命名重整：表 RENAME
-- 执行：psql -U zhouch -d attribution_db -f scripts/migrate_d0_rename_tables.sql
--
-- 范围：仅改表名，列名 / 索引 / 约束 / 外键 一律不动
-- 风险：低（pure rename，原子）
--

BEGIN;

-- 1) 采集接口元数据：mirror → 事实来源
ALTER TABLE IF EXISTS collect_fetchers RENAME TO sys_data_ports;

-- 2) 采集执行实例：task → job
ALTER TABLE IF EXISTS sys_collect_tasks RENAME TO sys_collect_jobs;

-- 3) 重命名 collect_plan_items 上的外键引用（表名变了，FK 必须指向新表）
--    PostgreSQL 会自动随父表改名而更新 FK；但跨 rename 链路下保险起见，显式重建
DO $$
DECLARE
    fk_rec RECORD;
BEGIN
    FOR fk_rec IN
        SELECT conname, conrelid::regclass AS tbl
        FROM pg_constraint
        WHERE contype = 'f'
          AND pg_get_constraintdef(oid) LIKE '%collect_fetchers%'
    LOOP
        EXECUTE format(
            'ALTER TABLE %s RENAME CONSTRAINT %I TO %I',
            fk_rec.tbl, fk_rec.conname,
            replace(fk_rec.conname, 'collect_fetchers', 'sys_data_ports')
        );
    END LOOP;
END $$;

-- 4) 验证
SELECT
    'sys_data_ports'   AS expected,
    COUNT(*) AS actual_rows
FROM sys_data_ports
UNION ALL
SELECT
    'sys_collect_jobs' AS expected,
    COUNT(*) AS actual_rows
FROM sys_collect_jobs;

COMMIT;

\echo
\echo '=== 迁移完成 ==='
\echo '改名前后：'
\echo '  collect_fetchers  → sys_data_ports    (元数据)'
\echo '  sys_collect_tasks → sys_collect_jobs  (执行实例)'
\echo
\echo '验证：'
\echo '  SELECT tablename FROM pg_tables WHERE tablename IN (''sys_data_ports'', ''sys_collect_jobs'');'

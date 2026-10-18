--
-- PR1 + PR2 / D0 + D1 迁移脚本
-- 执行：psql -U zhouch -d attribution_db -f scripts/migrate_d0_d1.sql
--
-- 范围：
--   1) D0 表 RENAME：collect_fetchers → sys_data_ports，sys_collect_tasks → sys_collect_jobs
--   2) D1 sys_data_ports 字段精简：
--      删 description / sub_facet / default_params / supports_run_one
--      加 params_schema / upsert_mode / facet
--   3) D1 sys_data_ports 加 facet 索引
--   4) 同步：collect_plan_items 外键指向新表名（自动）
--
-- 风险：低（PG 改表名 / 改列名 / 加列 / 删列都是原子）
-- 字段名 task_type 保留（D0 §0.1 明确不动）
--

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- 1) D0 表 RENAME
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE IF EXISTS collect_fetchers RENAME TO sys_data_ports;
ALTER TABLE IF EXISTS sys_collect_tasks RENAME TO sys_collect_jobs;

-- 索引名跟随 PG 自动改名（如果之前用了 pg 默认命名 ix_<col>，会自动改）
-- 老索引 ix_sys_collect_tasks_* 已被 PG 自动改为 ix_sys_collect_jobs_*

-- collect_plan_items 上的外键自动跟随（PG 会同步更新 FK 引用）；
-- 保险起见显式重建约束名
DO $$
DECLARE
    fk_rec RECORD;
BEGIN
    FOR fk_rec IN
        SELECT conname, conrelid::regclass AS tbl
        FROM pg_constraint
        WHERE contype = 'f'
          AND (pg_get_constraintdef(oid) LIKE '%collect_fetchers%'
               OR pg_get_constraintdef(oid) LIKE '%sys_collect_tasks%')
    LOOP
        EXECUTE format(
            'ALTER TABLE %s RENAME CONSTRAINT %I TO %I',
            fk_rec.tbl, fk_rec.conname,
            replace(replace(fk_rec.conname,
                            'collect_fetchers', 'sys_data_ports'),
                            'sys_collect_tasks', 'sys_collect_jobs')
        );
    END LOOP;
END $$;

-- 序列：sys_collect_jobs_id_seq
-- PG 序列命名是 hardcoded（不随表 rename），需要手动改
DO $$
DECLARE
    seq_rec RECORD;
BEGIN
    FOR seq_rec IN
        SELECT c.relname AS seq_name
        FROM pg_class c
        WHERE c.relkind = 'S'
          AND c.relname LIKE 'sys_collect_tasks_%'
    LOOP
        EXECUTE format('ALTER SEQUENCE %I RENAME TO %I',
                       seq_rec.seq_name,
                       replace(seq_rec.seq_name, 'sys_collect_tasks', 'sys_collect_jobs'));
    END LOOP;
END $$;


-- ═══════════════════════════════════════════════════════════════════════════
-- 2) D1 sys_data_ports：删 4 字段
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE sys_data_ports
    DROP COLUMN IF EXISTS description,
    DROP COLUMN IF EXISTS sub_facet,
    DROP COLUMN IF EXISTS default_params,
    DROP COLUMN IF EXISTS supports_run_one;


-- ═══════════════════════════════════════════════════════════════════════════
-- 3) D1 sys_data_ports：加 3 字段
-- ═══════════════════════════════════════════════════════════════════════════

-- 3.1 facet（5 个面：tech / capital / fundamental / news / sentiment）
ALTER TABLE sys_data_ports
    ADD COLUMN IF NOT EXISTS facet VARCHAR(16) NOT NULL DEFAULT 'fundamental';

-- 3.2 params_schema（入参 JSON Schema）
ALTER TABLE sys_data_ports
    ADD COLUMN IF NOT EXISTS params_schema JSON NOT NULL DEFAULT '{}'::json;

-- 3.3 upsert_mode（入库策略）
ALTER TABLE sys_data_ports
    ADD COLUMN IF NOT EXISTS upsert_mode VARCHAR(16) NOT NULL DEFAULT 'by_unique';


-- ═══════════════════════════════════════════════════════════════════════════
-- 4) facet 索引
-- ═══════════════════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS ix_sys_data_ports_facet ON sys_data_ports (facet);
CREATE INDEX IF NOT EXISTS ix_sys_data_ports_kind ON sys_data_ports (kind);


-- ═══════════════════════════════════════════════════════════════════════════
-- 5) facet 字段数据回填（14 个 port，按任务名映射）
--    见 docs/backend-docs/dev/step6/03采集优化/02-配置表升级.md §5
-- ═══════════════════════════════════════════════════════════════════════════

UPDATE sys_data_ports SET facet = 'tech'        WHERE task_type IN ('adj_factor', 'name_change', 'suspend');
UPDATE sys_data_ports SET facet = 'capital'     WHERE task_type IN (
    'moneyflow', 'margin_detail', 'margin', 'top_list', 'top_inst',
    'block_trade', 'holder_number'
);
UPDATE sys_data_ports SET facet = 'fundamental' WHERE task_type IN (
    'daily_basic', 'fin_income', 'top10_holders', 'top10_floatholders',
    'dividend', 'index_member', 'sector_daily', 'market_daily', 'stock_basic'
);

-- 5.1 params_schema 默认值：给现有 batch 端口填一个最小可用的 schema
--     （含 trade_date 字段，与 step5 旧 default_params 行为兼容）
UPDATE sys_data_ports
SET params_schema = jsonb_build_object(
    'type', 'object',
    'properties', jsonb_build_object(
        'trade_date', jsonb_build_object('type', 'string', 'pattern', '^\\d{8}$')
    ),
    'required', jsonb_build_array('trade_date')
)::json
WHERE kind = 'batch' AND (params_schema IS NULL OR params_schema::text = '{}');

-- 5.2 upsert_mode 默认 by_unique（前面 DEFAULT 已处理，这里显式一次避免漏迁移）
UPDATE sys_data_ports
SET upsert_mode = 'by_unique'
WHERE upsert_mode IS NULL OR upsert_mode = '';


-- ═══════════════════════════════════════════════════════════════════════════
-- 6) 验证
-- ═══════════════════════════════════════════════════════════════════════════

\echo
\echo '=== sys_data_ports 表 ==='
SELECT
    task_type, label, kind, status, facet, upsert_mode,
    (params_schema IS NOT NULL) AS has_params_schema
FROM sys_data_ports
ORDER BY facet, task_type
LIMIT 20;

\echo
\echo '=== sys_collect_jobs 表 ==='
SELECT
    (SELECT COUNT(*) FROM sys_collect_jobs) AS job_count,
    (SELECT COUNT(*) FROM sys_data_ports) AS port_count;

\echo
\echo '=== facet 分布 ==='
SELECT facet, COUNT(*) AS n
FROM sys_data_ports
GROUP BY facet
ORDER BY facet;

COMMIT;

\echo
\echo '=== 迁移完成 ==='
\echo 'D0：'
\echo '  collect_fetchers  → sys_data_ports    (元数据)'
\echo '  sys_collect_tasks → sys_collect_jobs  (执行实例)'
\echo
\echo 'D1 sys_data_ports 字段变更：'
\echo '  删: description / sub_facet / default_params / supports_run_one'
\echo '  加: facet / params_schema / upsert_mode'
\echo
\echo '应用启动后请检查 /collect/catalog 接口'

--
-- S4b: 校验脚本 —— attribution.collect_logs 结构与数据核对（只读）
--
-- 执行：psql -h 8.148.204.54 -U zhouch -d attribution -f 04-verify-attribution.sql
--

\echo '════════ ① collect_logs 列数（期望 29）════════'
SELECT count(*) AS col_count
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'collect_logs';

\echo '════════ ② collect_logs 全部列清单（期望 29 行）════════'
SELECT ordinal_position AS pos, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'collect_logs'
ORDER BY ordinal_position;

\echo '════════ ③ CHECK 约束（期望 6 个：5 个业务 + 1 个主键）════════'
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.collect_logs'::regclass
ORDER BY conname;

\echo '════════ ④ 索引（期望 5 个业务索引 + 主键索引）════════'
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'collect_logs'
ORDER BY indexname;

\echo '════════ ⑤ 归档表与单数表（期望 2 张：collect_logs + collect_logs_legacy_20261029；collect_log 单数表已删）════════'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('collect_log', 'collect_logs', 'collect_logs_legacy_20261029')
ORDER BY 1;

\echo '════════ ⑥ 数据行数（期望 51 = 50 旧 + 1 单数表）════════'
SELECT count(*) AS rows FROM collect_logs;

\echo '════════ ⑦ 按 kind / status 分布（应为空串 kind = 0）════════'
SELECT kind, status, count(*) AS cnt
FROM collect_logs
GROUP BY 1, 2
ORDER BY 1, 2;

\echo '════════ ⑧ facet 分布（应只用五数据面）════════'
SELECT facet, count(*) AS cnt
FROM collect_logs
GROUP BY 1
ORDER BY 1;

\echo '════════ ⑨ 列值域检查（应全部返回 0 行）════════'
SELECT 'bad_status' AS chk, task_id FROM collect_logs
 WHERE status NOT IN ('queued','running','done','failed','cancelled')
UNION ALL
SELECT 'bad_trigger_source', task_id FROM collect_logs
 WHERE trigger_source NOT IN ('manual','schedule','api','retry')
UNION ALL
SELECT 'negative_counters', task_id FROM collect_logs
 WHERE total < 0 OR done < 0 OR success < 0 OR fail < 0 OR skip < 0 OR saved_total < 0
UNION ALL
SELECT 'done_gt_total', task_id FROM collect_logs
 WHERE total <> 0 AND done > total;

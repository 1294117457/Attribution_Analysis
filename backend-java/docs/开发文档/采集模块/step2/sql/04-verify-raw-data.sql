--
-- S4: 校验脚本 —— 两库结构核对（只读，可反复执行）
--
-- 执行：
--   psql -h 8.148.204.54 -U zhouch -d raw_data    -f 04-verify-raw-data.sql
--   psql -h 8.148.204.54 -U zhouch -d attribution -f 04-verify-attribution.sql
--

\echo '════════ ① 10 张表名核对（期望 10 行全部存在）════════'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'tech_daily', 'tech_trade_cal', 'tech_suspend_d', 'tech_namechange',
      'fundamental_stock_basic', 'fundamental_income', 'fundamental_top10_holders',
      'fundamental_top10_floatholders', 'capital_stk_holdernumber', 'capital_limit_list_d'
  )
ORDER BY 1;

\echo '════════ ② 时间列类型（期望 bad_ts_cols = 0）════════'
SELECT count(*) AS bad_ts_cols
FROM information_schema.columns
WHERE table_schema = 'public'
  AND data_type = 'timestamp without time zone'
  AND column_name IN ('created_at', 'updated_at', 'started_at', 'finished_at',
                       'synced_at', 'added_at', 'granted_at');

\echo '════════ ③ 补齐的列（期望各 1 行）════════'
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (table_name, column_name) IN (
      ('fundamental_stock_basic', 'total_shares'),
      ('capital_hsgt_top10',        'holding_days'),
      ('capital_hsgt_top10',        'share_ratio'),
      ('capital_hsgt_top10',        'hold_amount'),
      ('capital_moneyflow_hsgt',    'exchange'),
      ('capital_moneyflow_hsgt',    'buy_amount'),
      ('capital_moneyflow_hsgt',    'sell_amount'),
      ('capital_limit_list_d',      'close_price'),
      ('capital_limit_list_d',      'change_rate'),
      ('capital_limit_list_d',      'board_count'),
      ('capital_limit_list_d',      'first_limit_time'),
      ('capital_limit_list_d',      'board_strength'),
      ('capital_limit_list_d',      'reason')
  )
ORDER BY table_name, column_name;

\echo '════════ ④ 新建的表（期望 1 行）════════'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'fundamental_market_daily';

\echo '════════ ⑤ 关键表行数（数据未被破坏）════════'
SELECT 'tech_daily' AS t, count(*) FROM tech_daily
UNION ALL SELECT 'fundamental_stock_basic', count(*) FROM fundamental_stock_basic
UNION ALL SELECT 'tech_adj_factor', count(*) FROM tech_adj_factor;

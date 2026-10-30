--
-- S1: raw_data 库 —— 时间列类型对齐（timestamp without time zone → timestamptz）
--
-- 背景：
--   本地 ORM（collector-python/src/models/*.py）用 DateTime(timezone=True) = timestamptz，
--   而远端库的审计时间列全是 timestamp without time zone。
--   asyncpg 往 naive 列写 aware datetime 会直接抛 DataError
--   （can't subtract offset-naive and offset-aware datetimes）→ 所有带 TimestampMixin 的 INSERT 全挂。
--
-- ⚠️ 时区语义（关键）：
--   远端库 SET timezone = 'Asia/Shanghai'（见 postgres/initdb/01-init.sql），
--   现有 naive 值本身就是「上海本地时间」。
--   → 必须用 AT TIME ZONE 'Asia/Shanghai'（把本地时间解释为上海时区，转成 UTC 存储）。
--   → 若误用 'UTC'，整体偏移 8 小时，所有历史数据时间全错。
--
-- 执行：psql -h 8.148.204.54 -U zhouch -d raw_data -f 01-timezone-columns.sql
-- 可逆：把 timestamptz 改回 timestamp 再 AT TIME ZONE 'Asia/Shanghai' 即可还原。
--

BEGIN;

DO $$
DECLARE
    r RECORD;
    n INT := 0;
BEGIN
    FOR r IN
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.data_type = 'timestamp without time zone'
          AND c.column_name IN ('created_at', 'updated_at', 'started_at', 'finished_at',
                                'synced_at', 'added_at', 'granted_at')
        ORDER BY c.table_name, c.column_name
    LOOP
        EXECUTE format(
            'ALTER TABLE public.%I ALTER COLUMN %I TYPE timestamptz USING %I AT TIME ZONE ''Asia/Shanghai''',
            r.table_name, r.column_name, r.column_name);
        n := n + 1;
        RAISE NOTICE 'ALTER % -> timestamptz', r.table_name || '.' || r.column_name;
    END LOOP;
    RAISE NOTICE '共处理 % 个时间列', n;
END $$;

COMMIT;

-- 校验：期望 0
-- SELECT count(*) FROM information_schema.columns
--  WHERE table_schema='public' AND data_type='timestamp without time zone'
--    AND column_name IN ('created_at','updated_at');

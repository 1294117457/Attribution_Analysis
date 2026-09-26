import psycopg2
c = psycopg2.connect(host='8.148.204.54',port=5432,user='zhouch',password='zhouchenhui',dbname='attribution')
cur = c.cursor()

# stock_pool_members 全部
print('=== stock_pool_members ===')
cur.execute("""
    SELECT m.symbol, m.pool_id, m.memo, p.name AS pool_name, p.pool_type
    FROM stock_pool_members m
    JOIN stock_pools p ON p.id = m.pool_id
""")
for r in cur.fetchall():
    print(r)

# 看一下 stock_infos 里 603459 存在吗
print('\n=== stock_infos WHERE symbol IN panel 默认的 list ===')
cur.execute("SELECT symbol, name FROM stock_infos WHERE symbol='603459'")
print(cur.fetchone())

# 测试 panel 是否应该返回 603459
cur.execute("SELECT symbol FROM stock_infos WHERE list_status='L' ORDER BY symbol LIMIT 30")
rows = cur.fetchall()
print('\n=== 前 30 个上市股票 ===')
for r in rows[:5]:
    print(r)

# 验证 fin_daily_basics 9-18 当天
print('\n=== fin_daily_basics 9-18 ===')
cur.execute("SELECT COUNT(*) FROM fin_daily_basics WHERE trade_date='2026-09-18'")
print(cur.fetchone())

# 603459 当天是否有
print('\n=== fin_daily_basics WHERE symbol=603459 AND trade_date=2026-09-18 ===')
cur.execute("SELECT symbol, trade_date, pe, pe_ttm, total_mv FROM fin_daily_basics WHERE symbol='603459' ORDER BY trade_date DESC LIMIT 5")
for r in cur.fetchall():
    print(r)
c.close()

import psycopg2
c = psycopg2.connect(host='8.148.204.54',port=5432,user='zhouch',password='zhouchenhui',dbname='attribution')
cur = c.cursor()

# 1. fin_daily_basics 有没有数据
print('=== fin_daily_basics 总数 ===')
cur.execute("SELECT COUNT(*) FROM fin_daily_basics")
print(cur.fetchone())

print('\n=== fin_daily_basics 样本 (前 3 条) ===')
cur.execute("SELECT symbol, trade_date, pe, pe_ttm, total_mv, circ_mv FROM fin_daily_basics LIMIT 3")
for r in cur.fetchall():
    print(r)

print('\n=== stock_pool_members 总数 ===')
cur.execute("SELECT COUNT(*) FROM stock_pool_members")
print(cur.fetchone())

print('\n=== stock_pools 全部 ===')
cur.execute("SELECT id, name, pool_type FROM stock_pools")
for r in cur.fetchall():
    print(r)

print('\n=== concept_members 总数 ===')
cur.execute("SELECT COUNT(*) FROM concept_members")
print(cur.fetchone())

print('\n=== concepts 全部 ===')
cur.execute("SELECT id, name, source, stock_count FROM concepts")
for r in cur.fetchall():
    print(r)

print('\n=== tech_kline_dailys 总数 + 样本 ===')
cur.execute("SELECT COUNT(*) FROM tech_kline_dailys")
print(cur.fetchone())
cur.execute("SELECT symbol, date, close FROM tech_kline_dailys WHERE symbol='603459' ORDER BY date DESC LIMIT 5")
for r in cur.fetchall():
    print(r)
c.close()

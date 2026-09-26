import psycopg2
c = psycopg2.connect(host='8.148.204.54',port=5432,user='zhouch',password='zhouchenhui',dbname='attribution')
cur = c.cursor()

# 看 stock_pool_members 表的 pools 列表，看有没有 688981
print('=== stock_pool_members 中是否有 688xxx 系列 ===')
cur.execute("SELECT m.symbol, m.pool_id, p.name FROM stock_pool_members m JOIN stock_pools p ON p.id=m.pool_id WHERE m.symbol LIKE '688%' LIMIT 20")
for r in cur.fetchall():
    print(r)
print()
print('总数:', cur.execute("SELECT COUNT(*) FROM stock_pool_members WHERE symbol LIKE '688%'"), 'rows')

c.close()


import psycopg2
c = psycopg2.connect(host='8.148.204.54',port=5432,user='zhouch',password='zhouchenhui',dbname='attribution')
cur = c.cursor()
# fin_reports 字段清单
print('=== fin_reports 列 ===')
cur.execute("""
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name='fin_reports' ORDER BY ordinal_position""")
for r in cur.fetchall():
    print(r)
print()

# 是否有任何含 'profit' / 'margin' 的列
print('=== 包含 profit/margin 关键词的表 ===')
cur.execute("""
SELECT table_name, column_name, data_type FROM information_schema.columns
WHERE table_schema='public' AND (column_name LIKE '%profit%' OR column_name LIKE '%margin%')""")
for r in cur.fetchall():
    print(r)
print()

# fin_daily_basics 字段
print('=== fin_daily_basics 列 ===')
cur.execute("""
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name='fin_daily_basics' ORDER BY ordinal_position""")
for r in cur.fetchall():
    print(r)

c.close()

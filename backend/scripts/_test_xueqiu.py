"""深挖雪球免登录的板块/概念接口"""
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'https://xueqiu.com/',
    'Origin': 'https://xueqiu.com',
}


def safe(name, url, params=None, headers=None):
    try:
        r = requests.get(url, params=params or {}, headers=headers or HEADERS, timeout=8)
        body = r.text[:400]
        print(f'\n{name}: {r.status_code}')
        print(f'  body: {body}')
    except Exception as e:
        print(f'\n{name}: ERR {type(e).__name__} {str(e)[:100]}')


# 雪球行业接口（HS 行业）
print('=== 雪球 v5 industry ===')
safe('xq_industry_all', 'https://stock.xueqiu.com/v5/stock/industry/list.json',
     {'type': 'industry', 'source': 'xueqiu', 'page_size': 5, 'page': 1})

safe('xq_industry_concept', 'https://stock.xueqiu.com/v5/stock/industry/list.json',
     {'type': 'concept', 'source': 'xueqiu', 'page_size': 5, 'page': 1})

# 雪球 sectors
print('\n=== 雪球 v5 sectors ===')
safe('xq_sectors', 'https://stock.xueqiu.com/v5/stock/sector/list.json',
     {'type': 'concept', 'order_by': 'code', 'order': 'desc', 'page_size': 5, 'page': 1})

safe('xq_sectors_industry', 'https://stock.xueqiu.com/v5/stock/sector/list.json',
     {'type': 'industry', 'order_by': 'code', 'order': 'desc', 'page_size': 5, 'page': 1})

# 雪球 quotes / 排行
print('\n=== 雪球 quote ===')
safe('xq_quote_rank', 'https://stock.xueqiu.com/v5/stock/screener/quote/list.json',
     {'type': 'sh_sz', 'order_by': 'percent', 'order': 'desc', 'page': 1, 'size': 5})

# 雪球 v4 老接口（可能免登录）
print('\n=== 雪球 v4 ===')
safe('xq_v4_concept', 'https://xueqiu.com/v4/stock/industry/list.json',
     {'type': 'concept', 'size': 5, 'page': 1})

safe('xq_v4_sectors', 'https://xueqiu.com/v4/stock/sectors.json',
     {'market': 'cn', 'type': 'concept'})

# 同花顺数据接口
print('\n=== 同花顺 data.10jqka ===')
safe('ths_industry', 'http://data.10jqka.com.cn/api/finance/stock/industry/getIndustry',
     {'type': 'concept', 'count': 5})

safe('ths_block_data', 'http://data.10jqka.com.cn/dataapi/limit_up/block_concept',
     {'date': '2026-09-26', 'order': 'desc'})

# akshare 备用：ths_data_source
print('\n=== akshare 同花顺接口（wind/ths 数据）===')
# 不直接调用 akshare，看 akshare 自己用的 URL

"""验证哪些数据源能拿到概念清单"""
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'https://vip.stock.finance.sina.com.cn/',
}


def safe(name, url, params=None):
    try:
        r = requests.get(url, params=params or {}, headers=HEADERS, timeout=8)
        body = r.text[:300]
        print(f'{name}: {r.status_code} | {body}')
    except Exception as e:
        print(f'{name}: ERR {type(e).__name__} {str(e)[:80]}')


# 1) 新浪 - 概念板块节点枚举
print('=== 新浪 vip.stock.finance.sina ===')
for n in ['gn_3000', 'gn_hs300', 'gn_sz50', 'gn_sme300']:
    safe(f'sina:{n}',
         'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData',
         {'node': n, 'num': 5, 'sort': 'changepercent', 'asc': '0', 'page': '1'})

# 2) 新浪 - 概念指数成份股
print('\n=== 新浪 指数 / 成分股 ===')
safe('sina_index_gn',
     'http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData',
     {'node': 'gn_3000', 'num': 5, 'sort': 'changepercent', 'asc': '0', 'page': '1'})

# 3) 腾讯 - 概念列表
print('\n=== 腾讯 web.ifzq.gtimg ===')
safe('qq_kl_concept',
     'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get',
     {'param': 'conceptionNumber,conceptionName,conceptionStock', 'type': 'concept'})

safe('qq_app_concept',
     'https://web.ifzq.gtimg.cn/appstock/app/MarketLayoutData.getLayoutData',
     {'marketType': 'concept', 'pageSize': 10})

safe('qq_concept_list',
     'https://proxy.finance.qq.com/ifzq/gtimg/appstock/app/MarketLayoutData.getLayoutData',
     {'marketType': 'concept', 'pageSize': 10})

safe('qq_industry_concept',
     'https://stock.gtimg.cn/data/index.php?appn=rank&t=ranka/chr&p=1&o=0&l=10',
     {})

# 4) 新浪 - 板块列表（行业 vs 概念）
print('\n=== 新浪 板块列表 ===')
safe('sina_blocks',
     'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getBlocks?type=concept',
     {})

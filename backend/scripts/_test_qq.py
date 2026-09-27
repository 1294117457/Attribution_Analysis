"""深挖腾讯 + 备用"""
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36',
    'Referer': 'https://gu.qq.com/',
}


def safe(name, url, params=None, headers=None):
    try:
        r = requests.get(url, params=params or {}, headers=headers or HEADERS, timeout=8)
        body = r.text[:500]
        print(f'\n{name}: {r.status_code}')
        print(f'  body: {body}')
    except Exception as e:
        print(f'\n{name}: ERR {type(e).__name__} {str(e)[:100]}')


# 腾讯 - 行业 / 概念
print('=== 腾讯 web.ifzq ===')
safe('qq_concept', 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get',
     {'param': 'concept,constituents,conceptName,conceptCode'})
safe('qq_concept_v2', 'https://web.ifzq.gtimg.cn/appstock/app/finance/conceptList',
     {'page': 1, 'pagesize': 5})
safe('qq_industry', 'https://web.ifzq.gtimg.cn/appstock/app/finance/industryList',
     {'page': 1, 'pagesize': 5})
safe('qq_classify', 'https://web.ifzq.gtimg.cn/appstock/app/MarketLayoutData.getLayoutData',
     {'marketType': 'concept', 'pageSize': 5, 'page': 1})

# 腾讯 - finance.qq.com
print('\n=== 腾讯 finance.qq ===')
safe('qq_finance_concept', 'https://finance.qq.com/cgi-bin/webtrade/get_stock_concept',
     {'page': 1, 'pagesize': 5})
safe('qq_cgi_block', 'https://stock.gtimg.cn/data/index.php?appn=industry&t=industry/zh/chr&p=1&o=0&l=5',
     {})

# stock.gtimg.cn - 板块行情
print('\n=== stock.gtimg ===')
safe('gtimg_kcb', 'https://stock.gtimg.cn/data/index.php?appn=rank&t=ranka/chr&p=1&o=0&l=5', {})
safe('gtimg_concept', 'https://stock.gtimg.cn/data/index.php?appn=rank&t=ranka/cgs&p=1&o=0&l=5', {})

# 东方财富 web 站点（不是 API）
print('\n=== 东方财富 web ===')
safe('em_web_quote', 'https://quote.eastmoney.com/center/boardlist.html',
     {})
safe('em_quote_page', 'https://data.eastmoney.com/bkzj/hy.html',
     {})

# 同花顺 iwencai
print('\n=== 同花顺 问财 ===')
safe('iwc', 'http://www.iwencai.com/unifiedwap/unified-wap/result/get-stock-list',
     {'query': '所有概念板块', 'page': 1, 'per_page': 5})

# akshare 内部其他 fetcher（同花顺）
print('\n=== akshare 同花顺 fetcher URL ===')
# 看 akshare 用的同花顺 / iFinD / wind 等源

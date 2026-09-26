import urllib.request, json

# 测试 KlineVO 是否返回 snake_case
url='http://localhost:8000/api/v1/klines/688981?limit=2&order_desc=true'
try:
    r = urllib.request.urlopen(url, timeout=5)
    d = json.loads(r.read())
    items = d.get('data') or []
    if items and 'change_pct' in items[0]:
        print('OK KlineVO 已返回 snake_case')
    elif items:
        print('!! KlineVO 返回的不是 snake_case')
        print('字段:', list(items[0].keys())[:15])
except Exception as e:
    print('ERR:', e)

# 测试 panel 是否优先 fin_daily_basics
url='http://localhost:8000/api/v1/stock-panel/?page=1&page_size=2&with_pools=true&with_concepts=true&list_status=L'
try:
    r = urllib.request.urlopen(url, timeout=8)
    d = json.loads(r.read())
    body = d.get('data') or {}
    items = body.get('items') or []
    print('panel trade_date:', body.get('trade_date'))
    if items:
        first = items[0]
        print('first.symbol:', first.get('symbol'))
        print('first.pe_ttm:', first.get('pe_ttm'))
        print('first.total_mv:', first.get('total_mv'))
        print('first.pools:', first.get('pools'))
        print('first.concepts:', first.get('concepts'))
        if first.get('pe_ttm') is not None:
            print('OK panel 有估值')
        else:
            print('!! panel 估值仍空')
except Exception as e:
    print('ERR:', e)

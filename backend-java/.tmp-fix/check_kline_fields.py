import urllib.request, json

# 模拟前端调用
url = "http://localhost:8000/api/v1/klines/688981?limit=5&order_desc=true"
r = urllib.request.urlopen(url, timeout=5)
d = json.loads(r.read())
items = d.get('data') or []
print('count:', len(items))
if items:
    first = items[0]
    print('keys:', sorted(first.keys()))
    # 验证 Locator Chart 用到的字段都齐全
    needed = ['date', 'open', 'high', 'low', 'close', 'volume', 'change_pct',
              'ma5', 'ma10', 'ma20', 'ma60', 'ema12', 'ema26',
              'macd_dif', 'macd_dea', 'macd_bar',
              'rsi6', 'rsi12', 'rsi24',
              'kdj_k', 'kdj_d', 'kdj_j',
              'boll_up', 'boll_mid', 'boll_dn']
    missing = [k for k in needed if k not in first]
    print('缺失字段:', missing if missing else '✓ 全有')
    print('date:', first['date'], 'close:', first['close'])

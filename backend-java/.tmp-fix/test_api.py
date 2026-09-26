import urllib.request
import json

# 测试 K 线接口
for p in [8000, 8080]:
    print(f'\n===== 试端口 {p} =====')
    url = f"http://localhost:{p}/api/v1/klines/603459?limit=2&order_desc=true"
    print(f'GET {url}')
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode('utf-8')
            data = json.loads(body)
            print(f'\n=== code: {data.get("code")}, msg: {data.get("msg")} ===')
            items = data.get('data') or []
            if isinstance(items, list) and items:
                print(f'共 {len(items)} 条，第一条字段:')
                first = items[0]
                for k, v in first.items():
                    print(f'  {k}: {v}')
        break
    except Exception as e:
        print(f'ERR: {e}')

print()
for p in [8000, 8080]:
    print(f'\n===== 试端口 {p} =====')
    url2 = f"http://localhost:{p}/api/v1/minute-klines/603459?interval=5min&count=2"
    print(f'GET {url2}')
    try:
        with urllib.request.urlopen(url2, timeout=8) as resp:
            body = resp.read().decode('utf-8')
            data = json.loads(body)
            print(f'\n=== code: {data.get("code")}, msg: {data.get("msg")} ===')
            items = (data.get('data') or {}).get('items', [])
            if items:
                print(f'共 {len(items)} 条，第一条字段:')
                for k, v in items[0].items():
                    print(f'  {k}: {v}')
            else:
                print(f'items 为空')
        break
    except Exception as e:
        print(f'ERR: {e}')

print()
for p in [8000, 8080]:
    print(f'\n===== 试端口 {p} =====')
    url3 = f"http://localhost:{p}/api/v1/stock-panel/?page=1&page_size=2&with_pools=true&with_concepts=true&list_status=L"
    print(f'GET {url3}')
    try:
        with urllib.request.urlopen(url3, timeout=8) as resp:
            body = resp.read().decode('utf-8')
            data = json.loads(body)
            print(f'\n=== code: {data.get("code")}, msg: {data.get("msg")} ===')
            items = (data.get('data') or {}).get('items', [])
            if items:
                print(f'共 {len(items)} 条，第一条字段:')
                for k, v in items[0].items():
                    print(f'  {k}: {v}')
            else:
                print(f'items 为空')
        break
    except Exception as e:
        print(f'ERR: {e}')

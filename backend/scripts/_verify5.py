import urllib.request, json

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")

# 测试更精确的过滤
for url in [
    "http://127.0.0.1:8000/api/v1/stock-panel/?with_concepts=true&limit=3",
    "http://127.0.0.1:8000/api/v1/stock-panel/?with_concepts=true&limit=3&q=平安",
    "http://127.0.0.1:8000/api/v1/stock-panel/?with_concepts=true&symbol=000001",
    "http://127.0.0.1:8000/api/v1/stock-panel/?with_concepts=true&symbol=000002",
    "http://127.0.0.1:8000/api/v1/stock-panel/?with_concepts=true&symbols=000001,000002",
]:
    code, body = get(url)
    try:
        data = json.loads(body).get("data", {})
        items = data.get("items", [])
        print(f"  url={url[:80]}")
        for row in items[:3]:
            cs = row.get("concepts") or []
            print(f"    {row.get('symbol')} {row.get('name')}  concepts={len(cs)}")
            for c in cs[:2]:
                snap = c.get("snapshot") or {}
                print(f"      - {c.get('name')[:20]} pct={snap.get('pct_change')} rank={snap.get('rank_label')}")
    except Exception as e:
        print(f"  url={url[:80]}  err={e} raw={body[:200]}")

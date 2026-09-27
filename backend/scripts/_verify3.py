import urllib.request, urllib.parse, json

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")

# 测试各种过滤组合
for url in [
    "http://127.0.0.1:8000/api/v1/concepts/",
    "http://127.0.0.1:8000/api/v1/concepts/?source=ths",
    "http://127.0.0.1:8000/api/v1/concepts/?source=ths&is_active=true",
    "http://127.0.0.1:8000/api/v1/concepts/?is_active=true",
    "http://127.0.0.1:8000/api/v1/concepts/?source=&is_active=true",
]:
    code, body = get(url)
    try:
        data = json.loads(body)
        items = data.get("data", {}).get("items", [])
        total = data.get("data", {}).get("total")
        print(f"  url={url}  status={code}  items={len(items)}  total={total}")
    except Exception:
        print(f"  url={url}  status={code}  raw={body[:200]}")

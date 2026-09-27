import urllib.request, json

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")

# 1. 不带 source 看是否走默认 ths
for s in ["ths", "em", ""]:
    url = f"http://127.0.0.1:8000/api/v1/concepts/?limit=5&is_active=true" + (f"&source={s}" if s else "")
    code, body = get(url)
    print(f"=== source={s or '(default)'} status={code} ===")
    try:
        data = json.loads(body)
        items = data.get("items", [])
        print(f"  count={len(items)}")
        for it in items[:5]:
            print(f"  {it.get('name')[:30]:30s}  src={it.get('source')}  active={it.get('is_active')}")
    except Exception:
        print("  raw=", body[:300])

# 2. 直接 query 所有
print()
print("=== /concepts/ all ===")
code, body = get("http://127.0.0.1:8000/api/v1/concepts/?limit=5")
data = json.loads(body)
print("count=", len(data.get("items", [])), "total=", data.get("total"))
for it in data.get("items", [])[:5]:
    print(f"  {it.get('name')[:30]:30s}  src={it.get('source')}  active={it.get('is_active')}")

# 3. 看看 tab 究竟返回什么
print()
print("=== /concepts/tab-by-symbol/000001 raw ===")
code, body = get("http://127.0.0.1:8000/api/v1/concepts/tab-by-symbol/000001")
data = json.loads(body)
print(json.dumps(data, ensure_ascii=False, indent=2)[:1500])

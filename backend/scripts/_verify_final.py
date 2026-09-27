import urllib.request, urllib.parse, json

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")

def parse(body):
    try:
        return json.loads(body).get("data", {})
    except Exception:
        return {}

print("=== /stock-panel/?with_concepts=true&limit=3 ===")
code, body = get("http://127.0.0.1:8000/api/v1/stock-panel/?with_concepts=true&limit=3")
data = parse(body)
for row in data.get("items", [])[:3]:
    cs = row.get("concepts") or []
    print(f"  {row['symbol']} {row['name']}  concepts={len(cs)}  overflow={row.get('concepts_overflow', 0)}")
    for c in cs[:2]:
        snap = c.get("snapshot") or {}
        print(f"    - {c.get('name')[:20]:20s} pct={snap.get('pct_change')} rank={snap.get('rank_label')} turnover={snap.get('turnover_yi')}")

print()
print("=== /concepts/tab-by-symbol/000001 ===")
code, body = get("http://127.0.0.1:8000/api/v1/concepts/tab-by-symbol/000001")
data = parse(body)
secs = data.get("sections", [])
print("total=", data.get("total_count"), "merged=", data.get("is_merged"))
for s in secs:
    print(f"  {s['type_label']} ({len(s['concepts'])})")
    for c in s["concepts"][:3]:
        snap = c.get("snapshot") or {}
        print(f"    - {c['name'][:20]:20s} pct={snap.get('pct_change')} rank={snap.get('rank_label')}")

print()
print("=== /concepts/snapshots/batch?names=华为概念,5G概念 ===")
url = "http://127.0.0.1:8000/api/v1/concepts/snapshots/batch?names=" + urllib.parse.quote("华为概念,5G概念")
code, body = get(url)
print(f"  status={code}")
data = parse(body)
for k, v in data.items():
    print(f"  {k}: pct={v.get('pct_change')} rank={v.get('rank_label')}")

print()
print("=== /concepts/华为概念/snapshot ===")
url = "http://127.0.0.1:8000/api/v1/concepts/" + urllib.parse.quote("华为概念") + "/snapshot"
code, body = get(url)
data = parse(body)
print(f"  status={code}")
print(f"  snapshot: pct_change={data.get('pct_change')} color={data.get('color')} turnover_yi={data.get('turnover_yi')}")

print()
print("=== /concepts/华为概念/index-th?limit=5 ===")
url = "http://127.0.0.1:8000/api/v1/concepts/" + urllib.parse.quote("华为概念") + "/index-th?limit=5"
code, body = get(url)
print(f"  status={code}")
try:
    parsed = json.loads(body)
    data = parsed.get("data", [])
    print(f"  rows: {len(data) if isinstance(data, list) else len(data.get('items', []))}")
    if isinstance(data, list):
        for r in data[:3]:
            print(f"    {r}")
    elif isinstance(data, dict):
        for r in data.get("items", [])[:3]:
            print(f"    {r}")
except Exception as e:
    print(f"  err: {e}; raw: {body[:200]}")

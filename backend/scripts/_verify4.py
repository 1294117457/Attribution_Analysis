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
    print(f"  {row['symbol']} {row['name']}  concepts={len(cs)}")
    for c in cs[:2]:
        snap = c.get("snapshot") or {}
        print(f"    - {c.get('name')[:20]} pct={snap.get('pct_change')} rank={snap.get('rank_label')}")

print()
print("=== /concepts/tab-by-symbol/000001 ===")
code, body = get("http://127.0.0.1:8000/api/v1/concepts/tab-by-symbol/000001")
data = parse(body)
secs = data.get("sections", [])
print("total=", data.get("total_count"), "merged=", data.get("is_merged"))
for s in secs:
    print(f"  {s['type_label']} ({len(s['concepts'])})")
    for c in s["concepts"][:2]:
        snap = c.get("snapshot") or {}
        print(f"    - {c['name'][:20]} pct={snap.get('pct_change')} rank={snap.get('rank_label')}")

print()
print("=== /concepts/snapshots/batch?name=华为概念,name=5G概念 ===")
url = "http://127.0.0.1:8000/api/v1/concepts/snapshots/batch?name=" + urllib.parse.quote("华为概念") + "&name=" + urllib.parse.quote("5G概念")
code, body = get(url)
print(f"  status={code}")
print("  raw=", body[:400])

print()
print("=== /concepts/华为概念/snapshot ===")
url = "http://127.0.0.1:8000/api/v1/concepts/" + urllib.parse.quote("华为概念") + "/snapshot"
code, body = get(url)
data = parse(body)
print(f"  status={code}")
print("  snapshot:", json.dumps(data, ensure_ascii=False)[:300])

print()
print("=== /concepts/华为概念/index-th ===")
url = "http://127.0.0.1:8000/api/v1/concepts/" + urllib.parse.quote("华为概念") + "/index-th?limit=5"
code, body = get(url)
data = parse(body)
print(f"  status={code}")
print("  rows:", len(data.get("items", [])))

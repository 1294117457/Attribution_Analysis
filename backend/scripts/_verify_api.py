import urllib.request, json, sys

def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.status, r.read().decode("utf-8", "ignore")

print("=== /concepts/?source=ths ===")
status, body = get("http://127.0.0.1:8000/api/v1/concepts/?source=ths&limit=3")
print("status=", status)
try:
    data = json.loads(body)
    print("count=", len(data.get("items", [])))
    for it in data.get("items", [])[:3]:
        print(f"  {it['name']}  src={it.get('source')}  active={it.get('is_active')}")
except Exception as e:
    print("raw=", body[:600])

print()
print("=== /stock-panel/?with_concepts=true&limit=3 ===")
status, body = get("http://127.0.0.1:8000/api/v1/stock-panel/?with_concepts=true&limit=3")
print("status=", status)
try:
    data = json.loads(body)
    for row in data.get("items", [])[:3]:
        cs = row.get("concepts") or []
        print(f"  {row['symbol']} {row['name']}  concepts={len(cs)}")
        for c in cs[:2]:
            snap = c.get("snapshot") or {}
            print(f"    - {c.get('name')[:20]} pct={snap.get('pct_change')} rank={snap.get('rank_label')}")
except Exception as e:
    print("raw=", body[:600])

print()
print("=== /concepts/tab-by-symbol/000001 ===")
status, body = get("http://127.0.0.1:8000/api/v1/concepts/tab-by-symbol/000001")
print("status=", status)
try:
    data = json.loads(body)
    secs = data.get("sections", [])
    print("total=", data.get("total_count"), "merged=", data.get("is_merged"))
    for s in secs:
        print(f"  {s['type_label']} ({len(s['concepts'])})")
        for c in s["concepts"][:2]:
            snap = c.get("snapshot") or {}
            print(f"    - {c['name'][:20]} pct={snap.get('pct_change')} rank={snap.get('rank_label')}")
except Exception as e:
    print("raw=", body[:600])

print()
print("=== /concepts/snapshots/batch?name=华为概念,name=5G概念 ===")
status, body = get("http://127.0.0.1:8000/api/v1/concepts/snapshots/batch?name=" + urllib.parse.quote("华为概念") + "&name=" + urllib.parse.quote("5G概念"))
print("status=", status)
try:
    data = json.loads(body)
    items = data.get("items", [])
    print("snapshots=", len(items))
    for s in items[:3]:
        print(f"  {s.get('concept_name')} pct={s.get('pct_change')} turnover_yi={s.get('turnover_yi')}")
except Exception as e:
    print("raw=", body[:400])

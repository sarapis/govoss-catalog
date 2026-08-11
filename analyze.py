#!/usr/bin/env python3
import json, collections, os
OUT = os.path.dirname(os.path.abspath(__file__))
c = json.load(open(f"{OUT}/catalog.json"))

print(f"TOTAL RECORDS: {len(c)}")
print("\n== by source / tier")
for (s, t), n in sorted(collections.Counter((r["source"], r["tier"]) for r in c).items(),
                        key=lambda x: -x[1]):
    print(f"   {n:>6}  {s:<28} {t}")

print("\n== by country")
for k, n in collections.Counter(r["country"] for r in c).most_common():
    print(f"   {n:>6}  {k}")

keys = collections.defaultdict(set)
for r in c:
    if r.get("repo_key"):
        keys[r["repo_key"]].add(r["country"])
print(f"\n== distinct repos: {len(keys)}")
multi = {k: sorted(v) for k, v in keys.items() if len(v) > 1}
print(f"== repos claimed by >1 country: {len(multi)}")
for k, v in list(multi.items())[:12]:
    print(f"     {'+'.join(v):<10} {k}")

pc = [r for r in c if r["tier"] == "publiccode"]
print(f"\n== publiccode tier: {len(pc)}   index tier: {len(c)-len(pc)}")
print("== licenses (publiccode tier):")
for k, n in collections.Counter(r.get("license") for r in pc).most_common(8):
    print(f"   {n:>5}  {k}")

if any("http_status" in r for r in c):
    st = {}
    for r in c:
        if r.get("repo_key") and r["repo_key"] not in st:
            st[r["repo_key"]] = r.get("http_status")
    cnt = collections.Counter(st.values())
    ok = cnt.get(200, 0)
    dead = sum(v for k, v in cnt.items() if k in (404, 410))
    print(f"\n== LIVENESS over {len(st)} distinct repos")
    print(f"   200 OK: {ok} ({round(100*ok/len(st))}%)   hard-dead 404/410: {dead} ({round(100*dead/len(st),1)}%)")
    print("   other:", {k: v for k, v in cnt.most_common(10) if k not in (200, 404, 410)})
    print("\n   dead entries by source:")
    bad = collections.Counter(r["source"] for r in c if r.get("http_status") in (404, 410))
    for k, n in bad.most_common(10):
        print(f"     {n:>4}  {k}")
    print("\n   sample dead:")
    seen = set()
    for r in c:
        if r.get("http_status") in (404, 410) and r["repo_key"] not in seen:
            seen.add(r["repo_key"])
            print(f"     [{r['http_status']}] {r['source']:<26} {(r['name'] or '')[:32]:<34} {r['repo'][:62]}")
            if len(seen) >= 12:
                break

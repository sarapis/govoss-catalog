#!/usr/bin/env python3
"""The Civic Tech Field Guide navigation, pulled from its Payload CMS.

govoss is presented as part of the CTFG network, so its utility bar and footer
link columns should be the SAME links the rest of the network shows - and should
follow when CTFG edits them, without anyone remembering to edit this repo.

WHERE IT COMES FROM
    https://cms.civictech.guide/api/navigation

Payload, five documents keyed by `location`: "Main Menu" plus four
"Footer - <group>" collections. Found by probing: civictech.guide itself is a
Next.js front end with no API, and app.civictech.guide is Softr - which answers
200 to ANY path, so it looks like an API and is not. The CMS is the separate
cms.civictech.guide host, and its Payload REST error shape is what identified it.

FETCHED AT BUILD TIME, NOT IN THE BROWSER
The pages are static and self-contained. A runtime fetch would put a third-party
request on every reader's browser - the same objection that made us self-host the
fonts - and would break the page when the CMS is slow. Pulling at build time
means the nav refreshes on the weekly run and ships as plain HTML.

DEGRADES, NEVER EMPTIES
A successful fetch is cached to cache/ctfg_nav.json and committed. If the CMS is
unreachable at build time the cache is used; if there is no cache, a minimal
built-in set is used. A build must never publish an empty nav because a third
party had an outage - an empty utility bar looks deliberate to a reader and
signals nothing to us.
"""
import json, os, ssl, urllib.request

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()

OUT = os.path.dirname(os.path.abspath(__file__))
CACHE = f"{OUT}/cache/ctfg_nav.json"
API = "https://cms.civictech.guide/api/navigation?limit=50"
UA = {"User-Agent": "govoss-catalog/0.2 (+https://govoss-catalog.vercel.app)"}

# Last-resort floor. Deliberately tiny: if we are this far into the fallback
# chain, the honest thing is a couple of links that certainly exist, not a
# reconstruction of a menu we cannot currently see.
FLOOR = {"Main Menu": [{"label": "Directory", "url": "https://app.civictech.guide/"},
                       {"label": "Calendar", "url": "https://app.civictech.guide/calendar"}]}


def _norm(doc):
    out = []
    for it in (doc.get("items") or []):
        link = it.get("link") or {}
        label = it.get("label") or it.get("title") or link.get("label")
        url = it.get("url") or link.get("url") or it.get("href")
        if not (label and url):
            continue
        # CMS links are relative to civictech.guide, not to this site
        if url.startswith("/"):
            url = "https://civictech.guide" + url
        out.append({"label": label, "url": url})
    return out


def fetch(timeout=20):
    """Live pull. Returns {location: [{label,url}]} or raises."""
    req = urllib.request.Request(API, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        data = json.load(r)
    nav = {}
    for doc in data.get("docs", []):
        loc = (doc.get("location") or "").strip()
        items = _norm(doc)
        if loc and items:
            nav[loc] = items
    if "Main Menu" not in nav:
        raise ValueError("navigation returned no Main Menu")
    return nav


def load():
    """Build-time entry point. Never raises, never returns empty."""
    try:
        nav = fetch()
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w") as f:
            json.dump(nav, f, indent=1, sort_keys=True)
        print("   ctfg nav: fetched %d locations from the CMS" % len(nav))
        return nav
    except Exception as e:
        if os.path.exists(CACHE):
            nav = json.load(open(CACHE))
            print("   ctfg nav: CMS unreachable (%s); using cached copy (%d locations)"
                  % (type(e).__name__, len(nav)))
            return nav
        print("   ctfg nav: CMS unreachable (%s) and no cache; using the built-in floor" % e)
        return dict(FLOOR)


def footer_groups(nav):
    """The four 'Footer - <group>' locations, in CMS order, group name only."""
    out = []
    for loc, items in nav.items():
        if loc.lower().startswith("footer"):
            # "Footer - Get Involved" / "Footer — Get Involved" -> "Get Involved"
            name = loc.split("—")[-1].split("-")[-1].strip() if (
                "—" in loc or "-" in loc) else loc
            out.append((name, items))
    return out


if __name__ == "__main__":
    n = load()
    for loc, items in n.items():
        print(f"\n{loc}")
        for i in items:
            print("   -", i["label"], "->", i["url"])

#!/usr/bin/env python3
"""Fetch the /ospos page's logos and flags into ospos/img/ - MANUAL, like
place_from_wikidata.py; never run by run.sh. build_ospos.py only READS this
folder (copied to site/ospo-img/), so the page makes no third-party request
(GDPR) and a dead favicon service never breaks a build.

  logo/<host>.png   each office's site favicon at 64px, from Google's favicon
                    service (the design handoff's source); when the host has none,
                    its parent domain's (candidates()). Skipped for github.com and
                    gitlab.com, and when the service has no real icon (a 404, or
                    its 16px default globe) - the card shows initials then.
  flag/<code>.svg   from flag-icons (lipis/flag-icons, MIT), the 4x3 set, by the
                    flag's code: Greece's EL is gr; INT has none.

Adds, never overwrites: a logo that looks wrong is deleted by hand (or replaced
with a better file of the same name) and stays that way. --refresh re-fetches all.

    python3 ospos/fetch_images.py [--refresh]
"""
import json
import os
import struct
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import build_ospos as B          # noqa: E402  (host_of, flag_file: one rule for both)

LOGO = "https://www.google.com/s2/favicons?domain=%s&sz=64"
FLAG = "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/%s"
UA = {"User-Agent": "govoss-catalog ospos/fetch_images.py (+https://govoss.cat)"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return r.read()


# hosts that are a SHARED platform: their parent domain is not the office's organisation
SHARED = ("github.io", "gitlab.io", "netlify.app", "pages.dev", "readthedocs.io")


def candidates(h):
    """The host, then its parent domains down to two labels (cloudblogs.microsoft.com
    -> microsoft.com), never past a shared platform or a two-letter second level
    (ac.uk, go.jp, ac.cn)."""
    out, parts = [h], h.split(".")
    if any(h == s or h.endswith("." + s) for s in SHARED):
        return out
    while len(parts) > 2:
        parts = parts[1:]
        if len(parts) == 2 and len(parts[0]) <= 3 and len(parts[1]) == 2:
            break
        out.append(".".join(parts))
    return out


def png_width(b):
    return struct.unpack(">I", b[16:20])[0] if b[:8] == b"\x89PNG\r\n\x1a\n" else 0


def main(refresh):
    data = json.load(open(os.path.join(ROOT, "cache", "ospos.json"), encoding="utf-8"))["ospos"]
    locs = json.load(open(os.path.join(HERE, "locations.json"), encoding="utf-8"))["locations"]
    os.makedirs(os.path.join(HERE, "img", "logo"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "img", "flag"), exist_ok=True)
    got = skipped = 0
    hosts = sorted({B.host_of(r["url"]) for r in data} - {"", "github.com", "gitlab.com"})
    for h in hosts:
        out = os.path.join(HERE, "img", "logo", h + ".png")
        if os.path.exists(out) and not refresh:
            continue
        b = None
        for cand in candidates(h):
            try:
                b = get(LOGO % cand)
            except Exception:          # 404: the service has no icon for that host
                b = None
            if b and png_width(b) >= 32:   # under 32px is the service's default globe
                break
            b = None
        if not b:
            print("  logo %s: none (%s)" % (h, ", ".join(candidates(h))))
            skipped += 1
            if os.path.exists(out):
                os.remove(out)
            continue
        open(out, "wb").write(b); got += 1
        time.sleep(0.2)
    print("logos: %d fetched, %d with no icon, %d hosts" % (got, skipped, len(hosts)))
    ccs = {r.get("country") or (locs.get(r["id"]) or {}).get("country") for r in data}
    nf = 0
    for cc in sorted(c for c in ccs if c):
        f = B.flag_file(cc)
        out = f and os.path.join(HERE, "img", "flag", f)
        if not f or (os.path.exists(out) and not refresh):
            continue
        try:
            b = get(FLAG % f)
        except Exception as e:
            print("  flag %s: %s" % (cc, e))
            continue
        if not b.lstrip().startswith(b"<svg"):
            print("  flag %s: not an SVG" % cc)
            continue
        open(out, "wb").write(b); nf += 1
    print("flags: %d fetched" % nf)


if __name__ == "__main__":
    main("--refresh" in sys.argv[1:])

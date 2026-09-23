#!/usr/bin/env python3
"""Tests for variants.py - "this entry is a version of that entry".

    python3 test_variants.py

Every rule in variants.resolve() exists for a case in the data, and each is
pinned here by the smallest record that exercises it. The last two checks run
on REAL data: the Osnabrueck and Regensburg portals' publiccode.yml isBasedOn
(which only reaches catalog.json on a live harvest) injected into their real
rows, and norm_repo agreeing with harvest.norm_repo on every catalogue URL.
"""
import copy
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    s = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


V = load("variants")


def rec(name, repo, **kw):
    r = {"name": name, "source": "XX/test", "repo": "https://" + repo,
         "repo_key": repo, "catalogue_entries": [{"repo_url": "https://" + repo}]}
    r.update(kw)
    return r


CORE = rec("Consul Democracy", "github.com/consul/consul")
LIB = rec("Bootstrap Italia", "github.com/italia/bootstrap-italia", software_type="library")
NONE = {"variants": [], "aliases": {}}

failed, n = [], 0


def check(label, got, want):
    global n
    n += 1
    if got != want:
        failed.append("%s: expected %r, got %r" % (label, want, got))


def link_of(catalog, curated, name):
    links, report = V.resolve(catalog, curated)
    by_name = {r["name"]: V.ident(r) for r in catalog}
    return links.get(by_name[name]), report


# 1. a publisher's isBasedOn that resolves by repo URL links, with provenance
v = rec("Portal A", "gitlab.example/a/portal",
        based_on=["https://github.com/consul/consul"])
l, _ = link_of([CORE, v], NONE, "Portal A")
check("publiccode claim links to the core", l and l["name"], "Consul Democracy")
check("publiccode claim carries via=publiccode", l and l["via"], "publiccode")

# 2. an alias maps a moved repo onto the URL the catalogue holds
v = rec("Portal B", "gitlab.example/b/portal",
        based_on=["https://github.com/consuldemocracy/consuldemocracy"])
l, _ = link_of([CORE, v], NONE, "Portal B")
check("without the alias a moved repo does not resolve", l, None)
cur = {"variants": [], "aliases": {"https://github.com/consuldemocracy/consuldemocracy":
                                   "https://github.com/consul/consul"}}
l, _ = link_of([CORE, v], cur, "Portal B")
check("with the alias it does", l and l["name"], "Consul Democracy")

# 3. a claim naming a LIBRARY is a dependency, not a version
v = rec("Sito Comune", "github.com/comune/sito",
        based_on=["https://github.com/italia/bootstrap-italia"])
l, rep = link_of([LIB, v], NONE, "Sito Comune")
check("a library core is rejected", l, None)
check("...and reported with its reason",
      [x["reason"][:15] for x in rep["rejected"]], ["core is a libra"])

# 4. an addon extends its core and a config file deploys it: neither is a version
for t in ("addon", "configurationFiles"):
    v = rec("Thing " + t, "github.com/x/" + t, software_type=t,
            based_on=["https://github.com/consul/consul"])
    l, _ = link_of([CORE, v], NONE, "Thing " + t)
    check("a %s entry is not a variant" % t, l, None)

# 5. homepages never match: "based on www.debian.org" names a platform
deb = rec("Debian", "salsa.debian.org/public", landing="https://www.debian.org")
v = rec("Distro", "github.com/x/distro", based_on=["www.debian.org"])
l, rep = link_of([deb, v], NONE, "Distro")
check("a homepage claim does not link", l, None)
check("...it is reported unresolved", len(rep["unresolved"]), 1)

# 6. a claim naming software outside the catalogue is unresolved, not an error
v = rec("Viewer", "github.com/x/viewer", based_on=["https://github.com/lodlive/lodview"])
l, rep = link_of([CORE, v], NONE, "Viewer")
check("outside-catalogue claim does not link", l, None)
check("...and is reported", [x["claim"] for x in rep["unresolved"]],
      ["https://github.com/lodlive/lodview"])

# 7. naming yourself is ignored
v = rec("Self", "github.com/x/self", based_on=["https://github.com/x/self"])
l, rep = link_of([v], NONE, "Self")
check("self-reference ignored", l, None)
# Silently: without its own guard a self-claim falls through to the cycle guard
# and is reported as a data error, which it is not.
check("self-reference is not reported as a cycle", rep["rejected"], [])

# 8. curated adds a link the publisher never declared - keyed on REPO, not name
w = rec("Mitmachportal", "gitlab.example/w/portal")
hashi = rec("Consul", "github.com/hashicorp/consul")
cur = {"aliases": {}, "variants": [{"repo": "https://gitlab.example/w/portal",
                                    "based_on": "https://github.com/consul/consul",
                                    "evidence": "README says CONSUL"}]}
links, _ = V.resolve([CORE, w, hashi], cur)
check("curated link added", links.get(V.ident(w), {}).get("via"), "curated")
check("curated evidence carried", links.get(V.ident(w), {}).get("evidence"), "README says CONSUL")
check("a same-NAMED entry is not touched", V.ident(hashi) in links, False)

# 9. curated based_on null VETOES a publisher claim
v = rec("Vetoed", "github.com/x/vetoed", based_on=["https://github.com/consul/consul"])
cur = {"aliases": {}, "variants": [{"repo": "https://github.com/x/vetoed",
                                    "based_on": None, "evidence": "names a dependency"}]}
l, rep = link_of([CORE, v], cur, "Vetoed")
check("veto removes the link", l, None)
check("veto is reported", [x["reason"][:6] for x in rep["rejected"]], ["vetoed"])

# 10. a variant of a variant resolves to the ROOT
mid = rec("Mid", "github.com/x/mid", based_on=["https://github.com/consul/consul"])
leaf = rec("Leaf", "github.com/x/leaf", based_on=["https://github.com/x/mid"])
links, _ = V.resolve([CORE, mid, leaf], NONE)
check("chain resolves to the root", links.get(V.ident(leaf), {}).get("name"), "Consul Democracy")

# 11. a cycle is a data error, not a core
a = rec("A", "github.com/x/a", based_on=["https://github.com/x/b"])
b = rec("B", "github.com/x/b", based_on=["https://github.com/x/a"])
links, rep = V.resolve([a, b], NONE)
check("cycle links nothing", links, {})
check("cycle reported twice", sorted(x["reason"] for x in rep["rejected"]), ["cycle", "cycle"])

# 12. an excluded core is not a core
xc = dict(CORE, excluded=True)
v = rec("Portal X", "gitlab.example/x/portal", based_on=["https://github.com/consul/consul"])
l, _ = link_of([xc, v], NONE, "Portal X")
check("excluded core does not link", l, None)

# 13. a core reached through a MERGED catalogue's repo url still resolves
merged = dict(CORE, catalogue_entries=[{"repo_url": "https://github.com/consul/consul"},
                                       {"repo_url": "https://github.com/other/mirror"}])
v = rec("Portal M", "gitlab.example/m/portal", based_on=["https://github.com/other/mirror"])
l, _ = link_of([merged, v], NONE, "Portal M")
check("resolves via a merged member's repo", l and l["name"], "Consul Democracy")

# 14. apply() CLEARS a stale link: a withdrawn claim must disappear
stale = rec("Stale", "github.com/x/stale", variant_of={"ident": "gone", "name": "Gone"})
cat = [CORE, stale]
V.apply(cat, NONE)
check("stale variant_of cleared", "variant_of" in stale, False)
# ...and running twice is idempotent
v = rec("Twice", "github.com/x/twice", based_on=["https://github.com/consul/consul"])
cat = [copy.deepcopy(CORE), v]
V.apply(cat, NONE)
once = json.dumps(cat, sort_keys=True)
V.apply(cat, NONE)
check("apply() is idempotent", json.dumps(cat, sort_keys=True), once)

# 15. FORKS. A set-aside fork whose parent is listed by a DIFFERENT catalogue is
# another government's version: reinstated and linked, reason kept.
ck = rec("CKAN", "github.com/ckan/ckan", sources=["GLOBAL/dpg"], source="GLOBAL/dpg")
fk = rec("ckan", "github.com/governmentbg/ckan", source="BG/governmentbg",
         excluded=True, exclude_reason="upstream-fork", fork_parent="https://github.com/ckan/ckan")
cat = [ck, fk]
V.apply(cat, NONE)
check("cross-catalogue fork linked via fork", fk.get("variant_of", {}).get("via"), "fork")
check("...and reinstated", fk.get("excluded"), None)
check("...its original reason kept", fk.get("reinstated_as_variant"), "upstream-fork")
# a claim withdrawn upstream re-hides it: last run's reinstatement is undone first
fk.pop("fork_parent")
V.apply(cat, NONE)
check("withdrawn fork is set aside again", (fk.get("excluded"), fk.get("exclude_reason")),
      (True, "upstream-fork"))
check("...and carries no link", "variant_of" in fk, False)

# 16. a fork inside the SAME catalogue is a mirror or working copy, not a version
core = rec("os2web_help", "github.com/os2web/os2web_help", source="DK/os2")
mir = rec("os2web_help", "github.com/os2display/os2web_help", source="DK/os2",
          excluded=True, exclude_reason="upstream-fork",
          fork_parent="https://github.com/OS2web/os2web_help")
V.apply([core, mir], NONE)
check("same-catalogue fork stays set aside", mir.get("excluded"), True)
check("...and unlinked", "variant_of" in mir, False)

# 17. only upstream-fork rows are reinstated; a row set aside for another reason
# (here no-description) keeps its exclusion even with a qualifying parent
nd = rec("thin", "github.com/governmentbg/thin", source="BG/governmentbg",
         excluded=True, exclude_reason="no-description", fork_parent="https://github.com/ckan/ckan")
V.apply([ck, nd], NONE)
check("a differently-excluded fork is not reinstated", nd.get("excluded"), True)

# 17b. a curated link on a set-aside fork reinstates it too: a human said so
cf = rec("cfork", "github.com/y/cfork", source="BG/y", excluded=True,
         exclude_reason="upstream-fork", fork_parent="https://github.com/nowhere/x")
cur = {"aliases": {}, "variants": [{"repo": "https://github.com/y/cfork",
                                    "based_on": "https://github.com/ckan/ckan", "evidence": "checked"}]}
V.apply([ck, cf], cur)
check("curated link reinstates a set-aside fork", (cf.get("excluded"), cf.get("variant_of", {}).get("via")),
      (None, "curated"))

# 18. publisher claim outranks fork evidence
both = rec("Both", "github.com/x/both", based_on=["https://github.com/consul/consul"],
           fork_parent="https://github.com/ckan/ckan", source="BG/x")
links, _ = V.resolve([CORE, ck, both], NONE)
check("publiccode beats fork", links.get(V.ident(both), {}).get("name"), "Consul Democracy")

# ---- REAL DATA ---------------------------------------------------------------
catalog = json.load(open(os.path.join(HERE, "catalog.json")))
curated = json.load(open(os.path.join(HERE, "variants.json")))

# 15. Osnabrueck and Regensburg declare isBasedOn consuldemocracy/consuldemocracy
# (the repo's CURRENT url; the catalogue holds the old one). Checked on
# gitlab.opencode.de 2026-09-22. Injected here because the field reaches
# catalog.json only on a live harvest.
real = copy.deepcopy(catalog)
DECLARED = {"gitlab.opencode.de/stadtosnabrueck/smart_city_consul",
            "gitlab.opencode.de/regensburg_next/mein.regensburg"}
for r in real:
    if r.get("repo_key") in DECLARED:
        r["based_on"] = ["https://github.com/consuldemocracy/consuldemocracy"]
links, rep = V.resolve(real, curated)
got = {r["repo_key"]: links.get(V.ident(r), {}).get("name") for r in real
       if r.get("repo_key") in DECLARED}
check("both declared portals resolve to Consul Democracy",
      sorted(str(x) for x in got.values()), ["Consul Democracy", "Consul Democracy"])
check("...with publisher provenance",
      sorted(links.get(V.ident(r), {}).get("via", "none") for r in real
             if r.get("repo_key") in DECLARED),
      ["publiccode", "publiccode"])
check("real data: HashiCorp Consul is never a variant",
      any(links.get(V.ident(r)) for r in real
          if r.get("repo_key") == "github.com/hashicorp/consul"), False)

# 16b. Real forks, parents as GitHub reported them on 2026-09-22 (harvest fetches
# fork_parent only on a live run): Bulgaria's CKAN is another government's
# version; ARTE Portugal's udata is NOT, because Portugal's catalogue already
# lists upstream udata itself, so its fork is a working copy inside that catalogue.
real = copy.deepcopy(catalog)
PARENTS = {"github.com/governmentbg/ckan": "https://github.com/ckan/ckan",
           "github.com/amagovpt/udata": "https://github.com/opendatateam/udata"}
for r in real:
    if r.get("repo_key") in PARENTS:
        r["fork_parent"] = PARENTS[r["repo_key"]]
V.apply(real, curated)
got = {r["repo_key"]: (r.get("excluded"), (r.get("variant_of") or {}).get("via"))
       for r in real if r.get("repo_key") in PARENTS}
check("real: Bulgaria's CKAN fork reinstated as a fork variant",
      got.get("github.com/governmentbg/ckan"), (None, "fork"))
check("real: ARTE's udata fork stays set aside",
      got.get("github.com/amagovpt/udata"), (True, None))

# 16. the duplicated norm_repo must agree with harvest's on every real url
H = load("harvest")
urls = {r.get("repo") for r in catalog if r.get("repo")}
urls |= {e.get("repo_url") for r in catalog for e in (r.get("catalogue_entries") or [])
         if e.get("repo_url")}
bad = sorted(u for u in urls if H.norm_repo(u) != V.norm_repo(u))
check("norm_repo agrees with harvest.norm_repo on %d real urls" % len(urls), bad[:3], [])

for f in failed:
    print("FAIL  " + f)
print("\n%d/%d checks passed" % (n - len(failed), n))
sys.exit(1 if failed else 0)

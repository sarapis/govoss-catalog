#!/usr/bin/env python3
"""Regression test for dedupe identity and merge() — review finding F8.

    python3 test_dedupe_identity.py

F8 named dedupe identity and liveness's two-strike logic as the two pure,
regression-prone functions "one incident away" from earning a suite the way
detect_lang earned its own after five recurrences. This is that suite.

The identity rules, in precedence order, and what each one is defending against:

  1. **Wikidata QID.** Upstream general-purpose software does not join on repo
     URL — SILL says `angular.dev`, Sweden says `angular.io`.
  2. **Normalised repo URL** (`harvest.norm_repo`): no scheme/www/.git, deep
     links stripped.
  3. **Exact name AND exact homepage together.** Rules 1-2 cannot reach the
     commonest split: the same upstream tool listed by two catalogues that
     recorded different repo URLs and carry no QID. OpenStreetMap was three
     entries, two pointing at different *wiki pages*.

⚠ NEVER a name alone, and NEVER fuzzy. Angular (Q28925578) and AngularJS
(Q2849803) are different products and one name CONTAINS the other. That case is
asserted below in both directions, because a substring or similarity rule would
pass every other test in this file.

⚠ The homepage half of rule 3 is load-bearing in a way worth stating: it is what
stops `docs`, `about` and `api` merging (they have no landing page), while four
unrelated German repos sharing `umwelt.info` stay split because their names
differ. A conjunction of two independent identifiers is what makes rule 3 safe.
"""
import importlib.util
import sys

import dedupe

_s = importlib.util.spec_from_file_location("harvest", "harvest.py")
harvest = importlib.util.module_from_spec(_s)
_s.loader.exec_module(harvest)
norm_repo = harvest.norm_repo


def rec(name, **kw):
    r = dict({"name": name, "source": "IT/it", "country": "IT", "tier": "index"}, **kw)
    if r.get("repo"):
        r.setdefault("repo_key", norm_repo(r["repo"]))
    return r


def group_of(rows):
    """Run the real union-find grouping from dedupe.py's main block."""
    uf = dedupe.UF()
    for i, r in enumerate(rows):
        uf.find(("i", i))
        if r.get("repo_key"):
            uf.union(("repo", r["repo_key"]), ("i", i))
        if r.get("wikidata"):
            uf.union(("qid", r["wikidata"]), ("i", i))
        nk = dedupe.name_site_key(r)
        if nk:
            uf.union(("namesite", nk), ("i", i))
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(uf.find(("i", i)), []).append(r)
    return sorted(groups.values(), key=len, reverse=True)


def main():
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)          # counted, never hard-coded: a stale n reports a phantom pass
        if got != want:
            failed.append(f"{label}: expected {want!r}, got {got!r}")

    # ---- norm_repo: the join key
    check("scheme+www stripped",
          norm_repo("https://www.github.com/a/b"), "github.com/a/b")
    check(".git stripped", norm_repo("https://github.com/a/b.git"), "github.com/a/b")
    check("trailing slash stripped", norm_repo("https://github.com/a/b/"), "github.com/a/b")
    check("github deep link stripped",
          norm_repo("https://github.com/a/b/tree/main/sub"), "github.com/a/b")
    check("gitlab deep link stripped",
          norm_repo("https://gitlab.com/a/b/-/tree/main"), "gitlab.com/a/b")
    check("lowercased", norm_repo("https://GitHub.com/A/B"), "github.com/a/b")
    check("None on empty", norm_repo(""), None)
    check("None on non-string", norm_repo(42), None)
    # Case-folding is why liveness must HEAD the ORIGINAL url and never repo_key:
    # a case-sensitive host 404s the lowercased path.
    check("case is LOST, hence liveness fetches the original url",
          norm_repo("https://example.org/CaseSensitive/Path"),
          "example.org/casesensitive/path")

    # ---- norm_site: deliberately NOT the repo normalisation
    check("site keeps its path",
          dedupe.norm_site("https://example.org/foo"), "example.org/foo")
    check("site www+slash stripped",
          dedupe.norm_site("https://www.example.org/"), "example.org")
    check("site None on empty", dedupe.norm_site(None), None)

    # ---- name_site_key: rule 3 needs BOTH halves
    check("no landing -> no key",
          dedupe.name_site_key(rec("Foo")), None)
    check("no name -> no key",
          dedupe.name_site_key(rec("", landing="https://x.org")), None)
    check("both -> key",
          dedupe.name_site_key(rec("Foo", landing="https://Www.X.org/")), ("foo", "x.org"))
    check("name is case/space-insensitive",
          dedupe.name_site_key(rec("  FOO  ", landing="https://x.org")),
          dedupe.name_site_key(rec("foo", landing="https://x.org")))

    # ---- identity 1: QID joins what repo URLs cannot
    rows = [rec("Angular", repo="https://angular.dev", wikidata="Q28925578"),
            rec("Angular", repo="https://angular.io", wikidata="Q28925578")]
    check("QID merges differing repo urls", [len(g) for g in group_of(rows)], [2])

    # ---- identity 2: normalised repo URL
    rows = [rec("QGIS", repo="https://github.com/qgis/QGIS.git"),
            rec("qgis", repo="http://www.github.com/QGIS/qgis/")]
    check("norm_repo merges url variants", [len(g) for g in group_of(rows)], [2])

    # ---- identity 3: exact name AND homepage, no QID, different repos
    rows = [rec("OpenStreetMap", repo="https://wiki.osm.org/page/A",
                landing="https://openstreetmap.org"),
            rec("OpenStreetMap", repo="https://wiki.osm.org/page/B",
                landing="https://www.openstreetmap.org/")]
    check("name+homepage merges", [len(g) for g in group_of(rows)], [2])

    # ---- THE case a fuzzy rule would break: one name contains the other
    rows = [rec("Angular", wikidata="Q28925578", landing="https://angular.dev"),
            rec("AngularJS", wikidata="Q2849803", landing="https://angularjs.org")]
    check("Angular / AngularJS stay separate", [len(g) for g in group_of(rows)], [1, 1])
    # ...and even sharing a homepage must not merge them, since the names differ.
    rows = [rec("Angular", landing="https://angular.dev"),
            rec("AngularJS", landing="https://angular.dev")]
    check("same homepage, different names: still separate",
          [len(g) for g in group_of(rows)], [1, 1])

    # ---- generic names cannot merge: no landing page, so rule 3 never fires
    rows = [rec("docs", source="BE/imio"), rec("docs", source="DE/opencode")]
    check("generic names with no homepage stay split",
          [len(g) for g in group_of(rows)], [1, 1])

    # ---- four unrelated repos sharing an ORGANISATION site stay split
    rows = [rec(n, landing="https://umwelt.info") for n in ("a", "b", "c", "d")]
    check("shared org homepage, differing names: 4 groups",
          [len(g) for g in group_of(rows)], [1, 1, 1, 1])

    # ---- union-find CHAINS identities: A~B by repo, B~C by QID => one group
    rows = [rec("A", repo="https://github.com/x/y"),
            rec("B", repo="https://github.com/x/y", wikidata="Q1"),
            rec("C", repo="https://gitlab.com/p/q", wikidata="Q1")]
    check("identities chain through union-find", [len(g) for g in group_of(rows)], [3])

    # ---- merge(): survivor selection by namespace containment, not endswith.
    # openDesk declares bmi/opendesk while the canonical project lives at
    # bmi/opendesk/deployment/opendesk, so an endswith() test failed for the real
    # project AND every fork, handing the entry to a fork on richness alone.
    canonical = rec("openDesk", repo="https://gitlab.opencode.de/bmi/opendesk",
                    repo_key="gitlab.opencode.de/bmi/opendesk",
                    forge_path="bmi/opendesk/deployment/opendesk", tier="publiccode")
    fork = rec("opendesk", repo="https://gitlab.opencode.de/bmi/opendesk",
               repo_key="gitlab.opencode.de/bmi/opendesk",
               forge_path="tlrz/opendesk", tier="publiccode",
               extra1=1, extra2=2, extra3=3, extra4=4, extra5=5)
    check("canonical beats a RICHER fork",
          dedupe.merge([fork, canonical])["forge_path"],
          "bmi/opendesk/deployment/opendesk")
    check("...and the order of the group does not decide it",
          dedupe.merge([canonical, fork])["forge_path"],
          "bmi/opendesk/deployment/opendesk")

    # ---- merge(): union fields, provenance, and the field F5 protects
    a = rec("Matomo", source="FR/sill", country="FR", categories=["analytics"],
            functions=["data-analytics"], entry_url="https://sill/matomo",
            repo="https://github.com/matomo-org/matomo", tier="publiccode")
    b = rec("Matomo Analytics", source="IT/it", country="IT",
            categories=["web-analytics"], functions=["web-content"],
            entry_url=None, repo="https://github.com/matomo-org/matomo",
            short_desc="Analisi web", wikidata="Q3736872")
    m = dedupe.merge([a, b])
    check("categories unioned", sorted(m["categories"]), ["analytics", "web-analytics"])
    # functions is union'd, which is exactly why re-running taxonomy.py on merged
    # output narrows entries — see stage_guard.py.
    check("functions unioned", sorted(m["functions"]), ["data-analytics", "web-content"])
    check("catalogue_count is the DISTINCT source count", m["catalogue_count"], 2)
    check("one catalogue_entry per source", len(m["catalogue_entries"]), 2)
    check("deep link preserved per catalogue",
          m["catalogue_entries"][0]["entry_url"], "https://sill/matomo")
    check("a null entry_url stays null rather than being guessed",
          m["catalogue_entries"][1]["entry_url"], None)
    check("countries unioned", m["countries"], ["FR", "IT"])
    check("sources unioned", m["sources"], ["FR/sill", "IT/it"])
    check("merged_count", m["merged_count"], 2)
    check("alternate name recorded", m["also_known_as"], ["Matomo Analytics"])
    check("QID inherited from a sibling", m["wikidata"], "Q3736872")
    check("description inherited when survivor lacked one", m["short_desc"], "Analisi web")

    # the same source twice must not inflate the pill
    dup = dedupe.merge([a, dict(a, repo_key=a["repo_key"], name="Matomo (mirror)")])
    check("same source twice: catalogue_count stays 1", dup["catalogue_count"], 1)

    # ---- a singleton is not merge()'s job, but its count must still be 1
    check("publiccode tier outranks index in canonical_score",
          dedupe.canonical_score(rec("x", tier="publiccode"))
          > dedupe.canonical_score(rec("x", tier="index")), True)

    # ---- crosswalk.redirect_matches: lend a QID when homepages redirect to one
    # page. Real redirects as measured 2026-09-23; `resolve` is a fake, offline.
    import crosswalk
    R = {"http://www.knime.org/": "https://www.knime.com/",
         "https://www.knime.com": "https://www.knime.com/",
         "https://freemind.sourceforge.net": "https://freemind.sourceforge.io/",
         "https://freemind.sourceforge.io/wiki/index.php/Main_Page":
             "https://freemind.sourceforge.io/wiki/index.php/Main_Page",
         "https://www.consul.io/": "https://developer.hashicorp.com/consul",
         "https://demokratie.today": "https://demokratie.today/"}
    res = R.get

    def lent(rows, org=frozenset()):
        return [(t["source"], q) for t, q, _ in crosswalk.redirect_matches(rows, res, org)]

    k_sill = rec("KNIME Analytics Platform", source="FR/sill", wikidata="Q639194",
                 landing="http://www.knime.org/")
    k_muc = rec("KNIME Analytics Platform", source="DE/muc", landing="https://www.knime.com")
    check("KNIME: Munich row borrows SILL's QID", lent([k_sill, k_muc]), [("DE/muc", "Q639194")])
    check("KNIME: then dedupe merges them on QID",
          len(group_of([k_sill, dict(k_muc, wikidata="Q639194")])), 1)
    check("different final PATH is not a match (FreeMind)",
          lent([rec("FreeMind", source="FR/sill", wikidata="Q1331559",
                    landing="https://freemind.sourceforge.io/wiki/index.php/Main_Page"),
                rec("Freemind", source="DE/muc", landing="https://freemind.sourceforge.net")]), [])
    check("same name, different final host is not a match (Consul)",
          lent([rec("Consul", source="FR/sill", wikidata="Q28709844", landing="https://www.consul.io/"),
                rec("Consul", source="DE/muc", landing="https://demokratie.today")]), [])
    check("same catalogue is not a match", lent([k_sill, dict(k_muc, source="FR/sill")]), [])
    check("a different NAME is not a match, even on the same page",
          lent([k_sill, dict(k_muc, name="KNIME Server")]), [])
    check("an unresolvable page is not a match",
          lent([k_sill, dict(k_muc, landing="https://gone.example")]), [])
    check("two donor QIDs: not ours to pick",
          lent([k_sill, dict(k_sill, source="IT/it", wikidata="Q999"), k_muc]), [])
    check("no homepage is not a match", lent([k_sill, dict(k_muc, landing=None)]), [])
    check("an org-shared homepage is not a match",
          lent([k_sill, k_muc], org=frozenset({"knime.com"})), [])
    check("a row that already has a QID is left alone",
          lent([k_sill, dict(k_muc, wikidata="Q1")]), [])

    # ---- crosswalk.repo_rename_matches: the repo twin, for GitHub renames.
    # Real case, measured 2026-09-23: GitHub answers the old Démarches repo with
    # the renamed one. `resolve` is a fake; non-GitHub keys resolve to None.
    G = {"github.com/demarches-simplifiees/demarches-simplifiees.fr":
             "github.com/demarche-numerique/demarche.numerique.gouv.fr",
         "github.com/demarche-numerique/demarche.numerique.gouv.fr":
             "github.com/demarche-numerique/demarche.numerique.gouv.fr",
         "github.com/other/thing": "github.com/other/thing"}
    d_sill = rec("Démarches simplifiées", source="FR/sill", wikidata="Q93597458",
                 repo="https://github.com/demarche-numerique/demarche.numerique.gouv.fr")
    d_awe = rec("Démarches simplifiées", source="FR/awesome-codegouvfr",
                repo="https://github.com/demarches-simplifiees/demarches-simplifiees.fr")

    def renamed(rows):
        return [(t["source"], q) for t, q, _ in crosswalk.repo_rename_matches(rows, G.get)]

    check("Démarches: renamed repo borrows SILL's QID", renamed([d_sill, d_awe]),
          [("FR/awesome-codegouvfr", "Q93597458")])
    check("a different repo after resolving is not a match",
          renamed([d_sill, dict(d_awe, repo_key="github.com/other/thing")]), [])
    check("rename, but a different NAME, is not a match",
          renamed([d_sill, dict(d_awe, name="Démarche Numérique")]), [])
    check("rename, same catalogue, is not a match",
          renamed([d_sill, dict(d_awe, source="FR/sill")]), [])
    check("an unresolvable repo is not a match",
          renamed([d_sill, dict(d_awe, repo_key="gitlab.com/x/y")]), [])
    check("identical repos are not a 'rename' (dedupe already joins them)",
          renamed([d_sill, dict(d_awe, repo_key=d_sill["repo_key"])]), [])
    check("identical homepages are not a 'redirect' either",
          lent([k_sill, dict(k_muc, landing="http://www.knime.org/")]), [])
    # the inner same-catalogue guard: a third row in ANOTHER catalogue lets the
    # group past the cheap "one catalogue only" skip, so only the pair check stops
    # SILL lending to SILL.
    check("same-catalogue lending is refused even in a mixed group",
          renamed([d_sill, dict(d_awe, source="FR/sill"), rec("Démarches simplifiées", source="IT/it")]),
          [])
    # "without asking" is the claim, so the network is made to fail loudly: a
    # non-GitHub key sent to api.github.com would also come back None (a 404),
    # and a None-only check could not tell the two apart.
    import urllib.request
    asked = []
    real = urllib.request.urlopen
    urllib.request.urlopen = lambda *a, **k: asked.append(a) or (_ for _ in ()).throw(OSError("net"))
    try:
        got = crosswalk.resolve_github_repo("gitlab.com/x/y")
    finally:
        urllib.request.urlopen = real
    check("resolve_github_repo refuses a non-GitHub key without asking", (got, len(asked)), (None, 0))

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

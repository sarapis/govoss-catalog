#!/usr/bin/env python3
"""Regression test for crosswalk.run() - the glue between the identity routes.

    python3 test_crosswalk_run.py

F8's last gap. Every route had its own pinned parts (redirect/repo-rename loans
in test_dedupe_identity.py, cache refresh and the software check in
test_crosswalk_cache.py), but the wiring between them lived under __main__,
reachable only with the network. It is where the ORDER and the SKIPS live:

  * Comptoir precedence: repo url, then SILL id, then website, then an EXACT
    name - and the first Comptoir row to claim a key keeps it;
  * nothing already carrying a QID is re-stamped, by any route;
  * Wikidata is asked only about rows WITHOUT a QID, only about ACTIVE rows,
    and never about an org-shared homepage (umwelt.info: four unrelated repos);
  * a Wikidata match that is not software, or could not be verified, is dropped;
  * each route is best-effort: one failing does not stop the next, and never
    removes what an earlier route stamped;
  * the lending routes run LAST, so they lend QIDs stamped earlier in the run;
  * `wikidata_via` names the route, so an inferred identity is never mistaken
    for one a publisher asserted.

Offline: every network dependency is injected into run().
"""
import sys

import crosswalk as cw


def row(name, source="IT/it", **kw):
    return dict({"name": name, "source": source}, **kw)


class Boom(Exception):
    pass


def main():
    failed, ran = [], []

    def check(label, got, want):
        ran.append(label)
        if got != want:
            failed.append(f"{label}: expected {want!r}, got {got!r}")

    asked = {}

    def wd_repo(keys, state, answers=None):
        asked["repo"] = set(keys)
        return {k: v for k, v in (answers or {}).items() if k in keys}

    def wd_site(sites, state, answers=None):
        asked["site"] = set(sites)
        return {k: v for k, v in (answers or {}).items() if k in sites}

    def verify(qids, bad=(), unverified=()):
        return {q for q in qids if q not in bad and q not in unverified}, set(unverified) & set(qids)

    nores = lambda u: None

    def go(catalog, rows=(), repo_ans=None, site_ans=None, bad=(), unverified=(),
           landing=nores, repo=nores, **over):
        asked.clear()
        return cw.run(catalog, list(rows), {},
                      by_repo_fn=over.get("by_repo_fn") or (lambda k, s: wd_repo(k, s, repo_ans)),
                      by_site_fn=over.get("by_site_fn") or (lambda k, s: wd_site(k, s, site_ans)),
                      verify_fn=over.get("verify_fn") or (lambda q: verify(q, bad, unverified)),
                      resolve_landing_fn=landing, resolve_repo_fn=repo)

    via = lambda e: (e.get("wikidata"), e.get("wikidata_via"))

    # ---- Comptoir precedence: repo > sill_id > website > exact name
    C = [{"wikidata": "Q_REPO", "url_repository": "https://github.com/a/b"},
         {"wikidata": "Q_SILL", "sill": 42},
         {"wikidata": "Q_SITE", "url_website": "https://a.org/"},
         {"wikidata": "Q_NAME", "softwarename": "  Alpha  "}]
    e = row("Alpha", repo_key="github.com/a/b", sill_id=42, landing="https://a.org")
    go([e], C)
    check("repo beats every other Comptoir key", via(e), ("Q_REPO", "comptoir:repo"))
    e = row("Alpha", sill_id=42, landing="https://a.org")
    go([e], C)
    check("SILL id beats website and name", via(e), ("Q_SILL", "comptoir:sill_id"))
    e = row("Alpha", landing="https://www.a.org/")
    go([e], C)
    check("website (normalised) beats name", via(e), ("Q_SITE", "comptoir:website"))
    e = row("ALPHA")
    go([e], C)
    check("name is the last resort, exact and case-insensitive", via(e), ("Q_NAME", "comptoir:exact_name"))
    e = row("Alpha Beta")
    go([e], C)
    check("a name CONTAINING a Comptoir name never matches (Angular/AngularJS)", via(e), (None, None))
    e = row("x", sill_id="42", repo_key="github.com/zz/zz")
    go([e], C)
    check("SILL id matches across int/str", via(e), ("Q_SILL", "comptoir:sill_id"))
    C2 = [{"wikidata": "Q_FIRST", "url_repository": "https://github.com/a/b"},
          {"wikidata": "Q_SECOND", "url_repository": "https://github.com/a/b"},
          {"wikidata": "", "url_repository": "https://github.com/c/d"}]
    e1, e2 = row("x", repo_key="github.com/a/b"), row("y", repo_key="github.com/c/d")
    go([e1, e2], C2)
    check("the first Comptoir row to claim a key keeps it", via(e1), ("Q_FIRST", "comptoir:repo"))
    check("a Comptoir row with no QID stamps nothing", via(e2), (None, None))

    # ---- nothing that already has a QID is re-stamped
    e = row("Alpha", wikidata="Q_OWN", repo_key="github.com/a/b")
    go([e], C, repo_ans={"github.com/a/b": "Q_WD"})
    check("an asserted QID is never overwritten", via(e), ("Q_OWN", None))

    # ---- Wikidata: asked only about rows without a QID, and only active ones
    has = row("Has", wikidata="Q1", repo_key="github.com/has/it", landing="https://has.org")
    ex = row("Excl", excluded=True, repo_key="github.com/ex/cl", landing="https://ex.org")
    todo = row("Todo", repo_key="github.com/to/do", landing="https://todo.org")
    go([has, ex, todo])
    check("Wikidata repo route asks only rows without a QID, only active",
          asked.get("repo"), {"github.com/to/do"})
    check("Wikidata site route asks only rows without a QID, only active",
          asked.get("site"), {"todo.org"})

    # ---- Wikidata: repo beats site; both recorded with their route
    a = row("A", repo_key="github.com/a/a", landing="https://a.example")
    b = row("B", landing="https://b.example")
    go([a, b], repo_ans={"github.com/a/a": "QA"}, site_ans={"a.example": "QX", "b.example": "QB"})
    check("Wikidata: repo route first", via(a), ("QA", "wikidata:repo"))
    check("Wikidata: website route when no repo match", via(b), ("QB", "wikidata:website"))

    # ---- the org-shared homepage: never asked, never stamped (umwelt.info)
    rows4 = [row(n, landing="https://umwelt.info") for n in ("data-stories", "metadaten")]
    go(rows4, site_ans={"umwelt.info": "Q_ORG"})
    check("an org-shared homepage is not even asked", "umwelt.info" in asked.get("site", set()), False)
    check("...and nothing sharing it is stamped", [via(r) for r in rows4], [(None, None)] * 2)
    same = [row("Same", landing="https://one.org", source="FR/sill"),
            row("Same", landing="https://one.org", source="DE/muc")]
    go(same, site_ans={"one.org": "Q_ONE"})
    check("a homepage shared by the SAME name is a product, not an org",
          [via(r)[0] for r in same], ["Q_ONE", "Q_ONE"])

    # ---- the software check gates every Wikidata stamp
    s1, s2 = row("S1", landing="https://s1.org"), row("S2", landing="https://s2.org")
    go([s1, s2], site_ans={"s1.org": "Q_HESSE", "s2.org": "Q_OK"}, bad={"Q_HESSE"})
    check("a matched item that is NOT software is dropped (Hesse)", (via(s1)[0], via(s2)[0]), (None, "Q_OK"))
    s3 = row("S3", landing="https://s3.org")
    go([s3], site_ans={"s3.org": "Q_UNSURE"}, unverified={"Q_UNSURE"})
    check("an unverified item is not stamped", via(s3), (None, None))

    # ---- best effort: a failing route keeps what came before and lets the next run
    def boom(*a, **k):
        raise Boom("503")
    k_sill = row("KNIME", source="FR/sill", repo_key="github.com/knime/knime-core",
                 landing="http://www.knime.org/")
    k_muc = row("KNIME", source="DE/muc", landing="https://www.knime.com")
    R = {"http://www.knime.org/": "https://www.knime.com/", "https://www.knime.com": "https://www.knime.com"}
    hits = go([k_sill, k_muc], [{"wikidata": "Q639194", "url_repository": "https://github.com/knime/knime-core"}],
              by_repo_fn=boom, landing=R.get)
    check("Wikidata failing keeps Comptoir's stamp", via(k_sill), ("Q639194", "comptoir:repo"))
    check("...and the redirect route still runs, lending that stamp",
          via(k_muc), ("Q639194", "redirect:FR/sill"))
    check("the run reports what each route did", (hits["repo"], hits["redirect"]), (1, 1))

    # ---- ORDER: lending runs after Wikidata, so it lends a QID stamped this run
    # fresh rows: the case above stamped k_sill/k_muc in place
    k_sill2 = row("KNIME", source="FR/sill", repo_key="github.com/knime/other",
                  landing="http://www.knime.org/")
    k_muc2 = row("KNIME", source="DE/muc", landing="https://www.knime.com")
    go([k_sill2, k_muc2], repo_ans={"github.com/knime/other": "Q_WD_KNIME"}, landing=R.get)
    check("a QID Wikidata stamped this run is lent on by the redirect route",
          (via(k_sill2), via(k_muc2)),
          (("Q_WD_KNIME", "wikidata:repo"), ("Q_WD_KNIME", "redirect:FR/sill")))

    # ---- the redirect route failing does not stop the repo-rename route
    G = {"github.com/demarches-simplifiees/demarches-simplifiees.fr":
             "github.com/demarche-numerique/demarche.numerique.gouv.fr",
         "github.com/demarche-numerique/demarche.numerique.gouv.fr":
             "github.com/demarche-numerique/demarche.numerique.gouv.fr"}
    d_sill = row("Démarches simplifiées", source="FR/sill", wikidata="Q93597458",
                 repo_key="github.com/demarche-numerique/demarche.numerique.gouv.fr",
                 landing="https://demarches.numerique.gouv.fr")
    d_awe = row("Démarches simplifiées", source="FR/awesome-codegouvfr",
                repo_key="github.com/demarches-simplifiees/demarches-simplifiees.fr",
                landing="https://www.demarches-simplifiees.fr")
    go([d_sill, d_awe], landing=boom, repo=G.get)
    check("the redirect route raising does not stop the repo-rename route",
          via(d_awe), ("Q93597458", "repo-rename:FR/sill"))

    # ---- the whole run survives every route failing, and changes nothing
    z = row("Z", repo_key="github.com/z/z", landing="https://z.org")
    go([z], by_repo_fn=boom, by_site_fn=boom, verify_fn=boom, landing=boom, repo=boom)
    check("every route failing: no crash, nothing stamped", via(z), (None, None))

    for f in failed:
        print(f"FAIL  {f}")
    n = len(ran)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

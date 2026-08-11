#!/usr/bin/env python3
"""Flag entries that are not software a government could adopt.

FLAGS, NEVER DELETES. Every entry keeps `excluded: true` + `exclude_reason` so
the decision is auditable and reversible, and so a rule that turns out to be too
broad can be seen rather than having silently eaten records. `build_ui.py` hides
excluded entries by default and offers a toggle to show them.

Why this exists: iMio publishes 236 repos but only ONE has a publiccode.yml, so
the rest are indexed from bare GitHub metadata. That is real coverage, but it
sweeps in the org's `.github` repo, CI workflow definitions, buildout deployment
recipes, translation resource bundles, and 30 forks of upstream projects
(ZODB, zope.sendmail, Products.CMFEditions, puppetlabs-vcsrepo). "ZODB" listed
as Belgian public-sector software is simply wrong.

Rules apply to ALL sources, not just iMio — the same classes show up elsewhere.
`is_fork` comes from the GitHub API, so it is evidence rather than a name guess.
"""
import json, os, re, collections

OUT = os.path.dirname(os.path.abspath(__file__))

# name -> reason. Ordered: first match wins, so put the specific ones first.
RULES = [
    ("org-meta", re.compile(r"""
        ^\.                        # .github and friends
      | ^ospo$                     # "Open Source Policy Office and related work"
      | ^\.?github$
    """, re.X | re.I)),

    ("ci-plumbing", re.compile(r"""
        ^gha(-workflows)?$
      | ^security-scanning$
      | ^code-analysis-action$
      | -action$
      | ^ploneconf\d*_          # conference talk repos
      | jenkins_to_gha
    """, re.X | re.I)),

    # Buildout/server recipes install OTHER software; they are not the software.
    # (`buildout.pm` is "Buildout installer for iA.Delib product" — the product
    # itself is a separate entry, so keeping both double-counts it.)
    ("deployment-recipe", re.compile(r"""
        ^buildout\.
      | ^server\.
      | ^scripts-
      | ^wcs-scripts-
    """, re.X | re.I)),

    # Translation resource bundles carry no functionality of their own.
    ("locale-bundle", re.compile(r"""
        \.locales$
      | ^teleservices-german-translations$
    """, re.X | re.I)),
    # NOTE: do NOT add a `-german$` rule here. It looks like a locale pattern but
    # catches `teleservices-iacitizen-german`, which is a German-language BUILD
    # of a real product — software, not a resource bundle.
]


def classify(rec):
    """-> (excluded: bool, reason: str|None)"""
    # Never exclude anything that shipped a publiccode.yml: the publisher
    # explicitly declared it as reusable public-sector software, which beats
    # any heuristic of ours.
    if rec.get("tier") == "publiccode":
        return False, None

    if rec.get("is_fork"):
        return True, "upstream-fork"

    name = (rec.get("name") or "").strip()
    for reason, pat in RULES:
        if pat.search(name):
            return True, reason

    # Deliberately NO rule on "missing description". See the note above.
    return False, None


if __name__ == "__main__":
    c = json.load(open(f"{OUT}/catalog.json"))
    reasons, by_source = collections.Counter(), collections.Counter()
    for r in c:
        ex, why = classify(r)
        if ex:
            r["excluded"] = True
            r["exclude_reason"] = why
            reasons[why] += 1
            by_source[r["source"]] += 1
        else:
            r.pop("excluded", None)
            r.pop("exclude_reason", None)

    json.dump(c, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)
    total = sum(reasons.values())
    print(f"{total} of {len(c)} entries flagged as not-adoptable-software "
          f"({100*total/len(c):.0f}%); {len(c)-total} remain")
    print("\n  by reason:")
    for k, n in reasons.most_common():
        print(f"    {n:>4}  {k}")
    print("\n  by source:")
    for k, n in by_source.most_common():
        print(f"    {n:>4}  {k}")
    print("\n  nothing is deleted — every entry keeps excluded/exclude_reason")

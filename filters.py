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

# licence string -> reason. These read the SOURCE'S OWN licence claim, so they
# are evidence, not a guess. SILL's field is free text (156 distinct strings in
# 2026-09) and lists software French administrations use, not only free
# software: Veeam ("non-free license"), Obsidian ("Freemium"), PDF24
# ("Freeware"), Postman ("Propriétaire").
LICENCE_RULES = [
    ("closed-licence", re.compile(r"""
        non-free
      | \bfree\s?ware\b | \bshareware\b | \bfreemium\b | \bgratis\b
      | \bpropri[ée]taire\b | \bproprietary\b | ^eula$
      | n'est\ plus\ libre | no\ longer\ (free|open)
      # n8n's field is a pointer to its LICENSE.md, which is the Sustainable Use
      # License (read 2026-09-23) - source-available, not open source.
      | github\.com/n8n-io/n8n/.*license
    """, re.X | re.I)),
    # Open source permits commercial use (OSD 6), so an NC licence is not one.
    ("non-commercial-licence", re.compile(r"\bnc\b|non-?commercial", re.I)),
    # NOTE: do NOT add SSPL / Elastic License here. SILL's "SSPL 1.0 + Elastic
    # Licence 2.0" for Elasticsearch and Kibana is stale - both added AGPL-3.0
    # in 2024 - and would remove software that is open today.
    # NOTE: do NOT flag "N/A", "NSP", "Je ne sais pas". Unknown is not closed:
    # Debian and CentOS carry "N/A".
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

    lic = (rec.get("license") or "").strip()
    for reason, pat in LICENCE_RULES:
        if pat.search(lic):
            return True, reason

    name = (rec.get("name") or "").strip()
    for reason, pat in RULES:
        if pat.search(name):
            return True, reason

    # A publisher who cannot write one line saying what the software does has not
    # done the minimum needed to share it, so it is held out of the default view.
    # This runs AFTER enrich_desc.py, so it only fires when GitHub had nothing
    # either — the description is genuinely absent upstream, not merely unharvested.
    #
    # READ THIS BEFORE CHANGING IT. A near-identical rule existed once and was
    # removed for cause: `no-usable-metadata` hid 61 entries including
    # Products.PloneMeeting — iMio's flagship deliberations product — plus
    # Products.urban and the ten municipality Meeting* profiles Walloon councils
    # actually run. The reasoning then was "a missing description is not evidence
    # something is not software", and that reasoning still holds.
    #
    # What changed is the CLAIM, not the evidence. This is not an assertion that
    # the entry is not software; it is an editorial standard about publisher
    # effort. It therefore FLAGS rather than deletes, exactly like every rule
    # here: the entry keeps its reason, stays in catalog.json and on the catalog
    # page behind the "set-aside entries" toggle, and if a publisher adds a
    # description the next run returns it on its own.
    #
    # WHAT IT COSTS, corrected 2026-09-10. This comment used to say a set-aside
    # entry "disappears from /entries.json and every derived file", removing 316
    # entries from the public API. That was true when written and is no longer:
    # export_json.py now emits EVERY row carrying `excluded` + `exclude_reason`
    # (verified — /entries.json has 3,318 rows, 484 flagged, PloneMeeting among
    # them), and only the DERIVED indexes stay curated to active rows.
    #
    # The distinction matters for anyone weighing this rule: its cost is that an
    # entry leaves the default view and the browse surfaces, NOT that it leaves
    # the dataset. A stale cost estimate argues for softening a rule that is
    # cheaper than advertised. If the standard is ever softened, soften it here
    # rather than by special-casing the export.
    if not (rec.get("short_desc") or "").strip():
        return True, "no-description"

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

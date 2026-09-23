#!/usr/bin/env python3
"""Link variants to their core: "this entry is a version of that entry".

    python3 variants.py        # after dedupe; rewrites catalog.json in place

Three city participation portals on openCode (Osnabrück, Regensburg, Würzburg)
are all Consul Democracy, which the catalogue also lists. Merging them into it
would destroy what they are evidence of - three governments running their own
Consul - and would blur `catalogue_count`, which counts listings of the SAME
software. So they stay entries, and carry `variant_of` pointing at the core.

Evidence, strongest first, never a name comparison:
  curated     variants.json, keyed on REPO URL. Can add a link the publisher
              did not declare, or VETO one it did.
  publiccode  the publisher's own `isBasedOn` in publiccode.yml.
  fork        the forge's own fork relation (`fork_parent`, from harvest).

A FORK counts only when a different catalogue publishes it than lists its
parent: Bulgaria's fork of CKAN and ARTE Portugal's of udata are other
governments' versions. Inside one catalogue a fork is a mirror or working copy -
11 OS2 modules forked between OS2's own orgs, Dutch documentation repos - and
stays set aside. A qualifying fork that filters.py set aside as `upstream-fork`
is REINSTATED as a variant, its original reason kept in
`reinstated_as_variant`; every run first restores those rows, so a withdrawn
claim re-hides the fork rather than leaving it reinstated.

A claim counts only if it RESOLVES to an active catalogue entry by repo URL,
and survives three rules, each added for a case in the data:
  * the core is not a `library` - "based on Bootstrap Italia" means a site
    USES that framework, not that it is a version of it;
  * the variant is not an `addon` (it extends its core) or
    `configurationFiles` (it deploys it);
  * homepages are never matched - "based on www.debian.org" is a platform.

Pure recomputation every run: every `variant_of` is cleared and re-derived, so
running twice is harmless and a withdrawn claim disappears. That is why this
stage needs no stage_guard, unlike taxonomy and dedupe.

Report: out/variants.json - resolved links, claims naming software outside the
catalogue, and rejections with their reason.
"""
import json
import os
import re

OUT = os.path.dirname(os.path.abspath(__file__))

# Duplicated from harvest.norm_repo rather than imported: importing harvest runs
# its module body. test_variants.py checks the two agree on real URLs.
def norm_repo(url):
    if not url or not isinstance(url, str):
        return None
    u = re.sub(r"^https?://", "", url.strip().rstrip("/"), flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    u = re.sub(r"\.git$", "", u)
    u = re.sub(r"/-/(tree|blob)/.*$", "", u)
    u = re.sub(r"/(tree|blob)/.*$", "", u)
    return u.lower() or None


def ident(r):
    """Same identity as first_seen.ident(): stable across runs."""
    return r.get("repo_key") or "%s|%s" % (r.get("name"), r.get("source"))


REJECT_CORE_TYPES = {"library"}
REJECT_VARIANT_TYPES = {"addon", "configurationFiles"}


def _types(r):
    t = r.get("software_type")
    return set(t) if isinstance(t, list) else {t}


def repo_keys(r):
    """Every repo URL an entry answers to: its own, each merged catalogue's."""
    keys = {r.get("repo_key")}
    keys |= {norm_repo(e.get("repo_url")) for e in (r.get("catalogue_entries") or [])}
    keys |= {norm_repo(u) for u in (r.get("extra_repos") or [])}
    return {k for k in keys if k}


def _sources(r):
    return set(r.get("sources") or [r.get("source")])


def _fork_candidate(r):
    """A set-aside fork whose parent may be in the catalogue."""
    return (r.get("excluded") and r.get("exclude_reason") == "upstream-fork"
            and r.get("fork_parent"))


def resolve(catalog, curated):
    """Pure. Returns (links, report).

    links:  {variant ident: {"ident", "name", "via", "evidence"}} pointing at
            the ROOT core (a variant of a variant resolves to the original).
    report: {"resolved": [...], "unresolved": [...], "rejected": [...]}
    """
    active = [r for r in catalog if not r.get("excluded")]
    by_repo = {}
    for r in active:
        for k in repo_keys(r):
            by_repo.setdefault(k, r)
    aliases = {norm_repo(a): norm_repo(b)
               for a, b in (curated.get("aliases") or {}).items()}
    cur = {norm_repo(v["repo"]): v for v in (curated.get("variants") or [])
           if v.get("repo")}

    report = {"resolved": [], "unresolved": [], "rejected": []}
    direct = {}
    for r in active + [r for r in catalog if _fork_candidate(r)]:
        me = ident(r)
        mine = repo_keys(r)
        c = next((cur[k] for k in mine if k in cur), None)
        if c is not None:
            claims = [(c["based_on"], "curated")] if c.get("based_on") else []
            evidence = c.get("evidence")
            if not claims:
                if r.get("based_on") or r.get("fork_parent"):
                    report["rejected"].append({"entry": r.get("name"),
                                               "claim": r.get("based_on") or r.get("fork_parent"),
                                               "reason": "vetoed in variants.json: %s" % evidence})
                continue
        else:
            evidence = None
            claims = [] if r.get("excluded") else [(b, "publiccode") for b in (r.get("based_on") or [])]
            if r.get("fork_parent"):
                claims.append((r["fork_parent"], "fork"))
        for claim, via in claims:
            k = norm_repo(claim)
            k = aliases.get(k, k)
            core = by_repo.get(k) if k and "/" in k else None
            row = {"entry": r.get("name"), "claim": claim}
            if core is None:
                report["unresolved"].append(row)
                continue
            if ident(core) == me or k in mine:
                continue                                   # names itself
            if _types(core) & REJECT_CORE_TYPES:
                report["rejected"].append(dict(row, reason="core is a library: a dependency, not a version"))
                continue
            if _types(r) & REJECT_VARIANT_TYPES:
                report["rejected"].append(dict(row, reason="entry is an addon or configuration: it extends or deploys its core"))
                continue
            if via == "fork" and _sources(r) & _sources(core):
                report["rejected"].append(dict(row, reason="fork within the same catalogue: a mirror or working copy"))
                continue
            direct[me] = {"core": core, "via": via, "evidence": evidence or claim}
            break

    # Walk to the root, with a cycle guard: A->B->A is a data error, not a core.
    links = {}
    for me, d in sorted(direct.items()):
        core, seen = d["core"], {me}
        while ident(core) in direct and ident(core) not in seen:
            seen.add(ident(core))
            core = direct[ident(core)]["core"]
        if ident(core) in seen:
            report["rejected"].append({"entry": me, "claim": d["evidence"], "reason": "cycle"})
            continue
        links[me] = {"ident": ident(core), "name": core.get("name"),
                     "via": d["via"], "evidence": d["evidence"]}
    by_ident = {ident(r): r for r in catalog}
    for me, l in sorted(links.items()):
        report["resolved"].append({"entry": by_ident[me].get("name"), "core": l["name"],
                                   "via": l["via"], "evidence": l["evidence"]})
    for k in report:
        report[k].sort(key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
    return links, report


def apply(catalog, curated):
    """Restore last run's reinstated forks, clear every variant_of, then set the
    resolved ones - reinstating a qualifying fork. In place; pure otherwise."""
    for r in catalog:
        if r.get("reinstated_as_variant"):
            r["excluded"] = True
            r["exclude_reason"] = r.pop("reinstated_as_variant")
        r.pop("variant_of", None)
    links, report = resolve(catalog, curated)
    for r in catalog:
        l = links.get(ident(r))
        if not l:
            continue
        if r.get("excluded"):
            # Only fork or curated evidence can reach a set-aside row (resolve()
            # skips its publiccode claims), and both mean "show it as a version".
            r["reinstated_as_variant"] = r["exclude_reason"]
            r.pop("excluded", None)             # the shape filters.py gives
            r.pop("exclude_reason", None)       # an active row
        r["variant_of"] = l
    return links, report


def main():
    cat_path = os.path.join(OUT, "catalog.json")
    catalog = json.load(open(cat_path))
    curated = json.load(open(os.path.join(OUT, "variants.json")))
    links, report = apply(catalog, curated)
    json.dump(catalog, open(cat_path, "w"), indent=1, default=str)
    os.makedirs(os.path.join(OUT, "out"), exist_ok=True)
    json.dump(report, open(os.path.join(OUT, "out", "variants.json"), "w"),
              indent=1, ensure_ascii=False)
    cores = {l["ident"] for l in links.values()}
    print(f"variants: {len(links)} linked to {len(cores)} cores "
          f"({sum(1 for l in links.values() if l['via'] == 'curated')} curated); "
          f"{len(report['unresolved'])} claims name software outside the catalogue, "
          f"{len(report['rejected'])} rejected")


if __name__ == "__main__":
    main()

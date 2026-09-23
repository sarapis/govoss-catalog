#!/usr/bin/env python3
"""Regression test for filters.classify() and the replaces.json vocabulary gate.

    python3 test_filters.py

Two of the gaps review finding F8 listed. They belong together because they are
the same kind of thing: a HAND-MAINTAINED editorial rule set, where a wrong entry
produces a confident, plausible-looking error rather than a crash.

`filters.py` flags non-software so a bare-GitHub-metadata source (iMio publishes
236 repos, one with a publiccode.yml) does not offer governments things they
cannot adopt. Every case below is a rule that exists, or a rule that was REMOVED
FOR CAUSE and must not come back:

  * `no-usable-metadata` (missing description => not software) hid 61 entries
    including Products.PloneMeeting, iMio's flagship deliberations product, plus
    Products.urban and the ten municipality Meeting* profiles Walloon councils
    actually run. A missing GitHub description is an upstream metadata gap, not
    evidence something is not software — the same error shape as reading an API
    404 as a dead repo.
  * a `-german$` locale rule caught `teleservices-iacitizen-german`, which is a
    German-language BUILD of a real product.

⚠ The rules FLAG, never delete, and `tier == "publiccode"` is never filtered at
all — a publisher who shipped a publiccode.yml explicitly declared the thing
reusable, which beats any heuristic here. Both are asserted below, because
"filter" and "delete" drifting together is how PloneMeeting vanished once.

The second half runs `export_json.py` against a deliberately corrupted
replaces.json and asserts the build FAILS. That gate is load-bearing: the
by-product sort does `rank.get(confidence, 3)`, so an invalid confidence used to
sort last instead of being reported, which is how `Icinga -> Nagios XI` sat with
a `kind` value in its `confidence` field.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

import filters

HERE = os.path.dirname(os.path.abspath(__file__))


def r(name, **kw):
    return dict({"name": name, "short_desc": "does a thing", "tier": "index"}, **kw)


# (label, record, expected (excluded, reason))
CASES = [
    # ---- publiccode beats every heuristic here
    ("publiccode fork is NOT filtered",
     r("something", tier="publiccode", is_fork=True), (False, None)),
    ("publiccode .github is NOT filtered",
     r(".github", tier="publiccode"), (False, None)),
    ("publiccode with no description is NOT filtered",
     r("thing", tier="publiccode", short_desc=""), (False, None)),

    # ---- fork: evidence from the API, not a name guess. This is the
    # load-bearing rule — it catches ZODB, zope.sendmail, Products.CMFEditions.
    ("fork flag", r("ZODB", is_fork=True), (True, "upstream-fork")),
    ("fork flag beats the name rules", r(".github", is_fork=True),
     (True, "upstream-fork")),

    # ---- org-meta
    ("dot-github", r(".github"), (True, "org-meta")),
    ("ospo", r("ospo"), (True, "org-meta")),

    # ---- ci-plumbing
    ("gha", r("gha"), (True, "ci-plumbing")),
    ("gha-workflows", r("gha-workflows"), (True, "ci-plumbing")),
    ("security-scanning", r("security-scanning"), (True, "ci-plumbing")),
    ("a -action suffix", r("setup-python-action"), (True, "ci-plumbing")),

    # ---- deployment-recipe: installs other software, is not it
    ("buildout.", r("buildout.pm"), (True, "deployment-recipe")),
    ("server.", r("server.imio"), (True, "deployment-recipe")),
    ("scripts-", r("scripts-deploy"), (True, "deployment-recipe")),

    # ---- locale-bundle
    (".locales", r("imio.locales"), (True, "locale-bundle")),
    ("named translations bundle", r("teleservices-german-translations"),
     (True, "locale-bundle")),

    # ⚠ THE REMOVED RULE. A `-german$` pattern would catch this, and it is a
    # German-language build of a real product, not a resource bundle.
    ("a -german BUILD is NOT a locale bundle",
     r("teleservices-iacitizen-german"), (False, None)),

    # ---- no-description: an editorial standard, and it FLAGS
    ("empty description", r("thing", short_desc=""), (True, "no-description")),
    ("whitespace-only description", r("thing", short_desc="   "),
     (True, "no-description")),
    ("missing description key", {"name": "thing", "tier": "index"},
     (True, "no-description")),

    # ⚠ PloneMeeting and friends: real software, and they must be reached by the
    # no-description rule ONLY when the description is genuinely absent — never
    # by a rule that reads a missing description as "not software".
    ("PloneMeeting WITH a description is kept",
     r("Products.PloneMeeting", short_desc="Plone extension for meetings"),
     (False, None)),
    ("Products.urban with a description is kept",
     r("Products.urban", short_desc="Urban planning for Walloon councils"),
     (False, None)),
    ("a municipality Meeting* profile with a description is kept",
     r("Products.MeetingNamur", short_desc="Namur council deliberations profile"),
     (False, None)),

    # ---- licence: the source's own claim. Real SILL / DPG strings.
    ("non-free license", r("Veeam", license="non-free license"), (True, "closed-licence")),
    ("Freemium", r("Obsidian", license="Freemium"), (True, "closed-licence")),
    ("FREEWARE", r("Balabolka", license="FREEWARE"), (True, "closed-licence")),
    ("gratis software", r("IrfanView", license="gratis software"), (True, "closed-licence")),
    ("Propriétaire", r("Postman", license="Propriétaire"), (True, "closed-licence")),
    ("EULA", r("silhouette", license="EULA"), (True, "closed-licence")),
    ("no longer free", r("FreeFileSync", license="N'est plus libre et open-source"),
     (True, "closed-licence")),
    ("n8n's licence pointer",
     r("n8n", license="https://github.com/n8n-io/n8n/blob/master/LICENSE.md"),
     (True, "closed-licence")),
    ("CC NC, SILL spelling", r("CodEx", license="cc BY-NC-SA 4.0"),
     (True, "non-commercial-licence")),
    ("CC NC, SPDX", r("WaPOR", license="CC-BY-NC-SA-4.0"), (True, "non-commercial-licence")),
    ("PolyForm Noncommercial", r("x", license="PolyForm-Noncommercial-1.0.0"),
     (True, "non-commercial-licence")),
    ("licence beats no-description", r("x", license="Freeware", short_desc=""),
     (True, "closed-licence")),
    # ⚠ Stale, not closed: Elasticsearch and Kibana added AGPL-3.0 in 2024.
    ("SSPL + Elastic is NOT flagged", r("Elasticsearch", license="SSPL 1.0 + Elastic Licence 2.0"),
     (False, None)),
    # ⚠ Unknown is not closed.
    ("N/A is NOT flagged", r("Debian", license="N/A"), (False, None)),
    ("Je ne sais pas is NOT flagged", r("PDFgear", license="Je ne sais pas"), (False, None)),
    ("free software is NOT freeware", r("x", license="Free software"), (False, None)),
    ("GNU FSDG", r("x", license="GNU FSDG"), (False, None)),
    ("CC BY-SA", r("x", license="CC-BY-SA-4.0"), (False, None)),
    ("a licence containing 'nc' inside a word", r("x", license="Licence MIT, Inc."), (False, None)),
    ("publiccode with an NC licence is NOT filtered",
     r("Dove voto?", tier="publiccode", license="PolyForm-Noncommercial-1.0.0"), (False, None)),

    # ---- wordpress-plugin: the publisher's composer.json `type`, never a name.
    # Real Helsingborg repos.
    ("composer wordpress-plugin", r("modularity-timeline", composer_type="wordpress-plugin"),
     (True, "wordpress-plugin")),
    ("composer wordpress-muplugin", r("wpmu-allow-cors", composer_type="wordpress-muplugin"),
     (True, "wordpress-plugin")),
    ("a THEME is kept - Municipio is the product",
     r("Municipio", composer_type="wordpress-theme"), (False, None)),
    ("a composer library is kept", r("x", composer_type="library"), (False, None)),
    ("a plugin-sounding NAME with no declaration is kept",
     r("polylang-fallback-plugin"), (False, None)),
    ("publiccode beats a plugin declaration",
     r("x", tier="publiccode", composer_type="wordpress-plugin"), (False, None)),
    ("a fork plugin is reported as a fork", r("x", is_fork=True, composer_type="wordpress-plugin"),
     (True, "upstream-fork")),

    # ---- ordinary software passes
    ("plain software", r("QGIS"), (False, None)),
    ("a name merely containing 'action'", r("transaction-manager"), (False, None)),
    ("a name merely containing 'server'", r("mailserver-tools"), (False, None)),
]


def main():
    failed = []
    for label, rec, want in CASES:
        got = filters.classify(rec)
        if got != want:
            failed.append(f"classify: {label}: expected {want!r}, got {got!r}")

    # classify() must not mutate its input — filters.py's main loop sets
    # excluded/exclude_reason itself, and a classify() that also wrote them
    # would make the "flags, never deletes" contract depend on call order.
    probe = r("thing", short_desc="")
    before = json.dumps(probe, sort_keys=True)
    filters.classify(probe)
    if json.dumps(probe, sort_keys=True) != before:
        failed.append("classify() mutated the record it was given")

    # ---- the replaces.json vocabulary gate must FAIL the build (F8, and the
    # rule export_json.py shares with taxonomy.py: a bad value is a bug).
    rp = f"{HERE}/replaces.json"
    before_sha = hashlib.sha256(open(rp, "rb").read()).hexdigest()
    backup = os.path.join(tempfile.mkdtemp(), "replaces.json")
    shutil.copy2(rp, backup)
    try:
        raw = json.load(open(rp))
        vocab = raw["_README"]
        if "confidence" not in vocab or "kind" not in vocab:
            failed.append("replaces.json:_README no longer declares both vocabularies")

        victim = next(k for k in raw if not k.startswith("_"))
        for field, bad in (("confidence", "paid-tier"),  # the real Icinga bug: a
                                                         # kind value in confidence
                           ("kind", "strong"),           # ...and the mirror image
                           ("confidence", "probably")):
            doc = json.load(open(backup))
            doc[victim][0][field] = bad
            json.dump(doc, open(rp, "w"), indent=1, ensure_ascii=False)
            p = subprocess.run([sys.executable, "export_json.py"], cwd=HERE,
                               capture_output=True, text=True)
            if p.returncode == 0:
                failed.append(f"export_json.py ACCEPTED {field}={bad!r} — the "
                              f"vocabulary gate is not failing the build")
            out = (p.stdout or "") + (p.stderr or "")
            if "invalid values" not in out:
                failed.append(f"export_json.py rejected {field}={bad!r} without "
                              f"naming it as an invalid value")
            if victim not in out:
                failed.append(f"the refusal for {field}={bad!r} does not name the "
                              f"offending key {victim!r}")
    finally:
        shutil.copy2(backup, rp)
        if hashlib.sha256(open(rp, "rb").read()).hexdigest() != before_sha:
            failed.append("replaces.json was NOT restored — check it before committing")

    # ---- a PUBLISHER's own `replaces:` (harvest._pc_replaces) is the opposite
    # posture from the gate above: someone else's file, so a bad value is
    # DROPPED, never fatal, and every row is marked via=publiccode so it cannot
    # pass for a curated claim.
    _hs = importlib.util.spec_from_file_location("harvest", f"{HERE}/harvest.py")
    H = importlib.util.module_from_spec(_hs); _hs.loader.exec_module(H)
    PCR = [
        ("a bare string is a product", ["Zoom"], [{"product": "Zoom", "via": "publiccode"}]),
        ("valid vocabulary kept", [{"product": "Webex", "confidence": "strong", "kind": "software"}],
         [{"product": "Webex", "via": "publiccode", "confidence": "strong", "kind": "software"}]),
        ("bad vocabulary dropped, row kept", [{"product": "X", "confidence": "paid-tier", "kind": "strong"}],
         [{"product": "X", "via": "publiccode"}]),
        ("junk ignored", [3, {"nope": 1}, "  ", {"product": ""}], []),
        ("a non-list is ignored", "Zoom", []),
    ]
    for label, given, want in PCR:
        got = H._pc_replaces(given)
        if got != want:
            failed.append(f"_pc_replaces: {label}: expected {want!r}, got {got!r}")

    for f in failed:
        print(f"FAIL  {f}")
    n = len(CASES) + 2 + 9 + len(PCR)
    print(f"\n{n - len(failed)}/{n} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

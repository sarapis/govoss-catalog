#!/usr/bin/env python3
"""Emit the machine-readable export alongside the human page.

Everything here is a STATIC FILE written at build time — no server, no database,
no framework change, and the existing zero-backend Vercel deploy keeps working.
The human-facing catalogue.html is untouched; this adds a machine path beside it.

Writes into site/ (the Vercel deploy dir):

  entries.json            EVERY entry incl. set-aside ones, flagged, one array
  meta.json               categories, sources, licences, counts, generated_at
  v1/entries.json         versioned alias so consumers can pin
  v1/meta.json
  by-category/<slug>.json one file per functional category
  replaces.json           the inverted index: proprietary product -> alternatives

Deliberately NOT provided: POST /api/match. It cannot be a static file, and the
stated constraint is to keep the deployment backend-free. entries.json carries
`replaces` inline, so one fetch + a local lookup does the same job — see
by-product.json, which is exactly that index precomputed.
"""
import json, os, re, time, collections, importlib.util

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
_spec = importlib.util.spec_from_file_location("taxonomy", f"{OUT}/taxonomy.py")
_tax = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_tax)
FUNCTIONS = _tax.FUNCTIONS
_ss = importlib.util.spec_from_file_location("sources", f"{OUT}/sources.py")
_S = importlib.util.module_from_spec(_ss); _ss.loader.exec_module(_S)

GENERATED_AT = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
# 1.1.0: added counts.rows_in_entries_json + counts_note. Purely ADDITIVE - no
# key changed meaning, so a 1.0.0 consumer is unaffected. Bumped the minor rather
# than staying silent because /v1/entries.json exists for consumers who pin, and
# a schema that gains fields without saying so teaches them not to trust it.
SCHEMA_VERSION = "1.1.0"

# Licence strings arrive in three dialects: real SPDX ids from publiccode.yml,
# display strings from SILL ("MIT licence", "GPLv3+"), and free text. Only claim
# `licence_spdx` when we are actually confident — an spdx-named field holding
# "GPLv3+" is worse than a null, because a consumer will trust the name.
SPDX_FIXUPS = {
    "mit licence": "MIT", "mit license": "MIT", "mit": "MIT",
    "gplv3+": "GPL-3.0-or-later", "gplv3": "GPL-3.0-only",
    "gplv2+": "GPL-2.0-or-later", "gplv2": "GPL-2.0-only",
    "agplv3+": "AGPL-3.0-or-later", "agplv3": "AGPL-3.0-only",
    "lgplv3+": "LGPL-3.0-or-later", "lgplv2.1+": "LGPL-2.1-or-later",
    "apache 2.0": "Apache-2.0", "apache licence 2.0": "Apache-2.0",
    "apache-2.0": "Apache-2.0", "eupl-1.2": "EUPL-1.2",
    "bsd-3-clause": "BSD-3-Clause", "bsd-2-clause": "BSD-2-Clause",
    "mpl-2.0": "MPL-2.0", "cecill-2.1": "CECILL-2.1", "cecill-b": "CECILL-B",
}
SPDX_RE = re.compile(r"^[A-Za-z0-9.+-]+$")


def spdx(raw):
    if not raw:
        return None
    v = raw.strip()
    low = v.lower()
    if low in SPDX_FIXUPS:
        return SPDX_FIXUPS[low]
    # already looks like a single SPDX id (no spaces, no prose)
    if SPDX_RE.match(v) and not v.lower().startswith("http"):
        return v
    return None            # honest null rather than a guess


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def entry_id(r):
    """Stable-ish id: source slug + repo path, else source + name."""
    src = slug((r.get("sources") or [r.get("source", "")])[0].split("/")[-1])
    key = r.get("repo_key") or slug(r.get("name"))
    return f"{src}-{slug(key.split('/')[-1] if '/' in key else key)}"


def build():
    catalog = json.load(open(f"{OUT}/catalog.json"))
    live, LIVE_CHECKED = {}, None
    if os.path.exists(f"{OUT}/liveness.json"):
        _lv = json.load(open(f"{OUT}/liveness.json"))
        live = _lv.get("repos", {})
        LIVE_CHECKED = (_lv.get("summary") or {}).get("checked")
    replaces_raw = json.load(open(f"{OUT}/replaces.json"))
    rmap = {k.lower(): v for k, v in replaces_raw.items() if not k.startswith("_")}

    # Validate the seed against the vocabularies its own _README declares. An
    # invalid value used to pass silently: the by-product sort does
    # rank.get(confidence, 3), so a bad confidence just sorted last instead of
    # being reported — which is how `Icinga -> Nagios XI` sat with
    # confidence:"paid-tier" (a `kind` value) in the confidence field. Same rule
    # as taxonomy.py: an unmapped value is a BUG, not something to bucket.
    _vc, _vk = set(replaces_raw["_README"]["confidence"]), set(replaces_raw["_README"]["kind"])
    bad_vals = [f"{k} -> {m.get('product')}: {f}={m.get(f)!r}"
                for k, v in rmap.items() for m in v
                for f, ok in (("confidence", _vc), ("kind", _vk))
                if m.get(f) not in ok]
    if bad_vals:
        raise SystemExit("replaces.json: invalid values\n   " + "\n   ".join(bad_vals))

    # entries.json carries EVERY row, set-aside ones included and flagged. The
    # no-description rule alone set aside 316, and exporting only active rows
    # made them vanish from the public API with no way for a consumer to see
    # they existed or why. A complete dataset plus a flag lets the caller decide;
    # a truncated one decides for them, silently.
    #
    # The DERIVED indexes below stay curated (active only): by-product must not
    # offer a set-aside entry as a replacement, and by-category/mcp-index are
    # browse surfaces. One complete source of truth, curated views over it.
    entries, used_keys = [], set()
    id_counts = collections.Counter()

    for r in catalog:
        lv = live.get(r.get("repo_key") or "", {})
        fns = r.get("functions") or []
        name = r.get("name") or ""

        # Match on the surviving name OR any also_known_as. dedupe can pick a
        # different survivor name than the one a mapping was keyed on — merging
        # "GitLab Community Edition" into "GitLab" orphaned three keys — and the
        # mapping should follow the software, not the label that happened to win.
        # UNION every matching key — the surviving name and every also_known_as.
        # First-match-wins left "GitLab Community Edition" and "NextCloud" flagged as
        # rot when they were simply redundant with the survivor's own key, and it
        # silently dropped whatever those keys mapped that the survivor's did not.
        rep, seen_prod = [], set()
        for cand in [name] + list(r.get("also_known_as") or []):
            k = (cand or "").strip().lower()
            if not k or k not in rmap:
                continue
            used_keys.add(k)
            for m in rmap[k]:
                pk = (m.get("product") or "").lower()
                if pk and pk not in seen_prod:
                    seen_prod.add(pk)
                    rep.append(m)
        rep = rep or None
        # a publisher may also declare it upstream in publiccode.yml
        if r.get("replaces"):
            rep = (rep or []) + [x for x in r["replaces"] if isinstance(x, dict)]

        eid = entry_id(r)
        id_counts[eid] += 1
        if id_counts[eid] > 1:
            eid = f"{eid}-{id_counts[eid]}"

        e = {
            "id": eid,
            "name": name,
            "description": r.get("short_desc") or None,
            "description_lang": r.get("desc_lang") or None,
            "translated_from": r.get("desc_src_lang") if r.get("translated") else None,
            "description_original": r.get("desc_src") if r.get("translated") else None,

            # singular = primary (first, for simple consumers); plural = full truth
            # after dedupe, where one entry can be asserted by several countries
            "country": (r.get("countries") or [r.get("country")])[0] if (r.get("countries") or r.get("country")) else None,
            "countries": r.get("countries") or ([r["country"]] if r.get("country") else []),
            "source": (r.get("sources") or [r.get("source")])[0],
            "sources": r.get("sources") or ([r["source"]] if r.get("source") else []),
            "source_url": (_S.SOURCES.get((r.get("sources") or [r.get("source")])[0]) or {}).get("site"),
            "source_urls": [ (_S.SOURCES.get(x) or {}).get("site")
                             for x in (r.get("sources") or [r.get("source")]) if x ],
            "merged_from": r.get("merged_count", 1),
            # how many DISTINCT catalogues list this software, and a deep link into
            # each so the claim can be verified upstream rather than taken on trust
            "catalogue_count": r.get("catalogue_count", 1),
            "catalogues": [
                {"source": ce.get("source"),
                 "label": (_S.SOURCES.get(ce.get("source")) or {}).get("label", ce.get("source")),
                 "country": (_S.SOURCES.get(ce.get("source")) or {}).get("country"),
                 "catalogue_url": (_S.SOURCES.get(ce.get("source")) or {}).get("site"),
                 "entry_url": ce.get("entry_url"),
                 "name_there": ce.get("name")}
                for ce in (r.get("catalogue_entries") or [])],
            "also_known_as": r.get("also_known_as") or [],

            "repo_url": r.get("repo") or None,
            "homepage": r.get("landing") or None,
            "owner": r.get("repo_owner") or None,

            "licence": r.get("license") or None,
            "licence_spdx": spdx(r.get("license")),

            "category": FUNCTIONS[fns[0]] if fns else None,
            "categories": [FUNCTIONS[f] for f in fns],
            "category_keys": fns,
            "categories_inferred": bool(r.get("functions_inferred")),
            "source_categories": r.get("categories") or [],

            "development_status": r.get("dev_status") or None,
            "recommended_for_government": bool(r.get("recommended_for_gov")),
            "has_publiccode": r.get("tier") == "publiccode",
            "software_type": r.get("software_type") or None,
            "version": r.get("version") or None,
            "wikidata": r.get("wikidata") or None,
            "dpg": bool(r.get("dpg")),
            "dpg_type": r.get("dpg_type") or [],
            "sdgs": r.get("sdgs") or [],

            "adopters": len(r.get("used_by") or []),
            "adopter_names": r.get("used_by") or [],

            "link_dead": bool(lv.get("dead_since")),
            "repo_archived": bool(lv.get("archived")),
            # liveness.json no longer stores a timestamp per record — every record
            # is checked in the same sweep, so the run's timestamp IS this entry's
            # last_checked. `if lv` matters: an entry with no liveness record was
            # not checked at all, and must stay null rather than inherit the run's
            # time. The lv.get() first keeps an older liveness.json working.
            "last_checked": lv.get("checked") or (LIVE_CHECKED if lv else None),
            "last_push": lv.get("last_push"),

            "replaces": rep or [],

            # why a row is held out of the default view, and of every derived
            # index here. null when the entry is in the catalogue proper.
            "excluded": bool(r.get("excluded")),
            "exclude_reason": r.get("exclude_reason"),
        }
        entries.append(e)

    entries.sort(key=lambda e: (e["name"] or "").lower())
    active = [e for e in entries if not e["excluded"]]

    # ---- warn on seed rot: a replaces key matching nothing is a silent bug
    orphans = sorted(set(rmap) - used_keys)

    # ---- inverted index: proprietary product -> catalogue alternatives.
    # This is the /api/match use case, precomputed as a static file.
    by_product = collections.defaultdict(list)
    for e in active:
        for m in e["replaces"]:
            by_product[m["product"]].append({
                "name": e["name"], "id": e["id"],
                "confidence": m.get("confidence"), "kind": m.get("kind"),
                "country": e["country"], "countries": e["countries"],
                "adopters": e["adopters"], "licence_spdx": e["licence_spdx"],
                "repo_url": e["repo_url"], "category": e["category"],
                "link_dead": e["link_dead"], "note": m.get("note"),
            })
    # Collapse rows that name the same software: two catalogue entries can share a
    # name without dedupe merging them (different repo urls, no shared QID), which
    # showed up as "Docker Desktop -> Docker, Docker" in the product index.
    for prod, v in by_product.items():
        seen, uniq = set(), []
        for x in sorted(v, key=lambda x: -x["adopters"]):
            k = (x["name"] or "").lower()
            if k in seen:
                continue
            seen.add(k)
            uniq.append(x)
        rank = {"strong": 0, "partial": 1, "adjacent": 2}
        uniq.sort(key=lambda x: (rank.get(x["confidence"], 3), -x["adopters"]))
        by_product[prod] = uniq

    cats = collections.Counter(c for e in active for c in e["categories"])
    meta = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": GENERATED_AT,
        "human_page": "https://govoss-catalog.vercel.app/",
        # ⚠ `entries` counts the ACTIVE catalogue; /entries.json deliberately
        # ships MORE rows than that, because a set-aside entry is flagged rather
        # than dropped. Reported upstream 2026-08-14 by a consumer who read
        # `counts.entries` (2,753), counted /entries.json (3,206) and called the
        # difference a bug — reasonably, since `counts.entries` sits next to
        # `files.entries` and the same word meant two things. The reconciling
        # figures were already here (`filtered_out`, `total_including_set_aside`)
        # and llms.txt already spelled it out, so nothing was WRONG; it was
        # unfindable from the key a consumer naturally reads first.
        #
        # `entries` keeps its meaning - renaming it would break anyone already
        # reading it correctly. `rows_in_entries_json` is the fix: a key that
        # names the file it describes, so the question cannot be asked twice.
        # ⚠ The first draft of this note listed /v1/entries.json among the
        # active-only indexes. It is not one - it is a byte alias of
        # /entries.json, so it carries all rows by design. Caught by checking the
        # published files for set-aside ids instead of restating the docs; the
        # note would have shipped a confident, wrong claim into the artefact that
        # exists to stop exactly this confusion.
        "counts_note": (
            "`entries` is the ACTIVE catalogue. /entries.json holds "
            "`rows_in_entries_json` rows, because a set-aside entry is flagged "
            "`excluded: true` with an `exclude_reason` rather than dropped — filter "
            "on `excluded` for the active catalogue. /v1/entries.json is an alias of "
            "/entries.json and carries the same rows. The curated browse indexes "
            "(/by-product.json, /by-category/, mcp-index.json) are active-only."
        ),
        "counts": {
            "entries": len(active),
            "rows_in_entries_json": len(entries),
            "with_publiccode": sum(1 for e in active if e["has_publiccode"]),
            "with_wikidata": sum(1 for e in active if e["wikidata"]),
            "with_replaces": sum(1 for e in active if e["replaces"]),
            "in_multiple_catalogues": sum(1 for e in active if e["catalogue_count"] > 1),
            "with_entry_links": sum(1 for e in active
                                    if any(c["entry_url"] for c in e["catalogues"])),
            "digital_public_goods": sum(1 for e in active if e["dpg"]),
            "dead_links": sum(1 for e in active if e["link_dead"]),
            "archived_repos": sum(1 for e in active if e["repo_archived"]),
            "filtered_out": len(entries) - len(active),
            "total_including_set_aside": len(entries),
            "distinct_products_mapped": len(by_product),
        },
        # the 19 categories are a stable documented enumeration
        "categories": [{"key": k, "label": v, "count": cats.get(v, 0)}
                       for k, v in FUNCTIONS.items()],
        "countries": [{"code": k, "count": v} for k, v in
                      collections.Counter(cc for e in active for cc in e["countries"]).most_common()],
        "source_catalogues": [
            {"key": k, **{f: v[f] for f in ("label", "country", "site", "api", "route", "claim")}}
            for k, v in _S.SOURCES.items()],
        "surveyed_not_ingested": _S.SURVEY,
        "sources": [{"name": k, "count": v} for k, v in
                    collections.Counter(s for e in entries for s in e["sources"]).most_common()],
        "licences_spdx": [{"id": k, "count": v} for k, v in
                          collections.Counter(e["licence_spdx"] for e in entries
                                              if e["licence_spdx"]).most_common()],
        "replaces_disclaimer": replaces_raw["_README"]["status"],
        "confidence_values": replaces_raw["_README"]["confidence"],
        "kind_values": replaces_raw["_README"]["kind"],
        "files": {
            "entries": "/entries.json",
            "meta": "/meta.json",
            "by_product": "/by-product.json",
            "by_category": "/by-category/<category-key>.json",
            "sources": "/sources.json",
            "status": "/status.json",
            "versioned": "/v1/entries.json",
        },
        "known_gaps": {
            "note": "Absence is a finding: a category with no entries tells a European "
                    "public-sector audience where the gaps in their own commons are.",
            "no_results_observed_for": [
                "social media scheduling / management",
                "SMS / mass notification platforms",
                "mobile field data collection",
                "digital signage",
            ],
            "not_replaceable_by_software": [
                "managed hosting (Pantheon, WP Engine) — a CMS does not replace hosting",
                "training content subscriptions (LinkedIn Learning, Pluralsight, GO1) — "
                "an LMS does not produce course content",
            ],
            "unresolved_national_catalogues": ["IE", "PT", "CY"],
            "needs_api_key": ["NL"],
        },
        "replaces_seed_orphans": orphans,
    }

    os.makedirs(f"{SITE}/v1", exist_ok=True)
    os.makedirs(f"{SITE}/by-category", exist_ok=True)

    def w(path, obj):
        with open(f"{SITE}/{path}", "w") as f:
            json.dump(obj, f, indent=1, default=str)
        return os.path.getsize(f"{SITE}/{path}")

    # A COMPACT index for the MCP server, and only for it.
    #
    # entries.json is 5.6 MB. A Cloudflare Worker gets 10ms of CPU per request,
    # and JSON.parse runs at a few hundred MB/s, so parsing the full export does
    # not fit in the budget - the server would time out on a cold isolate. This
    # index carries only what search and lookup need (851 KB raw, 188 KB gzip,
    # ~3ms to parse) and is written HERE rather than assembled in the Worker, so
    # it cannot drift from what the site publishes: same build, same run.
    #
    # Keys are short because 3,070 of them repeat; this file is read by one
    # machine consumer, never by a human, and entries.json remains the readable
    # long-form export for everyone else.
    def compact(r):
        return {"id": r.get("id"), "n": r.get("name"),
                "d": (r.get("description") or "")[:180],
                "c": r.get("country"), "cs": r.get("countries") or [],
                "s": r.get("sources") or [], "f": r.get("functions") or [],
                "l": r.get("licence"), "u": r.get("repo_url"),
                "cc": r.get("catalogue_count", 1),
                "rp": [m.get("product") for m in (r.get("replaces") or [])
                       if m.get("product")],
                "x": 1 if r.get("link_dead") else 0}

    with open(f"{SITE}/mcp-index.json", "w") as f:
        json.dump({"generated_at": GENERATED_AT,
                   "entries": [compact(r) for r in active]},
                  f, separators=(",", ":"), ensure_ascii=False)

    sizes = {
        "mcp-index.json": os.path.getsize(f"{SITE}/mcp-index.json"),
        "entries.json": w("entries.json", entries),
        "meta.json": w("meta.json", meta),
        "by-product.json": w("by-product.json", dict(sorted(by_product.items()))),
        "v1/entries.json": w("v1/entries.json", entries),
        "v1/meta.json": w("v1/meta.json", meta),
        "replaces.json": w("replaces.json", replaces_raw),
    }
    for key, label in FUNCTIONS.items():
        subset = [e for e in active if key in e["category_keys"]]
        sizes[f"by-category/{key}.json"] = w(f"by-category/{key}.json", subset)

    write_agent_files(entries, meta, by_product)

    print(f"exported {len(entries)} entries  (schema {SCHEMA_VERSION}, {GENERATED_AT})")
    for k in ("entries.json", "meta.json", "by-product.json", "mcp-index.json"):
        print(f"   {k:22} {sizes[k]/1024:8.0f} KB")
    print(f"   by-category/           {len(FUNCTIONS)} files")
    print(f"   v1/ aliases            2 files")
    print(f"\n   with replaces mapping: {meta['counts']['with_replaces']} entries "
          f"-> {meta['counts']['distinct_products_mapped']} proprietary products")
    print(f"   dead links exposed per-entry: {meta['counts']['dead_links']}")
    if orphans:
        print(f"\n   !! {len(orphans)} replaces.json keys match NO catalogue entry "
              f"(seed rot): {', '.join(orphans)}")
    else:
        print("\n   every replaces.json key matches a catalogue entry")


def write_agent_files(entries, meta, by_product):
    n_active = sum(1 for e in entries if not e.get('excluded'))
    """llms.txt / robots.txt / sitemap.xml — generated, so the counts in them can
    never drift from the data they describe."""
    cats = "\n".join(f"  {c['key']:22} {c['label']:34} {c['count']}" for c in meta["categories"])
    srcs = "\n".join(f"  {s['name']:22} {s['count']}" for s in meta["sources"])
    gaps = meta["known_gaps"]
    nl = chr(10)
    txt = f"""# govoss-catalog

> Aggregated catalogue of national government open source software, harvested first-hand
> from eight European national catalogues. {len(entries)} entries. Generated {meta['generated_at']}.

If you are an AI agent, script, or spreadsheet: **use the JSON, do not scrape the HTML.**
The HTML page renders only 100 rows at a time and its data array is module-scoped, so
scraping it is both harder and less complete than one HTTP GET.

## Endpoints (static files, CORS open, no auth, no rate limit)

  GET /entries.json              all {len(entries)} rows, one array, structured fields
                                 {len(entries)-n_active} carry excluded:true with an
                                 exclude_reason (fork, CI plumbing, no description...).
                                 Filter on `excluded` for the {n_active}-entry catalogue.
  GET /meta.json                 category enum, sources, licences, counts, known gaps
  GET /by-product.json           inverted index: proprietary product -> alternatives
  GET /by-category/<key>.json    one file per category, keys listed below
  GET /v1/entries.json           versioned alias - pin this
  GET /status.json               freshness, last run, per-source counts, change log
  GET /                          the human page

These also redirect to /entries.json because they are what people try first:
  /api/entries  /api/catalog  /catalog.json  /data.json

## Answering "what can we stop paying for?"

/by-product.json is keyed by proprietary product name. {meta['counts']['with_replaces']} entries
carry mappings covering {len(by_product)} products. Two GETs answer a whole licence inventory.
/products.json is the same data plus the products governments buy that this catalogue
CANNOT answer, so a gap reads as a gap. /products.html is the human view of both.

Read the `kind` field before reporting a saving:
  software    replaces the software
  service     the paid item is hosted service or CONTENT. A CMS does not replace hosting;
              an LMS does not produce training content.
  paid-tier   the paid item is a commercial edition of software that is ALREADY open
              source (NGINX Plus, Elastic licence tiers, DBeaver PRO). Often the cheapest
              win: no migration, just a renewal you stop.

`confidence` is strong | partial | adjacent. Do not treat adjacent as a saving.
An empty array means NOT MAPPED, not "no European alternative exists".

## Honesty flags you should carry into anything you publish

  translated_from          ~74% of descriptions are MACHINE TRANSLATIONS from de/it/fr/fi/sv.
                           description_original holds the source wording.
  categories_inferred      true = category inferred by keyword rules, not declared upstream
  link_dead                repository URL confirmed gone over 2+ consecutive checks
  merged_from              how many catalogue records were merged into this entry
  licence_spdx             null where the upstream string was not a real SPDX id
                           ("GPLv3+", "MIT licence"). Use `licence` for the raw string.
  generated_at             build time. Harvest runs weekly; REDEPLOY IS MANUAL, so trust
                           generated_at over the deploy date.

## Categories ({len(meta['categories'])})

{cats}

## Sources

{srcs}

## Known gaps

Absence is a finding. Categories where the European commons appears to have nothing:
{nl.join('  - ' + g for g in gaps['no_results_observed_for'])}

Not replaceable by software at all:
{nl.join('  - ' + g for g in gaps['not_replaceable_by_software'])}

Unresolved national catalogues: {', '.join(gaps['unresolved_national_catalogues'])}
Pending an API key: {', '.join(gaps['needs_api_key'])}

The EU's own aggregate catalogue is deliberately NOT a source: its pager, facets and
search all ignore query strings, so only 20 of its 1,084 solutions are reachable.
"""
    open(f"{SITE}/llms.txt", "w").write(txt)
    open(f"{SITE}/robots.txt", "w").write(
        "User-agent: *\nAllow: /\n\n"
        "# Structured data - prefer these over parsing the HTML\n"
        "# /entries.json  /meta.json  /by-product.json  /status.json  /llms.txt\n"
        "Sitemap: https://govoss-catalog.vercel.app/sitemap.xml\n")
    # products.html/.json are written later by build_products.py, but they are
    # listed here because this is where the sitemap is generated. They are static
    # paths, so no ordering problem — only a missing-file one if that step fails,
    # and a failed step blocks the deploy anyway.
    urls = ["/", "/sources.html", "/api.html", "/products.html", "/entries.json",
            "/meta.json", "/by-product.json", "/products.json", "/llms.txt"]
    open(f"{SITE}/sitemap.xml", "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f'<url><loc>https://govoss-catalog.vercel.app{u}</loc>'
                  f'<lastmod>{meta["generated_at"][:10]}</lastmod></url>\n' for u in urls)
        + "</urlset>\n")


if __name__ == "__main__":
    build()

#!/usr/bin/env python3
"""Harvester for national public-sector open source catalogues.

Ingests each national source FIRST-HAND. Deliberately does NOT syndicate the
EU OSS Catalogue (interoperable-europe.ec.europa.eu/eu-oss-catalogue) — as of
2026-08-10 its pager, facets and keyword search all ignore query strings, so
only 20 of its 1084 solutions are reachable. See PAGINATION-BUG.md.

Two tiers, because the sources are not the same kind of thing:
  tier "publiccode" — a real publiccode.yml was parsed. Rich, comparable.
  tier "index"      — name/url/description only. Real coverage, thinner fields.

Join key is the normalized repository URL.

Usage:
    python3 harvest.py                  # all sources
    python3 harvest.py fr it de         # named sources only
    python3 harvest.py --liveness       # also HEAD-check every repo URL

Env:
    NL_API_KEY     x-api-key for the Dutch OSS register (see SOURCES['nl'])
    GITHUB_TOKEN   optional, raises the GitHub API rate limit
"""
import json, os, re, ssl, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

import certifi, yaml

CTX = ssl.create_default_context(cafile=certifi.where())
OUT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(OUT, "cache")
os.makedirs(CACHE, exist_ok=True)
UA = {"User-Agent": "govoss-catalog/0.2 (public-sector OSS catalogue harvester)"}


# ------------------------------------------------------------------ plumbing
def get(url, timeout=60, raw=False, headers=None, tries=3):
    h = dict(UA)
    h.update(headers or {})
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                b = r.read()
            return b if raw else json.loads(b)
        except urllib.error.HTTPError as e:
            if e.code in (404, 401, 403):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise last


def norm_repo(url):
    """Canonical join key: host+path, no scheme/www/.git/trailing slash."""
    if not url or not isinstance(url, str):
        return None
    u = re.sub(r"^https?://", "", url.strip().rstrip("/"))
    u = re.sub(r"^www\.", "", u)
    u = re.sub(r"\.git$", "", u)
    u = re.sub(r"/-/(tree|blob)/.*$", "", u)      # gitlab deep links
    u = re.sub(r"/(tree|blob)/.*$", "", u)        # github deep links
    return u.lower() or None


def rec(source, country, tier, name, repo, **kw):
    r = {"source": source, "country": country, "tier": tier,
         "name": name, "repo": repo, "repo_key": norm_repo(repo)}
    r.update({k: v for k, v in kw.items() if v not in (None, "", [], {})})
    return r


def base_lang(code):
    """it-IT / IT / en-US -> it / it / en. publiccode.yml is inconsistent here."""
    return (code or "").split("-")[0].lower() or None


def from_publiccode(pc, source, country, **kw):
    """Flatten a parsed publiccode.yml into the common record.

    Prefers an English description when the file ships one, and keeps the
    original-language text alongside it. The previous version took
    next(iter(desc)) — the FIRST key — which silently discarded English
    whenever it wasn't listed first.
    """
    desc = pc.get("description") or {}
    by_lang = {}
    for raw_lang, body in desc.items():
        if isinstance(body, dict):
            by_lang.setdefault(base_lang(raw_lang), body)

    en = by_lang.get("en")
    orig_lang = next((l for l in by_lang if l != "en"), None)
    orig = by_lang.get(orig_lang) or {}
    primary = en or orig

    legal = pc.get("legal") or {}
    maint = pc.get("maintenance") or {}
    return rec(
        source, country, "publiccode",
        name=pc.get("name"), repo=pc.get("url") or kw.pop("fallback_repo", None),
        landing=pc.get("landingURL"),
        license=legal.get("license"), repo_owner=legal.get("repoOwner"),
        categories=pc.get("categories") or [],
        platforms=pc.get("platforms") or [],
        software_type=pc.get("softwareType"),
        dev_status=pc.get("developmentStatus"),
        version=pc.get("softwareVersion"),
        released=str(pc.get("releaseDate")) if pc.get("releaseDate") else None,
        maintenance=maint.get("type"),
        contacts=[c.get("name") for c in (maint.get("contacts") or [])
                  if isinstance(c, dict) and c.get("name")],
        # desc_en is authoritative English straight from the source;
        # desc_src is the original wording, kept so a translation can be
        # checked and so nothing is lost when we translate the gaps.
        desc_en=(en.get("shortDescription") or "")[:400] if en else None,
        desc_src=(orig.get("shortDescription") or "")[:400] or None,
        desc_src_lang=orig_lang,
        short_desc=(primary.get("shortDescription") or "")[:400] if primary else None,
        desc_lang="en" if en else orig_lang,
        long_desc=(primary.get("longDescription") or "")[:1200] if primary else None,
        features=(primary.get("features") or [])[:8] if primary else [],
        used_by=(primary.get("usedBy") if primary else None) or pc.get("usedBy") or [],
        **kw)


def parse_pc(blob):
    try:
        pc = yaml.safe_load(blob.decode("utf-8", "replace") if isinstance(blob, bytes) else blob)
    except Exception:
        return None
    return pc if isinstance(pc, dict) and pc.get("name") else None


# ------------------------------------------------- generic forge adapters
def gitlab_scan(base, source, country, cap_pages=60, workers=12):
    """Any GitLab instance: list public projects, pull publiccode.yml from each.

    This is exactly how openCode.de builds its own directory, so it reproduces
    the official listing rather than approximating it.
    """
    api = f"{base}/api/v4"
    projs, page = [], 1
    while page <= cap_pages:
        d = get(f"{api}/projects?per_page=100&page={page}&simple=true&archived=false")
        if not d:
            break
        projs += d
        page += 1
    print(f"    {len(projs)} public projects on {base}")

    def one(p):
        if not p.get("default_branch"):
            return None
        ref = urllib.parse.quote(p["default_branch"], safe="")
        try:
            pc = parse_pc(get(f"{api}/projects/{p['id']}/repository/files/publiccode.yml/raw?ref={ref}",
                              timeout=30, raw=True, tries=2))
        except Exception:
            return None
        if not pc:
            return None
        # Do NOT construct an opencode.de/en/software/<slug>-<id> URL: the public
        # directory lists only ~270 of the 477 projects carrying a publiccode.yml,
        # so a constructed link 404s for ~40% of them. The GitLab project page
        # always exists and is what the directory is generated from.
        entry = p.get("web_url")
        return from_publiccode(pc, source, country,
                               fallback_repo=p.get("http_url_to_repo"),
                               upstream_id=p["id"],
                               forge_path=p.get("path_with_namespace"),
                               entry_url=entry,
                               last_activity=p.get("last_activity_at"))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        out = [r for r in ex.map(one, projs) if r]
    return out, len(projs)


def github_org_scan(org, source, country, workers=12):
    """GitHub org: list repos, then hit raw.githubusercontent (not rate-limited
    like the REST API, so a 380-repo org costs 4 API calls, not 380)."""
    hdr = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        hdr["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    repos, page = [], 1
    while page <= 20:
        d = get(f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}",
                headers=hdr)
        if not d:
            break
        repos += d
        page += 1
    repos = [r for r in repos if not r.get("archived")]
    # fork status is the reliable signal for "this is an upstream project this
    # org mirrors, not software this org produced" — 30 of iMio's 236 are forks
    # (ZODB, zope.sendmail, Products.CMFEditions, puppetlabs-vcsrepo...).
    # Recorded, not dropped here; filters.py decides.
    print(f"    {len(repos)} non-archived repos in github.com/{org}")

    def one(r):
        pc = None
        try:
            pc = parse_pc(get(f"https://raw.githubusercontent.com/{org}/{r['name']}/HEAD/publiccode.yml",
                              timeout=25, raw=True, tries=1))
        except Exception:
            pass
        if pc:
            return from_publiccode(pc, source, country,
                                   fallback_repo=r.get("html_url"),
                                   entry_url=r.get("html_url"),
                                   stars=r.get("stargazers_count"),
                                   last_activity=r.get("pushed_at"),
                                   is_fork=bool(r.get("fork")))
        # iMio publishes almost no publiccode.yml, but the repos are still
        # genuine public-sector OSS — index them rather than drop them.
        return rec(source, country, "index", r.get("name"), r.get("html_url"),
                   repo_owner=org, license=(r.get("license") or {}).get("spdx_id"),
                   entry_url=r.get("html_url"),
                   short_desc=(r.get("description") or "")[:400],
                   # GitHub repo descriptions in this org are written in English;
                   # tag it so language-gap detection does not skip these rows.
                   desc_lang="en",
                   stars=r.get("stargazers_count"), last_activity=r.get("pushed_at"),
                   is_fork=bool(r.get("fork")))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        out = [x for x in ex.map(one, repos) if x]
    return out, len(repos)


# ---------------------------------------------------------- national sources
def fr():
    """France — bulk JSON dumps.

    NOT ingested: code.gouv.fr/data/repositories/json/all.json (24,440 repos).
    That dump answers "who published this?", not "is this useful to a
    government". It is a provenance inventory of everything French public
    bodies have on a forge — 45% with no description, 80% with no licence,
    dominated by research code (INRIA, medialab, InseeFrLab) — and only 18 of
    its entries carry a publiccode.yml. Dropped deliberately, not overlooked;
    re-add it as an enrichment join (it has is_archived / last_update /
    software_heritage_url per repo) rather than as catalogue entries.
    """
    out = []
    for pc in get("https://code.gouv.fr/data/awesome-codegouvfr.json"):
        out.append(from_publiccode(pc, "FR/awesome-codegouvfr", "FR"))
    print(f"    awesome (publiccode): {len(out)}")

    # SILL = Socle Interministériel de Logiciels Libres: software formally
    # RECOMMENDED to French public agents. Mostly general-purpose OSS (7-Zip,
    # Ansible, Audacity) rather than gov-authored, so it is a recommendation
    # axis, not a provenance one — but it is squarely "useful to government".
    #
    # Use /sill/api/sill.json, NOT /data/sill.json. The latter is a reduced
    # export with 524 entries and NO url field at all — its `u` key is an
    # update timestamp, which an earlier version of this script mistook for a
    # repository URL, giving every SILL row a date as its identity. The rich
    # export has 668 entries and carries Wikidata QIDs, which is what makes
    # these joinable to the other catalogues at all.
    sill = get("https://code.gouv.fr/sill/api/sill.json", timeout=120)
    print(f"    SILL (recommended for public agents): {len(sill)}")
    n_qid = 0
    for s in sill:
        ext = s.get("softwareExternalData") or {}
        qid = ext.get("externalId") if ext.get("sourceSlug") == "wikidata" else None
        n_qid += bool(qid)
        lv = s.get("latestVersion") or {}
        out.append(rec("FR/sill", "FR", "index", s.get("name"),
                       ext.get("codeRepositoryUrl"),
                       landing=ext.get("url"),
                       wikidata=qid,
                       sill_id=s.get("id"),
                       license=s.get("license"),
                       categories=s.get("categories") or [],
                       keywords=(s.get("keywords") or [])[:10],
                       short_desc=(s.get("description") or "")[:400],
                       desc_lang="fr",
                       desc_src=(s.get("description") or "")[:400] or None,
                       desc_src_lang="fr",
                       version=lv.get("semVer"),
                       used_by=sorted((s.get("userAndReferentCountByOrganization") or {}).keys()),
                       recommended_for_gov=True,
                       entry_url="https://code.gouv.fr/sill/detail?name="
                                 + urllib.parse.quote(s.get("name") or ""),
                       note="recommended to public agents; not necessarily gov-authored"))
    print(f"      with Wikidata QID: {n_qid}/{len(sill)}")
    return out


def it():
    """Italy — a real REST API. The best of the eight."""
    out, url = [], "https://api.developers.italia.it/v1/software?page%5Bsize%5D=100"
    while url:
        d = get(url)
        for x in d["data"]:
            pc = parse_pc(x.get("publiccodeYml") or "")
            if not pc:
                continue
            v = x.get("vitality")
            out.append(from_publiccode(pc, "IT/developers-italia", "IT",
                                       fallback_repo=x.get("url"),
                                       upstream_id=x.get("id"),
                                       active=x.get("active"),
                                       vitality=v[-1] if isinstance(v, list) and v else v))
        nx = d["links"].get("next")
        url = ("https://api.developers.italia.it/v1/software" + nx
               ).replace("[", "%5B").replace("]", "%5D") if nx else None
    return out


def de():
    out, _ = gitlab_scan("https://gitlab.opencode.de", "DE/openCode", "DE")
    return out


def eu():
    out, _ = gitlab_scan("https://code.europa.eu", "EU/code.europa.eu", "EU")
    return out


def be():
    out, _ = github_org_scan("IMIO", "BE/iMio", "BE")
    return out


def fi():
    """Finland — three static JSON files behind avoinkoodi.fi. Not publiccode."""
    out = []
    for f, kind in [("projects.json", "national"),
                    ("municipalityprojects.json", "municipal"),
                    ("eduprojects.json", "education")]:
        d = get(f"https://avoinkoodi.fi/{f}")
        rows = next(iter(d.values())) if isinstance(d, dict) else d
        for r in rows:
            out.append(rec("FI/avoinkoodi", "FI", "index",
                           r.get("project"), r.get("code_url"),
                           repo_owner=r.get("owner"),
                           landing=r.get("service_url") or r.get("url"),
                           license=r.get("license"),
                           short_desc=(r.get("description") or "")[:400],
                           segment=kind))
        print(f"    {f}: {len(rows)}")
    return out


def se():
    """Sweden — GNU recutils DB, git-versioned. Unusual format, very durable."""
    proj = "open-data-knowledge-sharing%2Fkatalogen"
    br = get(f"https://gitlab.com/api/v4/projects/{proj}")["default_branch"]
    blob = get(f"https://gitlab.com/api/v4/projects/{proj}/repository/files/"
               f"db%2Fprogramvaror.rec/raw?ref={br}", raw=True).decode("utf-8", "replace")
    out, cur = [], {}
    for line in blob.splitlines():
        if not line.strip():
            if cur.get("Name"):
                out.append(rec("SE/offentligkod", "SE", "index",
                               cur.get("Name"), cur.get("Url"),
                               short_desc=(cur.get("Description") or "")[:400],
                               categories=cur.get("Keyword", "").split() if cur.get("Keyword") else [],
                               has_publiccode=bool(cur.get("Publiccode")),
                               used_by=cur.get("User_list", [])))
            cur = {}
            continue
        if line.startswith(("%", "+")):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "User":
                cur.setdefault("User_list", []).append(v)
            else:
                cur[k] = v
    if cur.get("Name"):
        out.append(rec("SE/offentligkod", "SE", "index", cur.get("Name"), cur.get("Url"),
                       short_desc=(cur.get("Description") or "")[:400]))
    return out


def nl_forgejo():
    """Netherlands — code.overheid.nl, the government's own self-hosted Forgejo.

    Found while surveying globally, and it makes the API-key problem moot: this is
    Gitea/Forgejo 1.22 with the standard OPEN api/v1, no auth. The OSS *register*
    (api.developer.overheid.nl) still needs a key and still 401s; this is the code
    platform itself, which is arguably the better source anyway — first-hand repos
    rather than a register of pointers.
    """
    api = "https://code.overheid.nl/api/v1"
    repos, page = [], 1
    while page <= 40:
        d = get(f"{api}/repos/search?limit=50&page={page}")
        batch = (d or {}).get("data") or []
        if not batch:
            break
        repos += batch
        page += 1
    repos = [r for r in repos if not r.get("archived")]
    print(f"    {len(repos)} non-archived repos on code.overheid.nl (Forgejo)")

    def one(r):
        br = r.get("default_branch") or "main"
        try:
            pc = parse_pc(get(f"{api}/repos/{r['full_name']}/raw/publiccode.yml?ref={br}",
                              timeout=25, raw=True, tries=1))
        except Exception:
            pc = None
        if pc:
            return from_publiccode(pc, "NL/code.overheid.nl", "NL",
                                   fallback_repo=r.get("html_url"),
                                   entry_url=r.get("html_url"),
                                   forge_path=r.get("full_name"),
                                   is_fork=bool(r.get("fork")),
                                   last_activity=r.get("updated_at"))
        return rec("NL/code.overheid.nl", "NL", "index", r.get("name"), r.get("html_url"),
                   entry_url=r.get("html_url"),
                   repo_owner=(r.get("owner") or {}).get("login"),
                   short_desc=(r.get("description") or "")[:400],
                   desc_lang="nl" if r.get("description") else None,
                   desc_src=(r.get("description") or "")[:400] or None,
                   desc_src_lang="nl" if r.get("description") else None,
                   forge_path=r.get("full_name"),
                   is_fork=bool(r.get("fork")),
                   stars=r.get("stars_count"),
                   last_activity=r.get("updated_at"))

    with ThreadPoolExecutor(max_workers=8) as ex:
        out = [x for x in ex.map(one, repos) if x]
    print(f"    -> {sum(1 for x in out if x['tier']=='publiccode')} with publiccode.yml")
    return out


def ca():
    """Canada — code.open.canada.ca/code.json.

    Uses the federal `code.json` schema (the format the retired US code.gov defined),
    but nested by government tier: tier -> adminCode -> {releases: [...]}. Covers
    federal, provincial, municipal and Indigenous administrations.
    """
    def loc(v, prefer="en"):
        """Canada localises name and tags: {"en": .., "fr": ..}. Flatten to the
        English value (then French), because every downstream step assumes a
        string — taxonomy, filters and dedupe all crashed on the raw dict."""
        if isinstance(v, dict):
            return v.get(prefer) or v.get("fr") or next(iter(v.values()), None)
        return v

    d = get("https://code.open.canada.ca/code.json", timeout=90)
    out = 0
    recs = []
    for tier, orgs in (d or {}).items():
        if not isinstance(orgs, dict):
            continue
        for admin, body in orgs.items():
            for rel in (body or {}).get("releases") or []:
                desc = rel.get("description") or {}
                wid = desc.get("whatItDoes") or {}
                text = wid.get("en") or wid.get("fr") or ""
                lang = "en" if wid.get("en") else ("fr" if wid.get("fr") else None)
                perms = rel.get("permissions") or {}
                lic = None
                for l in (perms.get("licenses") or []):
                    lic = l.get("name") or l.get("spdxID") or lic
                tags = loc(rel.get("tags")) or []
                if isinstance(tags, str):
                    tags = [tags]
                recs.append(rec("CA/code.open.canada.ca", "CA", "index",
                                loc(rel.get("name")), loc(rel.get("repositoryURL")),
                                landing=loc(rel.get("homepageURL")),
                                repo_owner=loc(rel.get("organization")) or admin,
                                license=loc(lic),
                                short_desc=text[:400] or None,
                                desc_lang=lang,
                                desc_src=text[:400] or None,
                                desc_src_lang=lang,
                                keywords=[t for t in tags if isinstance(t, str)][:10],
                                dev_status=rel.get("status"),
                                gov_tier=tier,
                                note=f"{tier} administration ({admin})"))
                out += 1
    print(f"    {out} releases across "
          f"{sum(1 for t,o in (d or {}).items() if isinstance(o,dict) and o)} tiers")
    return recs


def nl_register():
    """Netherlands OSS *register* — needs an API key (401 on every read).

    Kept because it is a different dataset (a curated register, not a forge), but
    nl_forgejo() covers NL without a key so this is no longer blocking.

    Request one via oss.developer.overheid.nl, then export NL_API_KEY.
    Spec: github.com/developer-overheid-nl/don-oss-register api/openapi.json
    """
    key = os.environ.get("NL_API_KEY")
    if not key:
        print("    SKIPPED — set NL_API_KEY (register at oss.developer.overheid.nl)")
        return []
    out, page = [], 1
    while page <= 100:
        d = get(f"https://api.developer.overheid.nl/oss-register/v1/repositories"
                f"?page={page}&perPage=100", headers={"x-api-key": key})
        items = d.get("repositories") or d.get("data") or d.get("items") or []
        if not items:
            break
        for r in items:
            pc = r.get("publiccode") or r.get("publiccodeYml")
            if isinstance(pc, dict) and pc.get("name"):
                out.append(from_publiccode(pc, "NL/developer.overheid", "NL",
                                           fallback_repo=r.get("url")))
            else:
                out.append(rec("NL/developer.overheid", "NL", "index",
                               r.get("name"), r.get("url"),
                               repo_owner=(r.get("organisation") or {}).get("name")
                               if isinstance(r.get("organisation"), dict) else r.get("organisation"),
                               license=r.get("license"),
                               short_desc=(r.get("description") or "")[:400],
                               last_activity=r.get("lastChange") or r.get("updatedAt")))
        page += 1
    return out


def dpg():
    """Digital Public Goods Registry — global, UN-affiliated (digitalpublicgoods.net).

    Widens the catalogue's criterion: DPGs are vetted against the DPG Standard for
    relevance to the SDGs, and many are NGO- or university-built rather than
    government-published. Included as a deliberate scope decision, and tagged
    `dpg: True` plus country "GLOBAL" so it can be filtered back out.

    All 249 entries carry a repository and an OSI licence, which makes them join
    cleanly against the national catalogues on repo URL.
    """
    d = get("https://app.digitalpublicgoods.net/api/dpgs", timeout=120)
    rows = d if isinstance(d, list) else (d.get("data") or [])

    # The registry slug is NOT derivable from the API name (the API says
    # "NextCloud Server", the registry serves /r/nextcloud), and the index page is
    # JS-paginated so scraping it yielded only 20 of 249 slugs. So HEAD-check each
    # candidate: 249 cheap requests buys a guarantee of zero broken deep links,
    # which is the same standard the liveness monitor holds itself to.
    def slugify(n):
        return re.sub(r"[^a-z0-9]+", "-", (n or "").lower()).strip("-")

    def verify(name):
        parts = slugify(name).split("-")
        for i in range(len(parts), 0, -1):
            cand = "-".join(parts[:i])
            if not cand:
                continue
            u = f"https://www.digitalpublicgoods.net/r/{cand}"
            try:
                req = urllib.request.Request(u, method="HEAD",
                                             headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
                    if r.status == 200:
                        return u
            except Exception:
                pass
        return None

    names = [r.get("name") or "" for r in rows]
    with ThreadPoolExecutor(max_workers=10) as ex:
        verified = dict(zip(names, ex.map(verify, names)))
    print(f"    {sum(1 for v in verified.values() if v)}/{len(names)} registry deep links verified")
    print(f"    {len(rows)} DPGs")
    out = []
    for r in rows:
        name = r.get("name") or ""
        repos = r.get("repositories") or []
        repo = next((x.get("url") for x in repos if x.get("url")), None)
        lic = next((x.get("openLicense") for x in (r.get("openlicenses") or [])
                    if x.get("openLicense")), None)
        locs = r.get("locations") or {}
        deployed = locs.get("deploymentCountries") or []
        sdgs = (r.get("sdgs") or {}).get("sdg") or []
        orgs = [o.get("name") for o in (r.get("organizations") or []) if o.get("name")]
        # verified pattern: /r/<name lowercased, non-alphanumerics -> hyphen>
        entry = verified.get(name)
        out.append(rec("GLOBAL/dpg", "GLOBAL", "index", name, repo,
                       landing=r.get("website"),
                       entry_url=entry,
                       license=lic,
                       short_desc=(r.get("description") or "")[:400] or None,
                       desc_lang="en",
                       dpg_type=[c for c in (r.get("categories") or []) if isinstance(c, str)],
                       keywords=[x.split(":")[0] for x in sdgs if isinstance(x, str)][:10],
                       repo_owner=orgs[0] if orgs else None,
                       # deployment countries are the closest thing to adopters here,
                       # and for a government buyer that is the trust signal
                       used_by=sorted(deployed)[:60],
                       sdgs=sdgs,
                       dpg=True,
                       upstream_id=r.get("dpgid"),
                       note="Digital Public Good (DPG Standard); may be NGO- or "
                            "university-built rather than government-published"))
    return out


SOURCES = {"fr": fr, "it": it, "de": de, "eu": eu, "be": be, "fi": fi,
           "se": se, "nl": nl_forgejo, "ca": ca, "dpg": dpg, "nlreg": nl_register}

# Reachable, but no machine route found yet — the EU catalogue lists them as
# source catalogues, and its own search is broken, so they can't be resolved
# from there either. Left as TODO rather than silently dropped.
UNRESOLVED = {"IE": "Ireland", "PT": "Portugal", "CY": "Cyprus"}


# ---------------------------------------------------------------- liveness
def liveness(catalog, workers=25, timeout=8):
    """The differentiated bit: national catalogues record what was published,
    nobody checks whether it still exists."""
    seen, targets = set(), []
    for r in catalog:
        if r.get("repo") and r["repo_key"] not in seen:
            seen.add(r["repo_key"])
            targets.append(r)

    def check(r):
        try:
            req = urllib.request.Request(r["repo"], method="HEAD",
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as x:
                return r["repo_key"], x.status
        except urllib.error.HTTPError as e:
            return r["repo_key"], e.code
        except Exception as e:
            return r["repo_key"], type(e).__name__
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(check, targets))


# -------------------------------------------------------------------- main
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # --from-cache rebuilds catalog.json from the per-source checkpoints without
    # touching the network. Lets the downstream steps (translate/taxonomy/filter/
    # dedupe) be re-run cheaply and politely while iterating on them.
    want = [] if "--from-cache" in sys.argv else (args or list(SOURCES))
    t0, catalog, failed = time.time(), [], {}
    if "--from-cache" in sys.argv:
        print("[--from-cache] no network; assembling from existing checkpoints")

    # Per-source checkpointing. A source that succeeds is persisted immediately,
    # so a network blip late in the run can never destroy earlier good data —
    # and catalog.json is always assembled from every checkpoint on disk, not
    # just the sources requested this time.
    for k in want:
        if k not in SOURCES:
            print(f"unknown source {k!r}; known: {', '.join(SOURCES)}")
            sys.exit(2)
        print(f"[{k.upper()}]")
        try:
            got = SOURCES[k]()
            json.dump(got, open(f"{CACHE}/src_{k}.json", "w"), indent=1, default=str)
            print(f"    -> {len(got)} records (checkpointed)")
        except Exception as e:
            failed[k] = f"{type(e).__name__}: {e}"
            print(f"    !! FAILED {failed[k]}")

    for k in SOURCES:
        f = f"{CACHE}/src_{k}.json"
        if os.path.exists(f):
            got = json.load(open(f))
            catalog += got
            if k not in want or k in failed:
                print(f"[{k.upper()}] reused checkpoint: {len(got)} records")

    if "--liveness" in sys.argv:
        print("[liveness] HEAD-checking every distinct repo URL…")
        live = liveness(catalog)
        for r in catalog:
            r["http_status"] = live.get(r["repo_key"])

    json.dump(catalog, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)

    pc = [r for r in catalog if r["tier"] == "publiccode"]
    print(f"\n{'='*64}\n{len(catalog)} records in {round(time.time()-t0)}s "
          f"({len(pc)} publiccode-tier, {len(catalog)-len(pc)} index-tier)")
    print(f"distinct repos: {len({r['repo_key'] for r in catalog if r['repo_key']})}")
    if failed:
        print("FAILED SOURCES:", json.dumps(failed, indent=1))
    print(f"unresolved catalogues: {', '.join(UNRESOLVED.values())}")
    print(f"written: {OUT}/catalog.json")

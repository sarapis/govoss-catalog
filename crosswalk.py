#!/usr/bin/env python3
"""Enrich entry IDENTITY from Comptoir du Libre and Wikidata, so dedupe can merge more.

Runs BEFORE dedupe.py and adds nothing to coverage — it only fills in Wikidata
QIDs that entries were missing. dedupe unions on QID first and repo URL second,
so an entry with no QID can only merge with something sharing its exact repo URL.
That is why the same upstream tool listed by two catalogues with slightly
different repo URLs (angular.io vs angular.dev, a mirror vs the canonical) stays
split.

Comptoir du Libre (comptoir-du-libre.org, run by ADULLACT) is the one open source
that carries several identifiers on the SAME row: 780 entries, all with a
repository URL and a website, 270 with a Wikidata QID and 349 with a SILL id. So
it can bridge repo URL -> QID and SILL id -> QID.

Wikidata itself is the second source, reached over SPARQL by URL, never by name:

  P1324 source code repository  -> our repo_key
  P856  official website        -> our landing

WHY NOT BY NAME. Tried and rejected, with the evidence:
  * Q936 (OpenStreetMap) has NO English label at all, so a label lookup misses
    the very case that prompted this.
  * "Audacity" resolves to three different QIDs and "Caddy" to two. An ambiguous
    identity is worse than none.
  * "about" matches a real software item called `about`. Generic repo names are
    everywhere in this catalogue (`docs`, `api`, `about`) and every one of them
    is a live false positive.

MEASURED YIELD, so nobody re-litigates this expecting more:
  * repo route:    ~51 QIDs stamped, but only ONE extra merge. By construction —
    entries sharing a repo URL ALREADY merge on repo URL, so a QID derived from
    that same URL tells dedupe nothing it did not know. The QIDs are still worth
    having as identity for consumers.
  * website route: ~27 QIDs, ~0 extra merges after the guard below.
The routes are worth running for identity coverage. They are NOT the fix for
duplicate entries — see the note at the end of this file.

URL PROPERTIES ARE IRIs, NOT STRINGS. `VALUES ?s { "https://..." }` silently
matches nothing; it has to be `VALUES ?s { <https://...> }`. And Wikidata stores
one exact spelling, so each candidate is expanded over scheme x www x trailing
slash before being sent.

Every stamped QID records `wikidata_via: comptoir:<how>` or `wikidata:<how>` so an
inferred identity is never mistaken for one the publisher asserted — the same rule
as translated vs desc_en, and inferred vs source categories.

Wikidata is BEST EFFORT: any failure warns and leaves the Comptoir result in
place. This is a gated step in run.sh, and a third-party SPARQL endpoint being
slow must never block the deploy.
"""
import calendar, collections, json, os, re, time

OUT = os.path.dirname(os.path.abspath(__file__))
SRC = f"{OUT}/out/comptoir.json"
API = "https://comptoir-du-libre.org/api/v1/softwares.json"
WD_REPO_CACHE = f"{OUT}/out/wikidata_repo.json"
WD_SITE_CACHE = f"{OUT}/out/wikidata_site.json"
CACHE_STATE = f"{OUT}/out/crosswalk_cache.json"
# The weekly run refreshes every input; a same-week manual run reuses them.
MAX_AGE_DAYS = 6
WDQS = "https://query.wikidata.org/sparql"
UA = "govoss-catalog/0.2 (https://github.com/sarapis/govoss-catalog)"


def norm(url):
    """Same normalisation as harvest.norm_repo, kept local so this step has no
    import-time dependency on the harvester."""
    if not url or not isinstance(url, str):
        return None
    u = re.sub(r"^https?://", "", url.strip().rstrip("/"))
    u = re.sub(r"^www\.", "", u)
    u = re.sub(r"\.git$", "", u)
    u = re.sub(r"/-/(tree|blob)/.*$", "", u)
    u = re.sub(r"/(tree|blob)/.*$", "", u)
    return u.lower() or None


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _age_days(ts, now=None):
    """Days since `ts`, or None when there is no usable stamp. None means STALE:
    a missing measurement is not a fresh one."""
    try:
        t = calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
        n = calendar.timegm(time.strptime(now or _now(), "%Y-%m-%dT%H:%M:%SZ"))
        return (n - t) / 86400
    except Exception:
        return None


def _load_state(path=None):
    try:
        return json.load(open(path or CACHE_STATE))
    except Exception:
        return {}


def _save_state(state, path=None):
    os.makedirs(os.path.dirname(path or CACHE_STATE), exist_ok=True)
    json.dump(state, open(path or CACHE_STATE, "w"), indent=1, sort_keys=True)


def cached(name, path, fetch, state, now=None, max_age=MAX_AGE_DAYS):
    """Return the cached copy of one crosswalk input, refreshing it when old.

    WHY. Until 2026-09-23 every input here was reused for as long as its file
    existed: comptoir.json dated from 08-11 and the Wikidata files from 08-13,
    six weeks of weekly runs later, and nothing said so. A frozen input that
    looks live is the fourth recurring bug in CLAUDE.md.

    The rules, each pinned by test_crosswalk_cache.py:
      * no `fetched_at` recorded = stale, never fresh;
      * `fetched_at` advances ONLY on a successful fetch - the same invariant as
        cache/_fetched.json - so a failure cannot make old data look new;
      * a failed fetch falls back to the old copy (this step never fails the
        run) and records `error`, which /sources.html reports once it is old;
      * no old copy and a failed fetch raises, so the caller's best-effort
        handler decides, exactly as before."""
    rec = state.get(name) or {}
    age = _age_days(rec.get("fetched_at"), now)
    if os.path.exists(path) and age is not None and age < max_age:
        return json.load(open(path))
    try:
        data = fetch()
    except Exception as ex:
        state[name] = dict(rec, error=f"{type(ex).__name__}: {ex}"[:300])
        if not os.path.exists(path):
            raise
        print(f"   {name}: refresh failed ({state[name]['error']}); using the copy "
              f"from {rec.get('fetched_at') or 'an unrecorded date'}")
        return json.load(open(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w"))
    state[name] = {"fetched_at": now or _now(), "error": None}
    return data


def _fetch_comptoir():
    import ssl, urllib.request, certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(API, headers={"User-Agent": "govoss-catalog/0.2"})
    with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
        return json.load(r)


def load_comptoir(state):
    d = cached("comptoir", SRC, _fetch_comptoir, state)
    rows = d if isinstance(d, list) else (d.get("softwares") or list(d.values())[0])
    if rows and isinstance(rows[0], dict) and "software" in rows[0]:
        rows = [r["software"] for r in rows]
    return rows


def _sparql(query, timeout=300):
    """POST, not GET: the VALUES blocks below run to tens of kilobytes and a GET
    returns 414 URI Too Long."""
    import ssl, urllib.request, urllib.parse, certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(WDQS, data=data, headers={
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return json.load(r)["results"]["bindings"]


def _qid(binding):
    return binding["value"].rsplit("/", 1)[-1]


def _variants(bare):
    """Wikidata records one exact spelling of a URL; we hold a normalised one.
    Expand ours over the axes norm() collapsed so an exact IRI match can hit."""
    return {f"{s}{w}{bare}{t}"
            for s in ("https://", "http://") for w in ("", "www.") for t in ("", "/")}


def _iri_safe(u):
    """A URL with a space, quote or angle bracket breaks SPARQL IRI syntax and
    fails the WHOLE chunk with a 400. Drop those rather than lose 200 good ones."""
    return u and not re.search(r'[\s<>"{}|\\^`]', u)


def software_qids(qids, chunk=300):
    """Keep only the QIDs that are software.

    LOAD-BEARING, not tidiness. A URL match says "this page belongs to that
    item", not "that item is the software". Of 92 homepages matched by P856, 17
    resolved to something that is not software at all: Q1199 is the German state
    of Hesse (an entry's landing was hessen.de), plus an Italian municipality, a
    Taiwanese ministry, an elementary school and an academic publisher. Each was
    a wrong identity, and a wrong identity is what makes dedupe merge unrelated
    entries later.

    Asked only about the handful of items a URL actually matched — the same
    constraint asked over all of Wikidata times out (504).

    -> (software, unverified). A batch that fails twice is UNVERIFIED, not
    rejected and not accepted: its QIDs are not stamped this run, and the rest
    still are. Until 2026-09-23 one 503 here raised out of the whole Wikidata
    stage and cost every website and repo stamp for the week."""
    if not qids:
        return set(), set()
    out, unverified = set(), set()
    qids = sorted(qids)
    for i in range(0, len(qids), chunk):
        batch = qids[i:i + chunk]
        vals = " ".join("wd:%s" % q for q in batch)
        try:
            rows = _sparql_twice("SELECT DISTINCT ?item WHERE { VALUES ?item { %s } "
                                 "?item wdt:P31/wdt:P279* wd:Q7397 . }" % vals, timeout=300)
        except Exception as ex:
            print(f"   wikidata: software check failed for {len(batch)} items ({ex}); "
                  f"not stamping them this run")
            unverified |= set(batch)
            continue
        out |= {_qid(b["item"]) for b in rows}
    return out, unverified


def _sparql_twice(query, timeout=120, pause=5):
    """One retry for any SPARQL failure. Unlike _retry_once(), an HTTP error is
    retried too: from the query service a 429, 502 or 503 is load, not an answer."""
    try:
        return _sparql(query, timeout=timeout)
    except Exception:
        time.sleep(pause)
        return _sparql(query, timeout=timeout)


def site_lookup(sites, ask, cache, fresh):
    """Which homepages to send, and the merged result. Pure; `ask(batch)` is the
    network and returns {norm site: {qid}} or raises.

    The cache records the homepages it ASKED, not only the ones that matched.
    Before 2026-09-23 it stored matches alone, so a homepage added after the
    cache was written was never sent at all - not "asked and not found", simply
    never asked. While the cache is fresh only the new homepages go out; once it
    is stale, all of them. A failed batch is left un-asked so the next run
    retries it. -> (new cache, number of failed batches)."""
    prior_asked = set(cache.get("asked") or [])
    prior_found = cache.get("found") or {}
    want = {x for x in sites if x}
    todo = sorted(want - prior_asked) if fresh else sorted(want)
    newly, got_all, failed = set(), collections.defaultdict(set), 0
    for batch in ask.batches(todo):
        try:
            got = ask(batch)
        except Exception as ex:                          # one bad chunk, not the run
            print(f"   wikidata: website batch failed ({ex})")
            failed += 1
            continue
        for k, v in got.items():
            got_all[k] |= set(v)
        newly |= set(batch)
    # An answer supersedes the old one; a homepage that went un-answered (failed
    # batch) keeps its old match rather than losing its identity for a week.
    found = {k: set(v) for k, v in prior_found.items()
             if k not in newly and (fresh or k in want)}
    for k, v in got_all.items():
        found[k] = set(v)
    asked = (prior_asked if fresh else set()) | newly
    return {"asked": sorted(asked),
            "found": {k: sorted(v) for k, v in sorted(found.items())}}, failed


class _AskWikidata:
    """<property> URL -> QID, asked only about URLs we hold (P856 official website).
    One retry per batch: the endpoint answers 502/503 under load and a second try
    a few seconds later usually lands."""
    def __init__(self, prop, chunk=200):
        self.prop, self.chunk = prop, chunk

    def batches(self, cands):
        return [cands[i:i + self.chunk] for i in range(0, len(cands), self.chunk)]

    def __call__(self, batch):
        vals = " ".join("<%s>" % v for b in batch for v in sorted(_variants(b)) if _iri_safe(v))
        found = collections.defaultdict(set)
        if not vals:
            return found
        q = "SELECT ?item ?s WHERE { VALUES ?s { %s } ?item wdt:%s ?s . }" % (vals, self.prop)
        rows = _sparql_twice(q)
        for b in rows:
            found[norm(b["s"]["value"])].add(_qid(b["item"]))
        return found


def wikidata_by_url(name, path, ask, urls, state, now=None):
    """The website route's refresh: an asked-set cache under
    `path`, the clock under state[name]. -> {norm url: qid}, one-claim only."""
    rec = state.get(name) or {}
    age = _age_days(rec.get("fetched_at"), now)
    fresh = age is not None and age < MAX_AGE_DAYS
    try:
        cache = json.load(open(path))
    except Exception:
        cache = {}
    if not isinstance(cache, dict) or "asked" not in cache:
        # the pre-2026-09-23 shape: {site: [qid]}, matches only, no asked set.
        # Keep its matches as the fallback and re-ask everything.
        cache, fresh = {"asked": [], "found": cache or {}}, False
    cache, failed = site_lookup(urls, ask, cache, fresh)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(cache, open(path, "w"))
    if failed:
        state[name] = dict(rec, error=f"{failed} batch(es) failed")
    elif not fresh:
        # a FULL refresh that fully succeeded is the only thing that restarts the clock
        state[name] = {"fetched_at": now or _now(), "error": None}
    # One url claimed by two items is not an identity. Drop it.
    return {k: v[0] for k, v in cache["found"].items() if len(v) == 1 and k in urls}


def p1324_rows(text, expected):
    """Parse the P1324 CSV dump -> [[qid, url]], or raise if it is incomplete.

    The query service TRUNCATES under load and still answers HTTP 200: measured
    2026-09-23, one download returned all 28,759 rows in 10s and the next, a
    minute later, 11,116 rows cut off mid-line. A responding endpoint is not a
    working source (CLAUDE.md, recurring bug 1), so the dump is checked against
    a separate COUNT. The 0.5% slack absorbs edits landing between the two
    queries; a truncation is never that small."""
    import csv, io
    if not text.endswith("\n"):
        text = text[:text.rfind("\n") + 1]        # drop a half-written last row
    rows = [[_qid({"value": r["item"]}), r["r"]]
            for r in csv.DictReader(io.StringIO(text)) if r.get("item") and r.get("r")]
    if len(rows) < expected * 0.995:
        raise RuntimeError(f"P1324 dump truncated: {len(rows)} of {expected} rows")
    return rows


def _sparql_csv(query, timeout=200):
    import ssl, urllib.request, urllib.parse, certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(WDQS, data=data, headers={
        "User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/csv"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read().decode("utf-8", "replace")


def _fetch_p1324(tries=3):
    """Every P1324 value on Wikidata, as CSV (a third of the JSON's size), checked
    complete. Asking per repo instead was measured and rejected: 25 repos took
    29s and 50 got a 502, so the ~3,000 we hold would take about an hour."""
    n = int(_sparql_csv("SELECT (COUNT(*) AS ?n) WHERE { ?item wdt:P1324 ?r . }")
            .split("\n")[1].strip())
    last = None
    for i in range(tries):
        try:
            return p1324_rows(_sparql_csv("SELECT ?item ?r WHERE { ?item wdt:P1324 ?r . }"), n)
        except Exception as ex:
            last = ex
            time.sleep(10 * (i + 1))
    raise last


def wikidata_by_repo(repo_keys, state):
    """P1324 source code repository -> QID, for repo urls we actually hold."""
    raw = cached("wikidata_repo", WD_REPO_CACHE, _fetch_p1324, state)
    idx = collections.defaultdict(set)
    for qid, url in raw:
        k = norm(url)
        if k:
            idx[k].add(qid)
    # One repo url claimed by two items is not an identity. Drop it.
    return {k: next(iter(v)) for k, v in idx.items() if len(v) == 1 and k in repo_keys}


def wikidata_by_site(sites, state):
    """P856 official website -> QID, asked only about homepages we hold."""
    return wikidata_by_url("wikidata_site", WD_SITE_CACHE, _AskWikidata("P856"),
                           set(sites), state)


CACHE_NAMES = {"comptoir": "Comptoir du Libre", "wikidata_repo": "Wikidata (repositories)",
               "wikidata_site": "Wikidata (websites)"}
WARN_AFTER_DAYS = 14


def cache_problems(state, now=None):
    """-> [(level, message)] for /sources.html. `warn`, never `critical`: these
    inputs only add identity, and the catalogue is correct without them - but a
    reader should know dedupe is working from an old copy.

    An EMPTY state is a fresh checkout that has not run the crosswalk yet, and
    says nothing, like every other out/ sensor. A state that names some inputs
    but not others is not empty: the missing one never refreshed."""
    if not state:
        return []
    out = []
    for name, label in CACHE_NAMES.items():
        rec = state.get(name) or {}
        age = _age_days(rec.get("fetched_at"), now)
        why = rec.get("error") or "reason not recorded"
        if age is None:
            out.append(("warn", "identity input '%s' has no recorded successful refresh (%s); "
                                "dedupe is using whatever copy is on disk" % (label, why)))
        elif age > WARN_AFTER_DAYS:
            out.append(("warn", "identity input '%s' last refreshed %d days ago (%s); "
                                "dedupe is using that copy" % (label, int(age), why)))
    return out


def resolve_landing(url, timeout=15):
    """Final URL after redirects, or None. A redirect is the site owner saying
    two addresses are one site - the evidence redirect_matches() rests on."""
    import ssl, urllib.request, certifi
    if not url or not url.startswith(("http://", "https://")) or not _iri_safe(url):
        return None
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return _retry_once(lambda: _final_url(req, timeout, ctx))


def _final_url(req, timeout, ctx):
    import urllib.request
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.geturl() if r.status < 400 else None


def _retry_once(call, pause=2):
    """One retry for a NETWORK failure; an HTTP answer (404, 410...) is final.

    Measured 2026-09-23: in one end-to-end run a single failed fetch of a KNIME
    homepage returned None, the loan did not happen, and the entry split for
    that run; the same call succeeded on the next. A lost fetch must not cost a
    merge for a week - but a real 404 is an answer, not a flake."""
    import urllib.error
    for attempt in (1, 2):
        try:
            return call()
        except urllib.error.HTTPError:
            return None
        except Exception:
            if attempt == 2:
                return None
            time.sleep(pause)


def redirect_matches(active, resolve, org_sites=frozenset()):
    """Same-name rows in DIFFERENT catalogues whose homepages END at the same
    page -> [(row without a QID, the other row's QID, donor source)].

    Why: KNIME was two entries. SILL records http://www.knime.org/ (as does
    Wikidata's P856, so SILL's row has Q639194); Munich records
    https://www.knime.com, which is on no Wikidata item, and neither row's repo
    matches, so no URL route reaches the Munich row. knime.org redirects to
    knime.com - the vendor itself says the two are one site.

    This is dedupe identity 3 (exact name AND exact homepage) with the homepage
    taken AFTER redirects, and it only lends an existing QID; it never mints one.
    The final page must match EXACTLY, path included: FreeMind (/ vs /wiki/...)
    and Alfresco (two Hyland pages) stay split, and Consul - HashiCorp's tool vs
    the citizen-participation platform - ends on two different hosts. Pure:
    `resolve` is injected, so test_dedupe_identity.py runs it offline."""
    seen = {}

    def final(u):
        if u not in seen:
            seen[u] = norm(resolve(u))
        return seen[u]
    return _lend(active, "landing", final, skip=lambda e: norm(e["landing"]) in org_sites)


def resolve_github_repo(repo_key, token=None, timeout=15):
    """github.com/<owner>/<name> as GitHub now names it, or None. The API answers
    an old name with the renamed or transferred repo - the owner's own record that
    the two are one repository."""
    import ssl, urllib.request, certifi
    m = re.match(r"^github\.com/([^/]+)/([^/]+)$", repo_key or "")
    if not m:
        return None
    ctx = ssl.create_default_context(cafile=certifi.where())
    hdr = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if token:
        hdr["Authorization"] = "Bearer " + token
    req = urllib.request.Request(f"https://api.github.com/repos/{m[1]}/{m[2]}", headers=hdr)

    def call():
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return "github.com/" + json.load(r)["full_name"].lower()
    return _retry_once(call)


def repo_rename_matches(active, resolve):
    """Same-name rows in DIFFERENT catalogues whose repos are ONE repository after
    GitHub's renames -> [(row without a QID, the other row's QID, donor source)].

    Why: Démarches simplifiées. SILL's row asserts Q93597458 with repo
    github.com/demarche-numerique/demarche.numerique.gouv.fr; the awesome-codegouvfr
    row still records github.com/demarches-simplifiees/demarches-simplifiees.fr,
    the name before the product was renamed Démarche Numérique. The two only merged
    while a six-week-old Comptoir copy still matched the old name; GitHub itself
    redirects the old repo to the new one. The repo twin of redirect_matches(),
    with the same guards (_lend). Pure: `resolve` is injected."""
    seen = {}

    def final(k):
        if k not in seen:
            seen[k] = resolve(k)
        return seen[k]
    return _lend(active, "repo_key", final)


def _lend(active, field, final, skip=lambda e: False):
    """The shared guards of both lending routes. Only for rows with the EXACT same
    name in DIFFERENT catalogues; only an existing QID, and only when exactly one
    is on offer; never to a row that has one; `final` must agree exactly; and
    never when the two values are ALREADY equal - dedupe joins those itself, and
    recording a redirect or rename that did not happen would be a false claim."""
    by_name = collections.defaultdict(list)
    for e in active:
        n = (e.get("name") or "").strip().lower()
        if n:
            by_name[n].append(e)
    out = []
    for rows in by_name.values():
        if len({e.get("source") for e in rows}) < 2:
            continue                      # no cross-catalogue pair: never hit the network
        donors = [e for e in rows if e.get("wikidata") and e.get(field)]
        if len({e["wikidata"] for e in donors}) != 1:
            continue                      # none, or two identities: not ours to pick
        for t in rows:
            if t.get("wikidata") or not t.get(field) or skip(t):
                continue
            for d in donors:
                if d.get("source") == t.get("source") or skip(d):
                    continue
                if norm(t[field]) == norm(d[field]):
                    continue              # already one identity to dedupe; "renamed" would be false
                a, b = final(t[field]), final(d[field])
                if a and a == b:
                    out.append((t, d["wikidata"], d.get("source")))
                    break
    return out


if __name__ == "__main__":
    state = _load_state()
    rows = load_comptoir(state)
    catalog = json.load(open(f"{OUT}/catalog.json"))

    by_repo, by_sill, by_site, by_name = {}, {}, {}, {}
    for r in rows:
        qid = (r.get("wikidata") or "").strip() or None
        if not qid:
            continue
        for k, idx in ((norm(r.get("url_repository")), by_repo),
                       (norm(r.get("url_website")), by_site)):
            if k and k not in idx:
                idx[k] = qid
        if r.get("sill"):
            by_sill.setdefault(str(r["sill"]), qid)
        nm = (r.get("softwarename") or "").strip().lower()
        if nm:
            by_name.setdefault(nm, qid)

    print(f"comptoir: {len(rows)} rows -> {len(by_repo)} repo, {len(by_sill)} sill, "
          f"{len(by_site)} website, {len(by_name)} name keys carrying a QID")

    hits = collections.Counter()
    for e in catalog:
        if e.get("wikidata"):
            continue
        qid = None
        if e.get("repo_key") and e["repo_key"] in by_repo:
            qid, how = by_repo[e["repo_key"]], "repo"
        elif e.get("sill_id") is not None and str(e["sill_id"]) in by_sill:
            qid, how = by_sill[str(e["sill_id"])], "sill_id"
        elif norm(e.get("landing")) and norm(e["landing"]) in by_site:
            qid, how = by_site[norm(e["landing"])], "website"
        else:
            # Name matching is the LAST resort and only for an exact, full,
            # case-insensitive match against a Comptoir entry. Never fuzzy: the
            # Angular / AngularJS pair is exactly what fuzzy matching gets wrong,
            # and one is a substring of the other.
            nm = (e.get("name") or "").strip().lower()
            if nm and nm in by_name:
                qid, how = by_name[nm], "exact_name"
        if qid:
            e["wikidata"] = qid
            e["wikidata_via"] = f"comptoir:{how}"
            hits[how] += 1

    # ---- second source: Wikidata, by URL only. Best effort.
    active = [e for e in catalog if not e.get("excluded")]
    todo = [e for e in active if not e.get("wikidata")]
    try:
        repo_keys = {e["repo_key"] for e in todo if e.get("repo_key")}
        by_wd_repo = wikidata_by_repo(repo_keys, state)

        # A homepage shared by entries with DIFFERENT names is an ORGANISATION
        # site, not a product identity. Measured: umwelt.info is the official
        # website of one Wikidata item and the landing page of four unrelated
        # German repos (data-stories, journal-web-ui, metadaten, usage-stats-api),
        # so without this the four collapse into a single entry. A wrong merge is
        # worse than the missed merge it was meant to fix.
        site_names = collections.defaultdict(set)
        for e in active:
            s = norm(e.get("landing"))
            if s:
                site_names[s].add((e.get("name") or "").strip().lower())
        org_sites = {s for s, n in site_names.items() if len(n) > 1}

        want = {norm(e.get("landing")) for e in todo if norm(e.get("landing"))} - org_sites
        by_wd_site = wikidata_by_site(want, state)

        # A URL match says the page belongs to the item, not that the item is
        # software. Verify before stamping — see software_qids().
        ok, unverified = software_qids(set(by_wd_repo.values()) | set(by_wd_site.values()))
        dropped = len(set(by_wd_repo.values()) | set(by_wd_site.values())) - len(ok) - len(unverified)
        by_wd_repo = {k: v for k, v in by_wd_repo.items() if v in ok}
        by_wd_site = {k: v for k, v in by_wd_site.items() if v in ok}

        for e in todo:
            if e.get("wikidata"):
                continue
            qid = how = None
            if e.get("repo_key") and e["repo_key"] in by_wd_repo:
                qid, how = by_wd_repo[e["repo_key"]], "repo"
            else:
                s = norm(e.get("landing"))
                if s and s not in org_sites and s in by_wd_site:
                    qid, how = by_wd_site[s], "website"
            if qid:
                e["wikidata"] = qid
                e["wikidata_via"] = f"wikidata:{how}"
                hits[f"wd_{how}"] += 1
        print(f"wikidata: {len(by_wd_repo)} repo urls, {len(by_wd_site)} websites resolved to "
              f"exactly one SOFTWARE item ({len(org_sites)} org-shared homepages skipped, "
              f"{dropped} matched items rejected as not software"
              + (f", {len(unverified)} left unverified" if unverified else "") + ")")
    except Exception as ex:
        # A gated step must not fail the run because a third-party endpoint is
        # slow. Comptoir's stamps are already applied and stand on their own.
        print(f"wikidata: SKIPPED ({type(ex).__name__}: {ex})")

    # ---- third: lend a QID across catalogues when homepages redirect to one
    # page. After both sources above, so it lends every QID they stamped. Best
    # effort like Wikidata: it only reaches the network for the few same-name
    # cross-catalogue pairs, and a failed fetch simply matches nothing.
    try:
        active = [e for e in catalog if not e.get("excluded")]
        site_names = collections.defaultdict(set)
        for e in active:
            s = norm(e.get("landing"))
            if s:
                site_names[s].add((e.get("name") or "").strip().lower())
        org_sites = {s for s, n in site_names.items() if len(n) > 1}
        for e, qid, donor in redirect_matches(active, resolve_landing, org_sites):
            e["wikidata"] = qid
            e["wikidata_via"] = f"redirect:{donor}"
            hits["redirect"] += 1
    except Exception as ex:
        print(f"redirect: SKIPPED ({type(ex).__name__}: {ex})")

    # ---- fourth: the same, when GitHub says two repo urls are one repository
    # (a rename or transfer). After the redirect route, so it lends those too.
    try:
        import liveness
        tok = liveness.gh_token()
        active = [e for e in catalog if not e.get("excluded")]
        for e, qid, donor in repo_rename_matches(
                active, lambda k: resolve_github_repo(k, tok)):
            e["wikidata"] = qid
            e["wikidata_via"] = f"repo-rename:{donor}"
            hits["repo_rename"] += 1
    except Exception as ex:
        print(f"repo-rename: SKIPPED ({type(ex).__name__}: {ex})")

    _save_state(state)
    json.dump(catalog, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)
    total = sum(hits.values())
    have = sum(1 for e in catalog if e.get("wikidata"))
    print(f"stamped {total} QIDs: {dict(hits)}")
    print(f"entries with a QID: {have}/{len(catalog)} ({100*have/len(catalog):.1f}%)")

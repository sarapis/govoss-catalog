#!/usr/bin/env python3
"""Build site/sources.html + site/sources.json + site/status.json.

This page ABSORBED the old /status.html (build_status.py is retired). Provenance
and liveness were always the same question - "where did this come from, and is
the machine still running?" - and answering it on two pages meant a reader had
to know both existed.

/status.json is NOT retired. It is a published endpoint, listed in llms.txt and
consumed by agents, so it is still written here. Retiring the page is a design
decision; retiring the endpoint would be a breaking change.

No f-strings for markup: plain strings with __PLACEHOLDER__ tokens, substituted
at the end, so no literal CSS or JS brace needs doubling.
"""
import json, os, importlib.util, collections, time

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_s = importlib.util.spec_from_file_location("sources", f"{OUT}/sources.py")
S = importlib.util.module_from_spec(_s); _s.loader.exec_module(S)
_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)
_cn = importlib.util.spec_from_file_location("ctfg_nav", f"{OUT}/ctfg_nav.py")
ctfg_nav = importlib.util.module_from_spec(_cn); _cn.loader.exec_module(ctfg_nav)
NAV = ctfg_nav.load()

STATUS_LABEL = {
    "ready": "Ready to add", "retired": "Retired upstream", "broken": "Broken",
    "no-code": "No code published", "wrong-shape": "Not a code catalogue",
    "bot-protected": "Bot-protected", "false-lead": "False lead",
    "none-found": "None exists", "discovery-source": "Discovery source",
    "needs-research": "Needs research", "unresolved": "Unresolved",
    "different-shape": "Different shape",
}
SPARK_N = 8


def esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def dur(sec):
    if sec is None:
        return "&mdash;"
    sec = int(sec)
    if sec < 60:
        return "%ds" % sec
    return "%dm %ds" % (sec // 60, sec % 60)


def ago(iso):
    if not iso:
        return "never"
    try:
        t = time.mktime(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
    except Exception:
        return iso
    d = time.mktime(time.gmtime()) - t
    for n, u in ((86400, "d"), (3600, "h"), (60, "m")):
        if d >= n:
            return "%d%s ago" % (int(d // n), u)
    return "just now"


def build():
    cat = json.load(open(f"{OUT}/catalog.json"))
    hist = json.load(open(f"{OUT}/history.json"))
    runs = hist["runs"]
    latest = runs[-1]
    active = [r for r in cat if not r.get("excluded")]

    # count by ORIGINAL source, so a merged entry credits every catalogue that
    # asserted it - the same rule runlog.py records per run
    counts = collections.Counter(
        s for r in active for s in (r.get("sources") or [r.get("source")]) if s)

    # ---- health. Same three states and triggers as the retired status page.
    problems = []
    if latest.get("failures"):
        problems.append(("critical", "%d pipeline step(s) failed on the last run: %s"
                         % (len(latest["failures"]), ", ".join(latest["failures"]))))
    stale_h = None
    try:
        stale_h = (time.mktime(time.gmtime())
                   - time.mktime(time.strptime(latest["run_at"], "%Y-%m-%dT%H:%M:%SZ"))) / 3600
    except Exception:
        pass
    if stale_h is not None and stale_h > 24 * 8:
        problems.append(("critical", "last successful run was %d days ago; the weekly "
                                     "schedule appears to have stopped" % int(stale_h // 24)))
    elif stale_h is not None and stale_h > 24 * 7.5:
        problems.append(("warn", "a scheduled run looks overdue"))
    for k, meta in S.SOURCES.items():
        if counts.get(k, 0) == 0:
            problems.append(("warn", "catalogue '%s' contributed 0 entries" % meta["label"]))
    state = ("critical" if any(p[0] == "critical" for p in problems)
             else "warn" if any(p[0] == "warn" for p in problems) else "ok")

    # ---- sparkline: per-CATALOGUE presence over the last N runs.
    # Derived from each run's recorded `catalogues` map. Runs older than that
    # field simply have no bar - the sparkline fills in over subsequent weeks
    # rather than inventing history it does not have.
    tail = runs[-SPARK_N:]
    timing = {k: (v or {}).get("seconds") for k, v in (latest.get("sources") or {}).items()}

    def spark(key):
        cells = ""
        for r in tail:
            cmap = r.get("catalogues")
            if cmap is None:
                cls, tip = "s-none", "not recorded for this run"
            elif cmap.get(key, 0) > 0:
                cls, tip = "s-ok", "%d entries" % cmap[key]
            elif key in cmap:
                cls, tip = "s-fail", "contributed nothing"
            else:
                cls, tip = "s-none", "not a source yet"
            cells += '<span class="sb %s" title="%s &mdash; %s"></span>' % (
                cls, esc(r["run_at"][:10]), tip)
        return cells

    # ---- catalogue rows
    crows = ""
    for key, meta in sorted(S.SOURCES.items(), key=lambda kv: -counts.get(kv[0], 0)):
        n = counts.get(key, 0)
        secs = timing.get(meta.get("checkpoint"))
        stamps = ""
        if meta.get("route", "").lower().find("publiccode") >= 0 or key in (
                "IT/developers-italia", "DE/openCode"):
            stamps += '<span class="stamp multi">publiccode.yml</span>'
        if n == 0:
            stamps += '<span class="stamp warn">contributed nothing</span>'
        crows += (
            '<div class="crow">'
            '<div class="c-cc">%s <b>%s</b></div>'
            '<div class="c-main"><div class="c-t">'
            '<a href="%s" target="_blank" rel="noopener">%s</a>%s</div>'
            '<div class="c-note">%s</div></div>'
            '<div class="c-n"><b class="num">%s</b><span>entries</span></div>'
            '<div class="c-m"><span class="mono">%s</span><span class="c-sec">%s</span></div>'
            '<div class="c-s">%s</div>'
            '</div>'
        ) % (meta["flag"], esc(meta["country"]), esc(meta["site"]), esc(meta["label"]),
             stamps, esc(meta.get("note") or meta.get("claim") or ""), "{:,}".format(n),
             esc(meta.get("route", "")),
             ("%ss" % int(secs)) if secs is not None else "&mdash;", spark(key))

    # ---- steps of the last run
    steps = latest.get("steps") or []
    longest = max([s.get("duration_s") or 0 for s in steps] or [1]) or 1
    srows = ""
    for i, st in enumerate(steps, 1):
        d = st.get("duration_s")
        pct = int(100 * (d or 0) / longest)
        badge = ('<span class="stamp rec">pass</span>' if st["ok"]
                 else '<span class="stamp warn">fail</span>')
        srows += (
            '<div class="srow"><span class="s-i num">%02d</span>'
            '<span class="s-n">%s</span>'
            '<span class="s-bar"><i style="width:%d%%"></i></span>'
            '<span class="s-d num">%s</span>%s</div>'
        ) % (i, esc(st["step"]), pct, dur(d), badge)

    # ---- weekly diff, newest first
    drows = ""
    for r in reversed(runs[-6:]):
        d = r.get("delta") or {}
        chips = ""
        if d.get("entries_active"):
            chips += '<span class="chip mint">%+d added</span>' % d["entries_active"]
        lv = r.get("liveness") or {}
        if lv.get("newly_dead"):
            chips += '<span class="chip ink">%d repos gone</span>' % len(lv["newly_dead"])
        if lv.get("revived"):
            chips += '<span class="chip">%d revived</span>' % len(lv["revived"])
        per = d.get("per_source") or {}
        if per:
            chips += '<span class="chip">%s</span>' % esc(
                ", ".join("%s %+d" % (k, v) for k, v in list(per.items())[:3]))
        if not chips:
            chips = '<span class="chip">no change</span>'
        drows += (
            '<div class="dcard"><div class="d-h"><b>%s</b><span class="num">%s entries</span></div>'
            '<div class="d-c">%s</div></div>'
        ) % (esc(r["run_at"][:10]), "{:,}".format((r.get("entries") or {}).get("active") or 0), chips)

    # ---- surveyed and rejected
    vrows = ""
    for e in S.SURVEY:
        vrows += (
            '<div class="vcard"><div class="v-h">%s <b>%s</b></div>'
            '<a class="v-n" href="%s" target="_blank" rel="noopener">%s</a>'
            '<span class="v-chip">%s</span>'
            '<p class="v-d">%s</p></div>'
        ) % (e["flag"], esc(e["country"]), esc(e["url"]), esc(e["name"]),
             esc(STATUS_LABEL.get(e["status"], e["status"])), esc(e["detail"]))

    n_countries = len({m["country"] for m in S.SOURCES.values()})
    added = (latest.get("delta") or {}).get("entries_active") or 0

    # ---- machine-readable. Same shape as before so existing consumers keep
    # working; `page` records where the human version now lives.
    json.dump({
        "generated_at": NOW, "state": state,
        "last_run": {k: latest.get(k) for k in
                     ("run_at", "trigger", "duration_s", "ok", "failures")},
        "entries": latest.get("entries"),
        "liveness": latest.get("liveness"),
        "translation": latest.get("translation"),
        "sources": latest.get("sources"),
        "catalogues": latest.get("catalogues"),
        "problems": [{"level": a, "message": b} for a, b in problems],
        "runs_recorded": len(runs), "history_begins": runs[0]["run_at"],
        "page": "/sources.html",
        "schedule": {"cron": "Mondays 07:00 local",
                     "agent": "org.antigravity.govoss-harvest",
                     "redeploy": "automatic - run.sh publishes and commits as its last "
                                 "steps, gated on every earlier step exiting 0"},
    }, open(f"{SITE}/status.json", "w"), indent=1, default=str)

    json.dump({"generated_at": NOW,
               "ingested": [{**m, "key": k, "entries": counts.get(k, 0)}
                            for k, m in S.SOURCES.items()],
               "survey": S.SURVEY},
              open(f"{SITE}/sources.json", "w"), indent=1)

    subs = {
        "__CROWS__": crows, "__SROWS__": srows, "__DROWS__": drows, "__VROWS__": vrows,
        "__N_CAT__": str(len(S.SOURCES)),
        "__N_COUNTRIES__": str(n_countries),
        "__N_ADDED__": "%+d" % added,
        "__N_RUNS__": str(len(runs)),
        "__N_SURVEY__": str(len(S.SURVEY)),
        "__RUN_AT__": esc(latest["run_at"]),
        "__RUN_AGO__": esc(ago(latest["run_at"])),
        "__RUN_DUR__": dur(latest.get("duration_s")),
        "__STATE_CLS__": {"ok": "rec", "warn": "warn", "critical": "warn"}[state],
        "__STATE_TXT__": {"ok": "published", "warn": "published with warnings",
                          "critical": "attention needed"}[state],
        "__PROBLEMS__": ("".join('<li class="p-%s"><b>%s</b> %s</li>' % (a, a, esc(b))
                                 for a, b in problems)
                         or '<li class="p-ok">Nothing outstanding. Every step of the last '
                            'run completed.</li>'),
        "__SPARK_N__": str(len(tail)),
        "__ICON_SEAL__": T.ICONS["seal"],
    }

    page = (theme.head(
        "Sources and harvest status | govoss",
        "The %d government catalogues govoss harvests first-hand, how the last harvest "
        "went, and the %d catalogues that were surveyed and rejected, with reasons."
        % (len(S.SOURCES), len(S.SURVEY)))
        + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + PAGE_CSS + "</style>\n"
        + theme.utility_bar(NAV) + theme.topbar("sources") + BODY + theme.footer(NAV))

    for k, v in subs.items():
        page = page.replace(k, v)
    import re as _re
    left = sorted(set(_re.findall(r"__[A-Z_]{3,}__", page)))
    if left:
        raise SystemExit("build_sources: unsubstituted placeholders %s" % left)

    page = page.encode("ascii", "xmlcharrefreplace").decode()
    open(f"{SITE}/sources.html", "w").write(page)
    print("sources page: %d catalogues, %d surveyed, state=%s (%.0f KB) + sources.json + status.json"
          % (len(S.SOURCES), len(S.SURVEY), state, len(page) / 1024))
    for a, b in problems:
        print("   [%s] %s" % (a, b))


PAGE_CSS = """
.sec{margin-top:44px;}
.sechead{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;
  gap:8px 20px;padding-bottom:10px;}
.sechead .r{font-size:12px;color:var(--ink-400);}
.stamp.ok{background:var(--green);color:var(--white);box-shadow:var(--shadow-green);}

/* catalogue rows */
.crow{display:flex;flex-wrap:wrap;gap:12px 16px;align-items:flex-start;
  padding:16px 20px;border-bottom:1px solid var(--border-soft);}
.crow:last-child{border-bottom:0;}
.clist{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);overflow:hidden;}
.c-cc{flex:0 0 52px;font-size:12px;color:var(--ink-600);}
.c-main{flex:1 1 320px;min-width:0;}
.c-t{display:flex;flex-wrap:wrap;align-items:center;gap:8px;}
.c-t a{font-family:var(--font-display);font-size:16px;font-weight:600;color:var(--ink);
  text-decoration:none;}
.c-t a:hover{color:var(--primary);text-decoration:underline;}
.c-note{font-size:13px;color:var(--ink-600);margin-top:3px;text-wrap:pretty;}
.c-n{flex:0 0 88px;text-align:right;}
.c-n b{display:block;font-family:var(--font-display);font-size:20px;color:var(--ink);}
.c-n span{font-family:var(--font-ui);font-size:10px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-400);}
.c-m{flex:0 0 150px;display:flex;flex-direction:column;gap:2px;font-size:12px;
  color:var(--ink-600);}
.c-m .c-sec{color:var(--ink-400);font-variant-numeric:tabular-nums;}
.c-s{flex:0 0 auto;display:flex;gap:2px;align-items:flex-end;}
.sb{width:7px;height:20px;border-radius:2px;background:var(--border-soft);}
.sb.s-ok{background:var(--green);}
.sb.s-fail{background:var(--ink-900);}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;font-size:12px;
  color:var(--ink-600);align-items:center;}
.legend i{display:inline-block;width:7px;height:14px;border-radius:2px;
  margin-right:5px;vertical-align:-2px;}

/* two columns */
.two{display:flex;flex-wrap:wrap;gap:32px;}
.two > div{min-width:0;}
.col-diff{flex:1 1 420px;} .col-steps{flex:1 1 380px;}
.dcard{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);padding:14px 16px;margin-bottom:10px;}
.d-h{display:flex;justify-content:space-between;align-items:baseline;gap:12px;
  font-size:13px;}
.d-h b{font-family:var(--font-display);font-size:15px;}
.d-h span{color:var(--ink-400);font-size:12px;}
.d-c{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;}
.chip{font-size:11px;padding:3px 8px;border-radius:var(--r-chip);
  background:var(--bg-alt);color:var(--ink-600);}
.chip.mint{background:var(--mint-100);color:var(--green-700);}
.chip.ink{background:var(--ink-900);color:var(--paper-50);}

.srow{display:flex;align-items:center;gap:10px;padding:9px 0;
  border-bottom:1px solid var(--border-soft);font-size:13px;}
.srow:last-child{border-bottom:0;}
.s-i{flex:0 0 22px;color:var(--ink-400);font-size:11px;}
.s-n{flex:1 1 110px;min-width:0;}
.s-bar{flex:0 0 90px;height:6px;background:var(--bg-alt);border-radius:3px;overflow:hidden;}
.s-bar i{display:block;height:100%;background:var(--primary);}
.s-d{flex:0 0 54px;text-align:right;color:var(--ink-600);font-size:12px;}

/* surveyed */
.vgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;}
.vcard{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);padding:16px;display:flex;flex-direction:column;gap:6px;}
.v-h{font-size:12px;color:var(--ink-600);}
.v-n{font-family:var(--font-display);font-size:15px;font-weight:600;color:var(--ink);
  text-decoration:none;}
.v-n:hover{color:var(--primary);text-decoration:underline;}
.v-chip{align-self:flex-start;font-family:var(--font-ui);font-size:10px;font-weight:600;
  letter-spacing:.1em;text-transform:uppercase;border:1px solid var(--border);
  border-radius:var(--r-chip);padding:3px 8px;color:var(--ink-600);}
.v-d{font-size:13px;color:var(--ink-600);line-height:1.5;text-wrap:pretty;}

/* problems */
.probs{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px;}
.probs li{background:var(--surface);border:1px solid var(--border);
  border-left:3px solid var(--border);border-radius:var(--r-chip);padding:10px 14px;
  font-size:13px;color:var(--ink-600);}
.probs li b{font-family:var(--font-ui);font-size:10px;letter-spacing:.1em;
  text-transform:uppercase;margin-right:8px;}
.probs .p-critical{border-left-color:var(--ink-900);}
.probs .p-warn{border-left-color:var(--primary);}
.probs .p-ok{border-left-color:var(--green);}
"""

BODY = """
<div class="hero tex">
  <div class="inner">
    <p class="overline">Sources</p>
    <h2>Where the entries come from, and how the last harvest went</h2>
    <p class="lede">Every entry is harvested first-hand from a government's own catalogue
      &mdash; never syndicated from an aggregator. This page shows all __N_CAT__ of them, the
      __N_SURVEY__ that were surveyed and rejected, and whether the machine is still running.</p>
    <span class="stamp __STATE_CLS__" style="margin-top:4px">__ICON_SEAL__
      Last updated __RUN_AT__ &middot; __STATE_TXT__ in __RUN_DUR__</span>
  </div>
</div>

<div class="wrap">
  <div class="stats">
    <div class="stat"><b>__N_CAT__</b><span>catalogues harvested</span></div>
    <div class="stat"><b>__N_COUNTRIES__</b><span>countries and bodies</span></div>
    <div class="stat"><b>__N_ADDED__</b><span>entries since last run</span></div>
    <div class="stat"><b>__N_RUNS__</b><span>runs recorded</span></div>
    <div class="stat"><b>__N_SURVEY__</b><span>surveyed and rejected</span></div>
  </div>

  <section class="sec">
    <div class="sechead"><h3>Harvested catalogues</h3>
      <span class="r">Counts credit every catalogue that listed an entry, so a tool in
        three catalogues counts three times.</span></div>
    <hr class="dashed">
    <div class="clist" style="margin-top:14px">__CROWS__</div>
    <div class="legend">
      <span><i style="background:var(--green)"></i>harvested</span>
      <span><i style="background:var(--ink-900)"></i>contributed nothing</span>
      <span><i style="background:var(--border-soft)"></i>not a source yet, or not recorded</span>
      <span style="color:var(--ink-400)">last __SPARK_N__ runs, oldest first</span>
    </div>
  </section>

  <section class="sec">
    <div class="sechead"><h3>Open items</h3></div>
    <hr class="dashed">
    <ul class="probs" style="margin-top:14px">__PROBLEMS__</ul>
  </section>

  <section class="sec">
    <div class="two">
      <div class="col-diff">
        <div class="sechead"><h3>What changed</h3></div>
        <hr class="dashed">
        <div style="margin-top:14px">__DROWS__</div>
      </div>
      <div class="col-steps">
        <div class="sechead"><h3>Steps of the last run</h3><span class="r">through the run log</span></div>
        <hr class="dashed">
        <div style="margin-top:8px">__SROWS__</div>
        <p class="note">A run publishes only if every step exits 0, so a failed step means
          the public copy stays on the last good run rather than being overwritten with a
          partial harvest.</p>
        <p class="note">This list stops at the step that wrote it: the run log is recorded
          before this page is built, so the steps that follow &mdash; building this page and
          the API page, deploying, and committing the data &mdash; cannot appear on it. They
          are not hidden. <b>That you are reading this page at all is the evidence the deploy
          step succeeded</b>, since a failed run publishes nothing and you would be looking at
          the previous week's copy.</p>
      </div>
    </div>
  </section>

  <section class="sec">
    <div class="sechead"><h3>Surveyed and not harvested</h3>
      <span class="r">Published with reasons, so nobody spends the same twenty minutes twice.</span></div>
    <hr class="dashed">
    <div class="vgrid" style="margin-top:14px">__VROWS__</div>
  </section>

  <div class="submit" id="submit">
    <p class="overline">Get involved</p>
    <h3>Are we missing a catalog?</h3>
    <p style="color:var(--ink-600);max-width:60ch">If your government publishes an open source
      register, open an issue. It will be assessed against the same first-hand rule as the
      __N_CAT__ already here &mdash; a live endpoint is not enough, the data has to be there.</p>
    <a class="btn btn-primary" href="https://github.com/sarapis/govoss-catalog/issues/new">Submit a catalog</a>
  </div>
</div>
"""

if __name__ == "__main__":
    build()

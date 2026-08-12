#!/usr/bin/env python3
"""Build site/status.html + site/status.json from history.json.

A dashboard, not a document: summary before detail, state encoded in form as well
as number, so what needs attention reads at a glance.

Everything shown is recorded, never inferred. If history.json has one run, the
page says so rather than drawing an empty trend line — a status page that implies
more history than it has is worse than one that admits it is new.
"""
import json, os, re, time, collections, importlib.util

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_spec = importlib.util.spec_from_file_location("taxonomy", f"{OUT}/taxonomy.py")
_tax = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_tax)

SOURCE_LABEL = {"fr": "France (SILL + awesome)", "it": "Italy (Developers Italia)",
                "de": "Germany (openCode)", "be": "Belgium (iMio)",
                "se": "Sweden (Offentligkod)", "fi": "Finland (Avoinkoodi)",
                "eu": "EU institutions (code.europa.eu)", "nl": "Netherlands (OSS register)"}
NOTES = {"nl": "needs NL_API_KEY — every read returns 401 without one"}


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
            return f"{int(d // n)}{u} ago"
    return "just now"


def esc(s):
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build():
    hist = json.load(open(f"{OUT}/history.json"))
    runs = hist["runs"]
    latest = runs[-1]
    lv = latest.get("liveness") or {}
    en = latest.get("entries") or {}

    # ---- health: only three states, and each has a defined trigger
    problems = []
    if latest.get("failures"):
        problems.append(("critical", f"{len(latest['failures'])} pipeline step(s) failed on the last run: "
                                     + ", ".join(latest["failures"])))
    stale_h = None
    try:
        stale_h = (time.mktime(time.gmtime()) -
                   time.mktime(time.strptime(latest["run_at"], "%Y-%m-%dT%H:%M:%SZ"))) / 3600
    except Exception:
        pass
    if stale_h is not None and stale_h > 24 * 8:
        problems.append(("critical", f"last successful run was {int(stale_h//24)} days ago; "
                                     "the weekly schedule appears to have stopped"))
    elif stale_h is not None and stale_h > 24 * 7.5:
        problems.append(("warn", "a scheduled run looks overdue"))
    for k, s in (latest.get("sources") or {}).items():
        if s["records"] == 0:
            problems.append(("warn", f"source '{k}' contributed 0 records"
                                     + (f" — {NOTES[k]}" if k in NOTES else "")))
    if lv.get("newly_dead"):
        problems.append(("info", f"{len(lv['newly_dead'])} repository link(s) newly confirmed dead"))
    state = ("critical" if any(p[0] == "critical" for p in problems)
             else "warn" if any(p[0] == "warn" for p in problems) else "ok")

    status_json = {
        "generated_at": NOW,
        "state": state,
        "last_run": {k: latest.get(k) for k in
                     ("run_at", "trigger", "duration_s", "ok", "failures")},
        "entries": en,
        "liveness": {k: lv.get(k) for k in
                     ("checked", "total", "ok", "dead", "pending_dead", "unknown", "archived")},
        "translation": latest.get("translation"),
        "categorisation": latest.get("categorisation"),
        "sources": latest.get("sources"),
        "problems": [{"level": a, "message": b} for a, b in problems],
        "runs_recorded": len(runs),
        "history_begins": runs[0]["run_at"],
        "schedule": {"cron": "Mondays 07:00 local",
                     "agent": "org.antigravity.govoss-harvest",
                     "log": "~/Library/Logs/govoss-harvest.log",
                     "redeploy": "automatic — run.sh publishes site/ to Vercel as its "
                                 "last step, gated on every earlier step succeeding"},
    }

    # ---------------- changelog rows, newest first
    log_rows = []
    for r in reversed(runs):
        d = r.get("delta") or {}
        bits = []
        if d.get("entries_active"):
            bits.append(f"{d['entries_active']:+d} entries")
        for k, v in (d.get("per_source") or {}).items():
            bits.append(f"{SOURCE_LABEL.get(k, k).split(' (')[0]} {v:+d}")
        if d.get("liveness_dead"):
            bits.append(f"{d['liveness_dead']:+d} dead links")
        for k in (r.get("liveness") or {}).get("newly_dead") or []:
            bits.append(f"dead: {k}")
        for k in (r.get("liveness") or {}).get("revived") or []:
            bits.append(f"revived: {k}")
        if r.get("failures"):
            bits.append("FAILED: " + ", ".join(r["failures"]))
        log_rows.append({
            "run_at": r["run_at"], "trigger": r.get("trigger"),
            "ok": r.get("ok", True), "duration_s": r.get("duration_s"),
            "active": (r.get("entries") or {}).get("active"),
            "changes": bits or ["no change"],
        })
    status_json["changelog"] = log_rows

    os.makedirs(SITE, exist_ok=True)
    json.dump(status_json, open(f"{SITE}/status.json", "w"), indent=1, default=str)

    # ---------------- HTML
    BADGE = {"ok": ("Operational", "ok"), "warn": ("Degraded", "warn"),
             "critical": ("Attention needed", "bad")}
    label, cls = BADGE[state]

    def tile(v, l, extra=""):
        return f'<div class="tile"><b class="{extra}">{esc(v)}</b><span>{esc(l)}</span></div>'

    tiles = "".join([
        tile(en.get("active"), "entries"),
        tile(lv.get("ok"), "repos reachable", "good"),
        tile(lv.get("dead"), "dead links", "bad" if (lv.get("dead") or 0) else ""),
        tile(f"{(latest.get('translation') or {}).get('coverage_pct')}%", "English coverage"),
        tile(en.get("publiccode_tier"), "with publiccode.yml"),
        tile(en.get("filtered_out"), "filtered out"),
    ])

    src_rows = ""
    for k, s in sorted((latest.get("sources") or {}).items(),
                       key=lambda kv: -kv[1]["records"]):
        zero = s["records"] == 0
        src_rows += (
            f'<tr class="{"zero" if zero else ""}">'
            f'<td>{esc(SOURCE_LABEL.get(k, k))}</td>'
            f'<td class="num">{s["records"]}</td>'
            f'<td class="mono dim">{esc(ago(s.get("checkpoint_mtime")))}</td>'
            f'<td class="dim">{esc(NOTES.get(k, "") if zero else "")}</td></tr>')

    prob_html = ""
    if problems:
        items = "".join(f'<li class="p-{a}"><b>{a}</b> {esc(b)}</li>' for a, b in problems)
        prob_html = f'<section><h2>Open items</h2><ul class="probs">{items}</ul></section>'
    else:
        prob_html = '<section><h2>Open items</h2><p class="dim">None. Last run completed every step.</p></section>'

    log_html = ""
    for r in log_rows:
        chg = "".join(f'<li>{esc(c)}</li>' for c in r["changes"])
        dur = f'{r["duration_s"]//60}m {r["duration_s"]%60}s' if r.get("duration_s") else "&mdash;"
        log_html += (
            f'<div class="run {"failed" if not r["ok"] else ""}">'
            f'<div class="when"><b class="mono">{esc(r["run_at"])}</b>'
            f'<span class="mono dim">{esc(r.get("trigger"))} &middot; {dur} &middot; '
            f'{esc(r.get("active"))} entries</span></div>'
            f'<ul class="chg">{chg}</ul></div>')

    single = ("<p class=\"dim note\">This is the first recorded run &mdash; history starts here, "
              "so there is nothing to compare against yet. Deltas appear from the next run on.</p>"
              if len(runs) == 1 else "")

    page = f"""<title>govoss-catalog &mdash; status</title>
<link rel="alternate" type="application/json" href="/status.json" title="This page as JSON">
<style>
:root {{
  --paper:#F7F8F7; --raised:#EDEFEE; --sunk:#E4E7E5; --ink:#171A19; --slate:#626B67;
  --hairline:#DBDFDC; --accent:#0F6B5C; --accent-dim:#E0EEEA;
  --good:#0F6B5C; --warn:#8A5A00; --bad:#A32A22;
  --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}}
@media (prefers-color-scheme:dark) {{ :root {{
  --paper:#0E110F; --raised:#171B18; --sunk:#1F2521; --ink:#E3E8E4; --slate:#939C97;
  --hairline:#262C28; --accent:#56C0AB; --accent-dim:#152420;
  --good:#56C0AB; --warn:#D9A43F; --bad:#EF7A70; }} }}
:root[data-theme="dark"] {{
  --paper:#0E110F; --raised:#171B18; --sunk:#1F2521; --ink:#E3E8E4; --slate:#939C97;
  --hairline:#262C28; --accent:#56C0AB; --accent-dim:#152420;
  --good:#56C0AB; --warn:#D9A43F; --bad:#EF7A70; }}
:root[data-theme="light"] {{
  --paper:#F7F8F7; --raised:#EDEFEE; --sunk:#E4E7E5; --ink:#171A19; --slate:#626B67;
  --hairline:#DBDFDC; --accent:#0F6B5C; --accent-dim:#E0EEEA;
  --good:#0F6B5C; --warn:#8A5A00; --bad:#A32A22; }}

body {{ background:var(--paper); color:var(--ink); font-family:var(--sans);
  font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:900px; margin:0 auto; padding:2rem 1.1rem 5rem;
  display:flex; flex-direction:column; gap:2rem; }}
.mono {{ font-family:var(--mono); }} .dim {{ color:var(--slate); }}
.num {{ font-family:var(--mono); font-variant-numeric:tabular-nums; text-align:right; }}
a {{ color:var(--accent); }}

header {{ display:flex; flex-direction:column; gap:.5rem; }}
h1 {{ font-size:clamp(1.4rem,3.5vw,1.85rem); font-weight:640; letter-spacing:-.02em; margin:0; }}
.badge {{ display:inline-flex; align-items:center; gap:.5rem; align-self:flex-start;
  font-family:var(--mono); font-size:.75rem; letter-spacing:.08em; text-transform:uppercase;
  padding:.32rem .7rem; border-radius:20px; background:var(--accent-dim); color:var(--accent); }}
.badge.warn {{ background:#8A5A0018; color:var(--warn); }}
.badge.bad  {{ background:#A32A2218; color:var(--bad); }}
.badge .dot {{ width:.5rem; height:.5rem; border-radius:50%; background:currentColor; }}

.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(8.5rem,1fr));
  gap:.1rem 1.6rem; border-top:1px solid var(--hairline);
  border-bottom:1px solid var(--hairline); padding:1rem 0; }}
.tile {{ display:flex; flex-direction:column; gap:.15rem; padding:.3rem 0; }}
.tile b {{ font-family:var(--mono); font-size:1.4rem; font-weight:600;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em; }}
.tile b.good {{ color:var(--good); }} .tile b.bad {{ color:var(--bad); }}
.tile span {{ font-family:var(--mono); font-size:.62rem; letter-spacing:.11em;
  text-transform:uppercase; color:var(--slate); }}

section {{ display:flex; flex-direction:column; gap:.8rem; }}
h2 {{ font-size:1.08rem; font-weight:640; margin:0; padding-bottom:.4rem;
  border-bottom:1px solid var(--hairline); }}
p {{ margin:0; max-width:70ch; }}
.note {{ font-size:.9rem; }}

.probs {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:.5rem; }}
.probs li {{ font-size:.92rem; padding-left:.9rem; border-left:2px solid var(--hairline); }}
.probs b {{ font-family:var(--mono); font-size:.65rem; letter-spacing:.09em;
  text-transform:uppercase; margin-right:.5rem; }}
.p-critical {{ border-left-color:var(--bad); }} .p-critical b {{ color:var(--bad); }}
.p-warn {{ border-left-color:var(--warn); }} .p-warn b {{ color:var(--warn); }}
.p-info {{ border-left-color:var(--accent); }} .p-info b {{ color:var(--accent); }}

.scroller {{ overflow-x:auto; border:1px solid var(--hairline); border-radius:4px; }}
table {{ border-collapse:collapse; width:100%; font-size:.88rem; }}
th,td {{ text-align:left; padding:.5rem .8rem; border-bottom:1px solid var(--hairline);
  white-space:nowrap; }}
thead th {{ font-family:var(--mono); font-size:.63rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--slate); background:var(--raised); font-weight:500; }}
tbody tr:last-child td {{ border-bottom:0; }}
tr.zero td {{ color:var(--warn); }}

.run {{ border-left:2px solid var(--hairline); padding:.15rem 0 .15rem 1rem;
  display:flex; flex-direction:column; gap:.3rem; }}
.run.failed {{ border-left-color:var(--bad); }}
.when {{ display:flex; flex-wrap:wrap; gap:.2rem .8rem; align-items:baseline; }}
.when b {{ font-size:.82rem; }} .when span {{ font-size:.7rem; }}
.chg {{ list-style:none; margin:0; padding:0; display:flex; flex-wrap:wrap; gap:.3rem .6rem; }}
.chg li {{ font-family:var(--mono); font-size:.72rem; color:var(--slate);
  background:var(--sunk); border-radius:3px; padding:.1rem .45rem; }}
.runs {{ display:flex; flex-direction:column; gap:1rem; }}

footer {{ border-top:1px solid var(--hairline); padding-top:1rem; color:var(--slate);
  font-size:.82rem; display:flex; flex-direction:column; gap:.4rem; }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
</style>

<div class="wrap">
  <header>
    <div class="badge {cls}"><span class="dot"></span>{label}</div>
    <h1>govoss-catalog &mdash; status</h1>
    <p class="dim">Data last rebuilt <b class="mono">{esc(latest['run_at'])}</b>
       ({esc(ago(latest['run_at']))}), trigger <span class="mono">{esc(latest.get('trigger'))}</span>.
       Harvest runs Mondays 07:00 local and publishes itself, so this page is redeployed by
       the run it describes &mdash; unless a step failed, in which case nothing is published
       and the copy you are reading is the last good run.</p>
    <p class="dim note" id="stale" hidden></p>
    <p class="dim note">Machine-readable: <a href="/status.json">/status.json</a> &middot;
       catalogue data <a href="/entries.json">/entries.json</a> &middot;
       <a href="/">back to the catalogue</a></p>
  </header>

  <div class="tiles">{tiles}</div>

  {prob_html}

  <section>
    <h2>Sources</h2>
    <p class="dim note">Counts come from each source's own checkpoint, so a source that failed
       this run shows its last good figure rather than reading as zero.</p>
    <div class="scroller"><table>
      <thead><tr><th>Source</th><th class="num">Records</th><th>Checkpoint</th><th>Note</th></tr></thead>
      <tbody>{src_rows}</tbody>
    </table></div>
  </section>

  <section>
    <h2>Pipeline &mdash; last run</h2>
    <div class="scroller"><table>
      <thead><tr><th>Step</th><th>Result</th></tr></thead>
      <tbody>{"".join(
        f'<tr><td class="mono">{esc(s["step"])}</td>'
        f'<td style="color:var(--{"good" if s["ok"] else "bad"})">'
        f'{"ok" if s["ok"] else "FAILED (exit " + esc(s["exit"]) + ")"}</td></tr>'
        for s in latest.get("steps") or [])}</tbody>
    </table></div>
  </section>

  <section>
    <h2>Change log</h2>
    {single}
    <div class="runs">{log_html}</div>
  </section>

  <footer>
    <span>Liveness checked {esc(ago(lv.get('checked')))} &mdash;
      {esc(lv.get('ok'))} reachable, {esc(lv.get('dead'))} dead (confirmed over 2+ runs),
      {esc(lv.get('pending_dead'))} pending, {esc(lv.get('unknown'))} unknown,
      {esc(lv.get('archived'))} archived.</span>
    <span>Categorisation: {esc((latest.get('categorisation') or {{}}).get('classified'))} classified,
      {esc((latest.get('categorisation') or {{}}).get('inferred'))} inferred from text,
      {esc((latest.get('categorisation') or {{}}).get('unclassified'))} left unclassified.</span>
    <span>{esc(len(runs))} run(s) recorded, history begins {esc(runs[0]['run_at'])}.
      Page generated {esc(NOW)}.</span>
  </footer>
</div>
<script>
/* The badge above is baked at build time. A page that stopped being republished
   would therefore keep reading "Operational" no matter how old it got - which is
   the same failure the deploy step exists to prevent, one layer up: a green
   signal that is green because nothing updated it. So re-judge freshness against
   the READER's clock, using the same 8-day trigger build_status.py uses.
   Pure ASCII on purpose: HTML entities are not decoded inside a script tag. */
(function () {{
  var runAt = "{esc(latest['run_at'])}";
  var d = (Date.now() - Date.parse(runAt)) / 864e5;
  if (!(d > 8)) return;
  var badge = document.querySelector('.badge');
  if (badge) {{ badge.className = 'badge bad';
                badge.innerHTML = '<span class="dot"></span>Stale'; }}
  var el = document.getElementById('stale');
  if (el) {{
    el.hidden = false;
    el.innerHTML = 'This page was published ' + Math.floor(d) + ' days ago and the '
      + 'schedule is weekly, so the run that should have replaced it did not publish. '
      + 'Every figure below describes that older run. Check '
      + '<span class="mono">~/Library/Logs/govoss-harvest.log</span>.';
  }}
}})();
</script>
"""
    page = page.encode("ascii", "xmlcharrefreplace").decode()
    open(f"{SITE}/status.html", "w").write(page)
    print(f"status page: state={state} runs={len(runs)} "
          f"({len(page)/1024:.0f} KB) + status.json")
    for a, b in problems:
        print(f"   [{a}] {b}")


if __name__ == "__main__":
    build()

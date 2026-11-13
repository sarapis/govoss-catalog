"""Build site/resources/nyc-ospo.html (served at /resources/nyc-ospo) + its JSON.

How to compile an OSPO executive summary, shown through a worked example: the
research behind a proposed open source program office for New York City, by
Olivia Croteau (Sarapis). Three tabs, as in the research artifact it is published
from: Executive Summary, Concepts and Sources. Linked from the top of /resources.

The data is NOT harvested: resources/nyc-ospo/*.json is a committed, REDACTED
copy of the artifact's export, written by the handoff's redact.py (kept with the
private export, never in this repo). Re-export, redact and replace the folder to
update. The research text stays English on every language copy; only the chrome
is translated.

Everything is rendered here, like /resources: the page works without script
(every tab shown, entries as native <details>), and an agent reading raw HTML gets
all of it. Markdown is rendered by md()/inline() below, a port of the artifact's
own renderer (HTML escaped first). Author-date citations ("Haddad 2022") become
links to their Sources entry at build time, styled by that entry's status.

No f-strings for markup: plain strings with __PLACEHOLDER__ tokens.
"""
import collections
import importlib.util
import json
import os
import re
import time

import build_resources as BR
import i18n

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
DATA = f"{OUT}/resources/nyc-ospo"
ROUTE = "/resources/nyc-ospo"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)

CASE_ORDER = ("CMS", "Munich", "Paris", "European Commission", "United Nations", "U.S. Federal", "NYC",
              "General")
STATUS = (("final", "Final notes"), ("draft", "Draft Notes"), ("todo", "TODO"))


# ---------------------------------------------------------------- markdown
# the two inline tags' labels, set per language by build() (chrome, so translated)
LBL = {"gap": "Gap filled", "need": "Input needed"}


def esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def inline(raw):
    """The artifact's inline(): escape, then links, bold, italic and the three tags."""
    t, keep = esc(raw), []

    def hold(h):
        keep.append(h)
        return "\x00%d\x00" % (len(keep) - 1)

    def link(url, text=None):
        return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (url, text or url)

    t = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", lambda m: hold(link(m.group(2), m.group(1))), t)
    t = re.sub(r"&lt;(https?://[^\s]+?)&gt;", lambda m: hold(link(m.group(1))), t)

    def bare(m):
        url, trail = m.group(0), ""
        while True:
            mm = re.search(r"(&(?:gt|quot|#39);|[.,;:!?)])$", url)
            if not mm:
                break
            trail = mm.group(1) + trail
            url = url[:-len(mm.group(1))]
        return hold(link(url)) + trail
    t = re.sub(r"https?://[^\s\x00]+", bare, t)
    t = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)", r"\1<em>\2</em>", t)
    t = re.sub(r"<em>Gap filled:?</em>:?", '<span class="xs-tag xs-gap">%s</span>' % esc(LBL["gap"]), t)
    t = re.sub(r"\bTODO:", '<span class="xs-tag xs-todo">TODO</span>', t)
    t = re.sub(r"\[Input needed(:[^\]]*)?\]",
               lambda m: '<span class="xs-need">%s%s</span>' % (esc(LBL["need"]), m.group(1) or ""), t)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], t)


def render_list(items):
    html, stack = [], []
    for it in items:
        while stack and stack[-1][0] > it["level"]:
            html.append("</li></%s>" % stack.pop()[1])
        if not stack or stack[-1][0] < it["level"]:
            tag = "ol" if it["ordered"] else "ul"
            stack.append((it["level"], tag))
            html.append("<%s><li>" % tag)
        else:
            html.append("</li><li>")
        html.append(inline(it["text"]))
    while stack:
        html.append("</li></%s>" % stack.pop()[1])
    return "".join(html)


def md(src):
    """The artifact's md(): paragraphs, nested lists, headings, note boxes, tables."""
    lines = str(src or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out, para, items, tbl, quote = [], [], [], [], []

    def flush_para():
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
            para.clear()

    def flush_list():
        if items:
            out.append(render_list(items))
            items.clear()

    def cells(l):
        return [c.strip() for c in re.sub(r"\|\s*$", "", re.sub(r"^\s*\|", "", l)).split("|")]

    def flush_table():
        if not tbl:
            return
        rows, head = [cells(l) for l in tbl], None
        if len(rows) > 1 and all(re.match(r"^:?-{2,}:?$", c) for c in rows[1]):
            head, rows = rows[0], rows[2:]
        h = '<div class="xs-tbl"><table>'
        if head:
            h += "<thead><tr>%s</tr></thead>" % "".join("<th>%s</th>" % inline(c) for c in head)
        h += "<tbody>%s</tbody></table></div>" % "".join(
            "<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r) for r in rows)
        out.append(h)
        tbl.clear()

    def flush_quote():
        if quote:
            out.append('<div class="xs-note">%s</div>' % inline(" ".join(quote)))
            quote.clear()

    for line in lines:
        if re.match(r"^\s*\|", line):
            flush_para(); flush_list(); flush_quote(); tbl.append(line)
            continue
        flush_table()
        bq = re.match(r"^\s*>\s?(.*)$", line)
        if bq:
            flush_para(); flush_list(); quote.append(bq.group(1))
            continue
        flush_quote()
        if not line.strip():
            flush_para(); flush_list()
            continue
        li = re.match(r"^(\s*)(?:[-+]|\*(?=\s)|(\d+)[.)])\s+(.*)$", line)
        if li:
            flush_para()
            items.append({"level": len(li.group(1).replace("\t", "  ")) // 2,
                          "ordered": bool(li.group(2)), "text": li.group(3)})
            continue
        h = re.match(r"^#{1,6}\s+(.*)$", line) or re.match(r"^\s*\*([^*]+)\*\s*$", line)
        if h:
            flush_para(); flush_list(); out.append("<h4>%s</h4>" % inline(h.group(1)))
            continue
        if items and re.match(r"^\s+", line):
            items[-1]["text"] += " " + line.strip()
            continue
        flush_list(); para.append(line.strip())
    flush_para(); flush_list(); flush_table(); flush_quote()
    return "".join(out)


def plain_citation(s):
    return re.sub(r"[*<>]", "", re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 \2", str(s or ""))).strip()


def natural(s):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", s.lower())]


class Cites:
    """The artifact's citeRegex() + linkCites(), at build time: every entry label,
    longest first, linked to #<id> in text that is not already inside a link."""
    def __init__(self, entries, titles):
        labels = sorted(((esc(e["label"]), e) for e in entries if e.get("label")), key=lambda x: -len(x[0]))
        self.by = dict(labels)
        self.re = re.compile("(%s)(?!\\w)" % "|".join(re.escape(l) for l, _ in labels))
        self.titles = titles

    def link(self, html):
        """returns (html, [status of each citation linked])"""
        parts, depth, seen = re.split(r"(<[^>]+>)", html), 0, []
        for i, p in enumerate(parts):
            if p.startswith("<"):
                if re.match(r"<a[\s>]", p):
                    depth += 1
                elif p.startswith("</a"):
                    depth -= 1
                continue
            if depth or not p:
                continue

            def rep(m):
                e = self.by[m.group(1)]
                seen.append(e["status"])
                return ('<a class="xs-cite xs-c-%s" href="#%s" title="%s">%s</a>'
                        % (e["status"], e["id"], self.titles[e["status"]], m.group(1)))
            parts[i] = self.re.sub(rep, p)
        return "".join(parts), seen


# ---------------------------------------------------------------- data
def load():
    d = {k: json.load(open(f"{DATA}/{k}.json", encoding="utf-8"))
         for k in ("executive-summary", "concepts", "bibliography", "meta")}
    entries = d["bibliography"]["entries"]
    if len(entries) != d["bibliography"].get("total", len(entries)):
        raise SystemExit("build_nyc_ospo: bibliography.json says total=%s but carries %d"
                         % (d["bibliography"].get("total"), len(entries)))
    # the public copy is the REDACTED one: the private export's flag never appears in it
    if any("contains_private_interview_notes" in e for e in entries):
        raise SystemExit("build_nyc_ospo: %s holds the PRIVATE export - run the handoff's redact.py" % DATA)
    ids = [e["id"] for e in entries]
    bad = [e["id"] for e in entries
           if e["status"] not in dict(STATUS) or not set(e.get("exec_sections") or []) <= dict(BR.SECTIONS).keys()
           or e.get("role") not in (None,) + tuple(dict(BR.ROLES))]
    reserved = {"exec", "concepts", "sources", "main"} | {s["id"] for s in d["executive-summary"]["sections"]}
    clash = sorted((set(ids) & reserved) | {i for i in ids if ids.count(i) > 1})
    if bad or clash:
        raise SystemExit("build_nyc_ospo: bad status/sections/role %s, or id clashes %s" % (bad, clash))
    return d


# ---------------------------------------------------------------- page
def build(lang, d):
    _ = lambda msg, **kw: i18n.t(lang, msg, **kw)
    N = lambda n: i18n.num(lang, n)
    LBL.update(gap=_("Gap filled"), need=_("Input needed"))
    sec_label = {k: _(v) for k, v in BR.SECTIONS}
    role_label = {k: _(v) for k, v in BR.ROLES}
    st_label = {k: _(v) for k, v in STATUS}
    entries = sorted(d["bibliography"]["entries"], key=lambda e: natural(e["label"]))
    cites = Cites(entries, {"final": _("Final notes"), "draft": _("Draft Notes: not yet verified"),
                            "todo": _("On the TODO list")})
    pages = d["meta"]["pages"]
    add_ids = {r["id"] for r in json.load(open(BR.ADD, encoding="utf-8"))["resources"]}

    # ---- Executive Summary: the paper, and each section's notes
    xs = d["executive-summary"]
    paper, notes = [], []
    for s in xs["sections"]:
        body, _seen = cites.link(md(s["body_md"]))
        nb = []
        for n in s.get("notes") or []:
            # authoring hints ("> Target: about 150 words.") are dropped, word counts never shown
            kept = "\n".join(l for l in (n.get("body_md") or "").split("\n") if not l.lstrip().startswith(">"))
            h, _seen = cites.link(md(kept))
            if h.strip():
                nb.append('<div class="xs-nblk"><h4>%s</h4>%s</div>' % (esc(n.get("title") or ""), h))
        has = bool(nb)
        paper.append('<section class="xs-sec%s" id="%s"%s><h2>%s</h2>%s</section>'
                     % (" xs-hasn" if has else "", esc(s["id"]),
                        ' tabindex="0" aria-controls="xs-panel"' if has else "", esc(s["title"]), body))
        if has:
            paper.append('<div class="xs-snotes" id="n-%s" data-title="%s" hidden>%s</div>'
                         % (esc(s["id"]), esc(s["title"]), "".join(nb)))

    # ---- Concepts: chips, legend, cards with their Draft Notes citation count
    cs = sorted(d["concepts"]["sections"], key=lambda c: c.get("order", 1e9))
    chips, cards = [], []
    for c in cs:
        body, seen = cites.link(md(c["body_md"]))
        nd = seen.count("draft")
        chips.append('<a class="xs-toc" href="#c-%s">%s</a>' % (esc(c["id"]), esc(c["title"])))
        cards.append('<article class="xs-card" id="c-%s"><header><h2>%s</h2>%s</header>%s</article>'
                     % (esc(c["id"]), esc(c["title"]),
                        ('<span class="xs-pill" title="%s">%s</span>'
                         % (esc(_("Citations to Draft Notes, not yet verified")),
                            esc(_("{n} draft citations", n=N(nd)) if nd > 1 else _("1 draft citation"))))
                        if nd else "", body))

    # ---- Sources: stats, toolbar, chip rows, entries
    cnt = collections.Counter(e["status"] for e in entries)
    n_todo = sum(1 for e in entries if e["status"] == "todo" or e.get("has_todo"))
    last = max(e.get("updated_at") or "" for e in entries)[:10]
    stats = esc(_("{n} sources · {f} final · {d} draft · {t} with TODOs · last updated {u}",
                  n=N(len(entries)), f=N(cnt["final"]), d=N(cnt["draft"]), t=N(n_todo), u=last))
    by_case = collections.Counter(c for e in entries for c in e.get("cases") or [])
    by_role = collections.Counter(e.get("role") for e in entries if e.get("role"))
    by_sec = collections.Counter(s for e in entries for s in e.get("exec_sections") or [])

    def chiprow(g, title, all_label, opts):
        return ('<div class="xs-row" role="group" aria-label="%s"><span class="xs-rl">%s</span>'
                '<button type="button" class="xs-chip" data-g="%s" data-v="" aria-pressed="true">%s</button>%s</div>'
                % (esc(title), esc(title), g, esc(all_label), "".join(
                    '<button type="button" class="xs-chip" data-g="%s" data-v="%s" aria-pressed="false">%s'
                    ' <span class="xs-n" data-n>%s</span></button>' % (g, esc(v), esc(lbl), N(n))
                    for v, lbl, n in opts if n)))
    case_names = list(CASE_ORDER) + sorted(set(by_case) - set(CASE_ORDER))
    rows = (chiprow("case", _("Case"), _("All cases"), [(c, c, by_case[c]) for c in case_names])
            + chiprow("role", _("For other cities"), _("All"),
                      [(k, role_label[k], by_role[k]) for k, _v in BR.ROLES])
            + chiprow("sec", _("Supports"), _("Any section"),
                      [(k, sec_label[k], by_sec[k]) for k, _v in BR.SECTIONS]))
    ents = []
    for e in entries:
        st, todo = e["status"], e["status"] == "todo" or bool(e.get("has_todo"))
        role = e.get("role")
        rl = (_("Local: {j}", j=e["jurisdiction"]) if role == "local" and e.get("jurisdiction")
              else role_label.get(role, ""))
        meta = ['<dt>%s</dt><dd>%s</dd>' % (esc(_("Case")), "".join(
                    '<span class="xs-ch">%s</span>' % esc(c) for c in e.get("cases") or []))]
        if rl:
            meta.append('<dt>%s</dt><dd><span class="xs-ch xs-chr">%s</span></dd>' % (esc(_("For other cities")), esc(rl)))
        if e.get("exec_sections"):
            meta.append('<dt>%s</dt><dd>%s</dd>' % (esc(_("Supports")), " &middot; ".join(
                esc(sec_label[k]) for k, _v in BR.SECTIONS if k in e["exec_sections"])))
        also = sorted(set(e.get("already_in_govoss") or []) | ({e["id"]} & add_ids))
        ents.append(
            '<details class="xs-ent" id="%s" data-st="%s" data-todo="%d" data-cases="%s" data-role="%s" data-secs="%s">'
            '<summary><span class="xs-chev" aria-hidden="true"></span><span class="xs-eh"><b>%s</b><span>%s</span></span>'
            '<span class="xs-badges">%s<span class="xs-b">%s</span><span class="xs-b xs-s-%s">%s</span></span></summary>'
            '<div class="xs-eb"><dl class="xs-meta">%s</dl>'
            '<div class="xs-blk"><div class="xs-bh"><h4 class="xs-bt">%s</h4><button type="button" class="xs-copy" data-copy="%s">%s</button></div>'
            '<div class="xs-cit">%s</div></div>'
            '<div class="xs-blk"><h4 class="xs-bt">%s</h4>%s</div><div class="xs-blk"><h4 class="xs-bt">%s</h4>%s</div>%s</div></details>'
            % (esc(e["id"]), st, todo, esc("|".join(e.get("cases") or [])), role or "",
               " ".join(e.get("exec_sections") or []), esc(e["label"]), esc(e.get("title") or ""),
               '<span class="xs-b xs-s-todo">TODO</span>' if todo and st != "todo" else "",
               esc(e.get("type") or ""), st, esc(st_label[st]), "".join(meta),
               esc(_("Citation")), esc(plain_citation(e.get("citation_md"))), esc(_("Copy")),
               inline(e.get("citation_md") or ""),
               esc(_("Summary and Credibility")), md(e.get("summary_and_credibility_md")),
               esc(_("Relevant Content")), md(e.get("relevant_content_md")),
               ('<p class="xs-also">%s %s</p>' % (esc(_("Also on govoss Resources:")), ", ".join(
                   '<a href="/resources#%s">%s</a>' % (esc(i), esc(i)) for i in also))) if also else ""))

    L = {"showing": _("Showing {n} of {t} sources"), "copy": _("Copy"), "copied": _("Copied"),
         "thou": "." if lang == "ca" else ","}
    subs = {
        "__XTITLE__": esc(xs["title"]), "__XSUB__": esc(xs.get("subtitle") or ""),
        "__PAPER__": "".join(paper), "__CHIPS__": "".join(chips), "__CARDS__": "".join(cards),
        "__STATS__": stats, "__INTRO__": md(d["meta"].get("intro_md")), "__ROWS__": rows,
        "__ENTRIES__": "".join(ents), "__NENT__": N(len(entries)),
        "__LX__": esc(pages["exec"]["lede"]), "__LC__": esc(pages["concepts"]["lede"]),
        "__LS__": esc(pages["sources"]["lede"]), "__TS__": esc(pages["sources"]["title"]),
        "__CFG__": theme.script_json({"L": L}, sort_keys=True),
        "__LANG__": lang,
    }
    page = (theme.head(
        _("OSPO executive summary | govoss"),
        _("How to compile an executive summary for a city open source program office, shown through "
          "a worked example for New York City: the summary, the working notes and the annotated sources."),
        lang=lang, route=ROUTE)
        + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + PAGE_CSS + "</style>\n"
        + theme.utility_bar(lang=lang) + theme.topbar("resources", lang, ROUTE)
        + BODY + theme.footer(lang=lang) + SCRIPT)
    page = i18n.markers(page, lang)
    page = theme.fill(page, subs, "build_nyc_ospo")
    page = i18n.links(page, lang)
    theme.assert_variant_live(page)
    page = page.encode("ascii", "xmlcharrefreplace").decode()
    out = f"{SITE}{ROUTE}.html" if lang == "en" else f"{SITE}/{lang}{ROUTE}.html"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="ascii").write(page)
    print("nyc ospo page [%s]: %d summary sections, %d concepts, %d sources (%.0f KB)"
          % (lang, len(xs["sections"]), len(cs), len(entries), len(page) / 1024))


PAGE_CSS = """
.xs-tabs{display:flex;gap:4px;margin-top:28px;border-bottom:1px solid var(--border);}
.xs-tabs button{font:inherit;font-family:var(--font-ui);font-size:14px;font-weight:600;padding:10px 14px;border:0;
  background:none;color:var(--ink-600);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;}
.xs-tabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--primary);}
.xs-tabs button:focus-visible{outline:2px solid var(--primary);outline-offset:-2px;}
.xs-panel-tab{padding-top:18px;}
.xs-lede{font-size:14px;color:var(--ink-600);margin:0 0 14px;max-width:860px;}
.xs-tools{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px;}
.xs-btn{font:inherit;font-family:var(--font-ui);font-size:13px;font-weight:600;padding:8px 14px;border-radius:var(--r-pill);
  border:1px solid var(--border);background:var(--surface);color:var(--ink);cursor:pointer;}
.xs-btn:hover{background:var(--bg-alt);}
/* the summary: a paper, and a sticky notes panel beside it */
.xs-xwrap{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:24px;align-items:start;}
.xs-paper{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);padding:36px 44px;
  max-width:800px;}
/* long reference URLs wrap instead of widening the page on a phone */
.xs-paper,.xs-card,.xs-blk,.xs-aside,.xs-snotes{overflow-wrap:anywhere;}
.xs-paper > header h2{font-size:30px;line-height:1.15;}
.xs-paper > header p{font-family:var(--font-ui);font-size:12px;font-weight:600;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-faint);margin-top:6px;}
.xs-sec{margin-top:22px;padding:6px 14px;margin-left:-14px;margin-right:-14px;border-left:3px solid transparent;
  border-radius:0 var(--r-chip) var(--r-chip) 0;}
.xs-sec.xs-hasn{cursor:pointer;}
.xs-sec.xs-hasn:hover{background:var(--bg);}
.xs-sec.xs-on,.xs-sec.xs-on:hover{background:var(--primary-tint);border-left-color:var(--primary);}
.xs-sec:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
.xs-sec h2{font-size:20px;margin:0 0 6px;}
.xs-sec p,.xs-sec li,.xs-card p,.xs-card li,.xs-blk p,.xs-blk li,.xs-snotes p,.xs-snotes li,.xs-aside p,.xs-aside li{
  font-size:14.5px;line-height:1.65;}
.xs-sec p + p,.xs-card p + p,.xs-blk p + p{margin-top:10px;}
.xs-sec ul,.xs-sec ol,.xs-card ul,.xs-card ol,.xs-blk ul,.xs-blk ol,.xs-snotes ul,.xs-snotes ol,.xs-aside ul,.xs-aside ol{
  margin:6px 0;padding-left:22px;}
.xs-sec h4,.xs-card h4,.xs-blk h4:not(.xs-bt),.xs-snotes h4,.xs-aside h4{font-family:var(--font-display);font-size:14px;margin:12px 0 4px;}
.xs-aside{position:sticky;top:16px;max-height:calc(100vh - 32px);overflow:auto;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--r-card);padding:16px 18px;}
.xs-aside header{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}
.xs-aside header h3{font-size:17px;}
.xs-x{font:inherit;font-size:18px;line-height:1;border:1px solid var(--border);border-radius:var(--r-chip);background:none;
  color:var(--ink-600);cursor:pointer;padding:4px 9px;}
.xs-hint{font-size:13px;color:var(--ink-faint);}
.xs-nblk{margin-top:10px;padding:10px 12px;border:1px dashed var(--border);border-radius:var(--r-chip);}
.xs-nblk > h4:first-child{margin-top:0;font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ink-faint);}
.xs-snotes{margin:6px 0 0;}
/* citations, by their entry's status: plain for final, amber for draft, red for TODO */
a.xs-cite{color:inherit;text-decoration:underline;text-decoration-color:var(--primary);text-underline-offset:2px;}
a.xs-cite.xs-c-draft{background:var(--wg-warning-surface);color:var(--wg-warning-text);text-decoration-style:dotted;
  text-decoration-color:var(--wg-warning-text);border-radius:2px;}
a.xs-cite.xs-c-todo{background:var(--wg-danger-surface);color:var(--wg-danger-text);text-decoration-style:dotted;
  text-decoration-color:var(--wg-danger-text);border-radius:2px;}
.xs-tag{display:inline-block;font-family:var(--font-ui);font-size:10.5px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;padding:1px 6px;border-radius:4px;vertical-align:1px;}
.xs-gap{background:var(--mint-100);color:var(--green-text);}
.xs-todo{background:var(--wg-danger-surface);color:var(--wg-danger-text);}
.xs-need{background:var(--wg-warning-surface);color:var(--wg-warning-text);font-weight:600;padding:1px 6px;border-radius:4px;}
.xs-note{margin:8px 0;padding:8px 12px;border-left:3px solid var(--green);background:var(--mint-100);color:var(--green-text);
  font-size:13.5px;line-height:1.55;border-radius:0 var(--r-chip) var(--r-chip) 0;}
.xs-tbl{overflow-x:auto;margin:10px 0;}
.xs-tbl table{border-collapse:collapse;font-size:13.5px;min-width:100%;}
.xs-tbl th,.xs-tbl td{border:1px solid var(--border);padding:7px 10px;text-align:left;vertical-align:top;line-height:1.45;}
.xs-tbl th{background:var(--bg-alt);font-weight:600;}
/* Concepts */
.xs-legend{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;font-size:12.5px;color:var(--ink-600);margin-bottom:12px;}
.xs-tocs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px;}
.xs-toc{font-size:12.5px;padding:5px 11px;border:1px solid var(--border);border-radius:var(--r-pill);background:var(--surface);
  color:var(--ink-600);text-decoration:none;}
.xs-toc:hover{color:var(--ink);border-color:var(--ink-faint);}
.xs-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);padding:20px 24px;
  scroll-margin-top:16px;max-width:900px;}
.xs-card + .xs-card{margin-top:12px;}
.xs-card header{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px;}
.xs-card header h2{font-size:21px;}
.xs-pill{flex:none;font-family:var(--font-ui);font-size:11px;font-weight:600;padding:3px 9px;border-radius:var(--r-pill);
  background:var(--wg-warning-surface);color:var(--wg-warning-text);}
/* Sources */
.xs-stats{font-size:13px;color:var(--ink-600);margin-bottom:8px;}
.xs-intro{font-size:13.5px;color:var(--ink-600);margin-bottom:14px;max-width:860px;}
.xs-intro summary{cursor:pointer;font-weight:600;color:var(--ink);}
.xs-intro ul{padding-left:20px;margin:6px 0;}
.xs-bar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:10px;}
.xs-bar input[type=search]{flex:1 1 260px;min-width:0;font:inherit;font-size:15px;padding:9px 14px;border:1px solid var(--border);
  border-radius:var(--r-chip);background:var(--surface);color:var(--ink);}
.xs-seg{display:inline-flex;border:1px solid var(--border);border-radius:var(--r-chip);overflow:hidden;background:var(--surface);}
.xs-seg button{font:inherit;font-size:12.5px;font-weight:600;border:0;background:none;padding:8px 12px;color:var(--ink-600);cursor:pointer;}
.xs-seg button + button{border-left:1px solid var(--border);}
.xs-seg button[aria-pressed="true"]{background:var(--ink);color:var(--white);}
.xs-row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:6px;}
.xs-rl{font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-faint);min-width:128px;}
.xs-chip{font:inherit;font-size:12.5px;padding:4px 10px;border:1px solid var(--border);border-radius:var(--r-pill);
  background:var(--surface);color:var(--ink-600);cursor:pointer;}
.xs-chip[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:var(--white);}
.xs-chip.xs-none{opacity:.5;}
.xs-n{opacity:.7;font-variant-numeric:tabular-nums;}
.xs-count{font-size:13px;color:var(--ink-600);margin:14px 0 10px;}
.xs-ents{display:flex;flex-direction:column;gap:8px;}
.xs-ent{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);scroll-margin-top:16px;}
.xs-ent[open]{border-color:var(--ink-faint);}
.xs-ent summary{list-style:none;display:flex;align-items:center;gap:12px;padding:12px 16px;cursor:pointer;}
.xs-ent summary::-webkit-details-marker{display:none;}
.xs-chev{flex:none;width:8px;height:8px;border-right:2px solid var(--primary);border-bottom:2px solid var(--primary);
  transform:rotate(-45deg);transition:transform .15s;margin-right:2px;}
.xs-ent[open] .xs-chev{transform:rotate(45deg);}
.xs-eh{display:flex;flex-direction:column;flex:1;min-width:0;}
.xs-eh b{font-family:var(--font-display);font-size:16px;font-weight:600;}
.xs-eh span{font-size:13px;color:var(--ink-600);}
.xs-badges{display:flex;flex-wrap:wrap;gap:5px;justify-content:flex-end;}
.xs-b{font-family:var(--font-ui);font-size:11px;font-weight:600;padding:3px 8px;border-radius:var(--r-chip);
  border:1px solid var(--border);color:var(--ink-600);white-space:nowrap;}
.xs-s-final{background:var(--mint-100);border-color:transparent;color:var(--green-text);}
.xs-s-draft{background:var(--wg-warning-surface);border-color:transparent;color:var(--wg-warning-text);}
.xs-s-todo{border-style:dashed;border-color:var(--wg-danger-text);color:var(--wg-danger-text);}
.xs-eb{padding:4px 20px 18px 40px;border-top:1px solid var(--border);}
.xs-meta{display:grid;grid-template-columns:max-content 1fr;gap:6px 12px;align-items:center;margin:14px 0 6px;}
.xs-meta dt{font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint);}
.xs-meta dd{margin:0;font-size:12.5px;color:var(--ink-600);display:flex;flex-wrap:wrap;gap:5px;}
.xs-ch{font-size:12px;padding:2px 9px;border-radius:var(--r-pill);background:var(--bg-alt);color:var(--ink);}
.xs-chr{background:none;border:1px solid var(--primary);}
.xs-blk{margin-top:16px;max-width:860px;}
.xs-bt{font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
  color:var(--primary);margin:0 0 6px;}
.xs-bh{display:flex;justify-content:space-between;align-items:center;}
.xs-copy{font:inherit;font-size:12px;padding:4px 10px;border:1px solid var(--border);border-radius:var(--r-chip);
  background:var(--surface);color:var(--ink-600);cursor:pointer;}
.xs-cit{background:var(--bg-alt);border-radius:var(--r-chip);padding:12px 14px;font-size:14px;line-height:1.6;word-break:break-word;}
.xs-also{margin-top:14px;font-size:13px;color:var(--ink-600);}
.xs-empty{padding:40px 10px;text-align:center;color:var(--ink-faint);}
.xs-credit{margin-top:24px;font-size:12px;color:var(--ink-faint);line-height:1.6;max-width:900px;}
/* without script every tab shows, stacked; the tab bar and the panel come with JS */
.xs-nojs .xs-tabs,.xs-nojs .xs-aside,.xs-nojs .xs-js{display:none;}
.xs-nojs .xs-snotes[hidden]{display:block!important;}
@media (max-width:1000px){
  .xs-xwrap{grid-template-columns:minmax(0,1fr);}
  .xs-aside{display:none;}
  .xs-paper{padding:24px 20px;}
  .xs-eb{padding-left:20px;}
  .xs-rl{min-width:0;width:100%;}
}
@media print{
  .topbar,.foot,.skip,.ph,.xs-tabs,.xs-tools,.xs-lede,.xs-aside,.xs-snotes,#xs-concepts,#xs-sources,.xs-credit{
    display:none!important;}
  #xs-exec{display:block!important;}
  body{background:#fff;}
  .wrap{padding:0;max-width:none;}
  .xs-xwrap{display:block;}
  .xs-paper{border:0;padding:0;max-width:none;}
  .xs-sec,.xs-sec.xs-on{background:none;border-left-color:transparent;padding:0;margin:18px 0 0;}
  a.xs-cite,a.xs-cite.xs-c-draft,a.xs-cite.xs-c-todo{background:none;color:inherit;text-decoration:none;}
}
"""

BODY = theme.page_header(
    '⟪OSPO executive summary⟫',
    '⟪How to compile one, shown through New York City&rsquo;s: the summary, the notes behind it, its sources.⟫',
    [theme.data_links(ROUTE + '.json'),
     '<a href="/resources">⟪All resources⟫</a>']) + """
<div class="wrap xs-nojs" id="xs-root">
  <main id="main">
    <div class="xs-tabs" role="tablist" aria-label="⟪Research⟫">
      <button type="button" role="tab" id="xs-t-exec" aria-controls="xs-exec" aria-selected="true">⟪Executive Summary⟫</button>
      <button type="button" role="tab" id="xs-t-concepts" aria-controls="xs-concepts" aria-selected="false">⟪Concepts⟫</button>
      <button type="button" role="tab" id="xs-t-sources" aria-controls="xs-sources" aria-selected="false">⟪Sources⟫</button>
    </div>

    <div class="xs-panel-tab" id="xs-exec" role="tabpanel" aria-labelledby="xs-t-exec">
      <div class="xs-tools"><p class="xs-lede">__LX__ ⟪Select a section to see the notes behind it.⟫</p>
        <button type="button" class="xs-btn xs-js" id="xs-print">⟪Print / Save as PDF⟫</button></div>
      <div class="xs-xwrap">
        <article class="xs-paper"><header><h2>__XTITLE__</h2><p>__XSUB__</p></header>__PAPER__</article>
        <aside class="xs-aside" id="xs-panel" aria-live="polite">
          <header><h3 id="xs-panel-h">⟪Notes⟫</h3>
            <button type="button" class="xs-x" id="xs-panel-x" aria-label="⟪Close the notes⟫" hidden>&times;</button></header>
          <div id="xs-panel-b"><p class="xs-hint">⟪Select a section of the summary to see the notes behind it.⟫</p></div>
        </aside>
      </div>
    </div>

    <div class="xs-panel-tab" id="xs-concepts" role="tabpanel" aria-labelledby="xs-t-concepts">
      <p class="xs-lede">__LC__</p>
      <p class="xs-legend"><span>⟪Citations:⟫</span><a class="xs-cite xs-c-final">⟪Final notes⟫</a>
        <span><a class="xs-cite xs-c-draft">⟪Draft Notes⟫</a> ⟪not yet verified⟫</span>
        <span><a class="xs-cite xs-c-todo">TODO</a> ⟪list⟫</span></p>
      <nav class="xs-tocs" aria-label="⟪Concepts sections⟫">__CHIPS__</nav>
      __CARDS__
    </div>

    <div class="xs-panel-tab" id="xs-sources" role="tabpanel" aria-labelledby="xs-t-sources">
      <h2 class="xs-js" style="font-size:22px;margin-bottom:6px">__TS__</h2>
      <p class="xs-lede">__LS__</p>
      <p class="xs-stats">__STATS__</p>
      <details class="xs-intro"><summary>⟪How entries are laid out⟫</summary>__INTRO__</details>
      <div class="xs-js">
        <div class="xs-bar">
          <input type="search" id="xs-q" autocomplete="off" placeholder="⟪Search sources&hellip;⟫" aria-label="⟪Search sources⟫">
          <div class="xs-seg" role="group" aria-label="⟪Notes status⟫" id="xs-st">
            <button type="button" data-st="" aria-pressed="true">⟪All⟫</button>
            <button type="button" data-st="final" aria-pressed="false">⟪Final notes⟫</button>
            <button type="button" data-st="draft" aria-pressed="false">⟪Draft Notes⟫</button>
            <button type="button" data-st="todo" aria-pressed="false">TODO</button></div>
          <button type="button" class="xs-btn" id="xs-open">⟪Expand all⟫</button>
          <button type="button" class="xs-btn" id="xs-close">⟪Collapse all⟫</button>
        </div>
        __ROWS__
        <p class="xs-count" id="xs-count" aria-live="polite"></p>
      </div>
      <div class="xs-ents" id="xs-ents">__ENTRIES__</div>
      <p class="xs-empty" id="xs-empty" hidden>⟪No sources match these filters.⟫</p>
    </div>

    <p class="xs-credit">⟪Research and writing by Olivia Croteau at Sarapis, published here as a read-only copy.
      Draft Notes are not yet verified against their sources; each citation shows its source&rsquo;s status.
      The same data: <a href="/resources/nyc-ospo.json">/resources/nyc-ospo.json</a>.⟫</p>
  </main>
</div>
<script type="application/json" id="xs-data">__CFG__</script>
"""

# Tabs from the hash (#exec, #concepts, #sources, #<entry id>, #c-<concept>,
# #<summary section>); every link to "#..." inside the page goes through go(), so
# a citation opens its entry even when the hash is already that entry.
SCRIPT = """
<script>
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var root = $('xs-root'), L = JSON.parse($('xs-data').textContent).L;
  root.classList.remove('xs-nojs');
  var TABS = ['exec', 'concepts', 'sources'];
  var num = function (n) { return String(n).replace(/\\B(?=(\\d{3})+(?!\\d))/g, L.thou); };
  function tab(t) {
    TABS.forEach(function (k) {
      $('xs-' + k).hidden = k !== t;
      $('xs-t-' + k).setAttribute('aria-selected', k === t ? 'true' : 'false');
    });
  }
  function setHash(h) { try { history.replaceState(null, '', location.pathname + location.search + '#' + h); } catch (e) {} }
  function go(id, scroll) {
    if (TABS.indexOf(id) >= 0) { tab(id); return; }
    var el = id && document.getElementById(id);
    if (!el || !root.contains(el)) { tab('exec'); return; }
    var p = el.closest('.xs-panel-tab');
    tab(p.id.slice(3));
    if (el.classList.contains('xs-ent')) {
      if (el.hidden) clear();
      el.open = true;
    }
    if (el.classList.contains('xs-hasn')) pick(el);
    if (scroll !== false) setTimeout(function () { el.scrollIntoView({block: 'start'}); }, 0);
  }
  TABS.forEach(function (k) {
    $('xs-t-' + k).onclick = function () { tab(k); setHash(k); };
  });
  // in-page links: citations, the Concepts chips
  root.addEventListener('click', function (e) {
    var a = e.target.closest('a[href^="#"]');
    if (!a || !a.getAttribute('href').slice(1)) return;
    e.preventDefault(); var id = a.getAttribute('href').slice(1);
    setHash(id); go(id);
  });
  window.addEventListener('hashchange', function () { go(decodeURIComponent(location.hash.slice(1))); });

  // ---- Executive Summary: a section's notes in the side panel (inline on narrow screens)
  var wide = function () { return window.matchMedia('(min-width:1001px)').matches; };
  var cur = null;
  function pick(sec) {
    if (cur) { cur.classList.remove('xs-on'); $('n-' + cur.id).hidden = true; }
    if (cur === sec) { cur = null; panel(null); return; }
    cur = sec; sec.classList.add('xs-on');
    var n = $('n-' + sec.id);
    if (wide()) panel(n); else { n.hidden = false; panel(null); }
  }
  function panel(n) {
    $('xs-panel-h').textContent = n ? n.dataset.title : $('xs-panel-h').dataset.empty;
    $('xs-panel-b').innerHTML = n ? n.innerHTML : $('xs-panel-b').dataset.empty;
    $('xs-panel-x').hidden = !n;
  }
  $('xs-panel-h').dataset.empty = $('xs-panel-h').textContent;
  $('xs-panel-b').dataset.empty = $('xs-panel-b').innerHTML;
  [].forEach.call(document.querySelectorAll('.xs-sec.xs-hasn'), function (s) {
    s.addEventListener('click', function (e) { if (!e.target.closest('a')) pick(s); });
    s.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(s); } });
  });
  $('xs-panel-x').onclick = function () { if (cur) pick(cur); };
  $('xs-print').onclick = function () { window.print(); };

  // ---- Sources: search, status, three chip rows (AND), counts against the other filters
  var ents = [].slice.call(document.querySelectorAll('.xs-ent')), total = ents.length;
  var text = new Map(ents.map(function (e) { return [e, e.textContent.toLowerCase()]; }));
  var st = {q: '', st: '', 'case': '', role: '', sec: ''};
  var has = {
    'case': function (e, v) { return e.dataset.cases.split('|').indexOf(v) >= 0; },
    role: function (e, v) { return e.dataset.role === v; },
    sec: function (e, v) { return e.dataset.secs.split(' ').indexOf(v) >= 0; }
  };
  function pass(e, skip) {
    if (st.q && text.get(e).indexOf(st.q) < 0) return false;
    if (st.st === 'todo' ? e.dataset.todo !== '1' && e.dataset.st !== 'todo' : st.st && e.dataset.st !== st.st) return false;
    for (var g in has) if (g !== skip && st[g] && !has[g](e, st[g])) return false;
    return true;
  }
  function apply() {
    var n = 0;
    ents.forEach(function (e) { var ok = pass(e); e.hidden = !ok; if (ok) n++; });
    $('xs-count').textContent = L.showing.replace('{n}', num(n)).replace('{t}', num(total));
    $('xs-empty').hidden = n > 0;
    [].forEach.call(document.querySelectorAll('.xs-chip'), function (b) {
      var g = b.dataset.g, v = b.dataset.v, on = st[g] === v;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      var c = b.querySelector('[data-n]');
      if (c) {
        var k = ents.filter(function (e) { return pass(e, g) && has[g](e, v); }).length;
        c.textContent = num(k); b.classList.toggle('xs-none', !k && !on);
      }
    });
    [].forEach.call($('xs-st').children, function (b) { b.setAttribute('aria-pressed', b.dataset.st === st.st ? 'true' : 'false'); });
  }
  function clear() { st = {q: '', st: '', 'case': '', role: '', sec: ''}; $('xs-q').value = ''; apply(); }
  var qt = 0;
  $('xs-q').addEventListener('input', function () {
    var v = this.value; clearTimeout(qt); qt = setTimeout(function () { st.q = v.trim().toLowerCase(); apply(); }, 120);
  });
  [].forEach.call($('xs-st').children, function (b) { b.onclick = function () { st.st = b.dataset.st; apply(); }; });
  [].forEach.call(document.querySelectorAll('.xs-chip'), function (b) {
    b.onclick = function () { st[b.dataset.g] = st[b.dataset.g] === b.dataset.v ? '' : b.dataset.v; apply(); };
  });
  $('xs-open').onclick = function () { ents.forEach(function (e) { if (!e.hidden) e.open = true; }); };
  $('xs-close').onclick = function () { ents.forEach(function (e) { e.open = false; }); };
  [].forEach.call(document.querySelectorAll('.xs-copy'), function (b) {
    b.onclick = function (e) {
      e.preventDefault();
      try { navigator.clipboard.writeText(b.dataset.copy); } catch (x) {}
      b.textContent = L.copied; setTimeout(function () { b.textContent = L.copy; }, 1500);
    };
  });

  apply();
  go(decodeURIComponent(location.hash.slice(1)) || 'exec', !!location.hash);
})();
</script>
"""


if __name__ == "__main__":
    d = load()
    for _lang in i18n.LANGS:
        build(_lang, d)
    # the data as one request, for agents: the redacted research as published
    os.makedirs(os.path.dirname(f"{SITE}{ROUTE}.json"), exist_ok=True)
    with open(f"{SITE}{ROUTE}.json", "w", encoding="utf-8") as fh:
        json.dump({"generated_at": NOW, "human_page": i18n.BASE + ROUTE,
                   "about": "The research behind a proposed open source program office for New York City, by "
                            "Olivia Croteau (Sarapis), published as a worked example of compiling an OSPO "
                            "executive summary. status 'draft' notes are not yet verified against their source. "
                            "exec_sections and role tag each source by the summary section it supports and how "
                            "another city can use it, as on /resources.",
                   "meta": d["meta"], "executive_summary": d["executive-summary"],
                   "concepts": d["concepts"], "bibliography": d["bibliography"]},
                  fh, ensure_ascii=False, indent=1)
    i18n.report("build_nyc_ospo")

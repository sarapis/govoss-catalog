"""Build site/resources.html (served at /resources) + site/resources.json.

OSPO resources: the documents, decisions and accounts six public-sector open
source program offices are built from - Munich, Paris, Barcelona, the European
Commission, the UN and the US Centers for Medicare & Medicaid Services - each
with what it is for and how to use it when building an OSPO.

The data is NOT harvested: resources/ospo-resources.json is a committed snapshot
of the merged catalogue compiled by UN+NYC (un.opensource.nyc; its per-case
files are canonical, this is their convenience merge). Replace the file to
update the page. Its records are DATA, so they stay English on every language
copy, like entry descriptions; only the page chrome is translated.

Cards are STATIC HTML, like /products: 155 is small, the page works with no
script, and an agent reading raw HTML gets every record. The script only hides
cards (el.hidden - theme.py ships [hidden]{display:none!important}) and keeps
the view in the address bar, validated the same way /software does.

No f-strings for markup: plain strings with __PLACEHOLDER__ tokens.
"""
import collections
import importlib.util
import json
import os
import re
import time

import i18n

OUT = os.path.dirname(os.path.abspath(__file__))
SITE = f"{OUT}/site"
SRC = f"{OUT}/resources/ospo-resources.json"
# govoss's OWN additions, same record shape, kept out of the UN+NYC file so a
# replacement of that file never drops them and never credits them to UN+NYC.
ADD = f"{OUT}/resources/govoss-additions.json"
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

_th = importlib.util.spec_from_file_location("theme", f"{OUT}/theme.py")
theme = importlib.util.module_from_spec(_th); _th.loader.exec_module(theme)
_tp = importlib.util.spec_from_file_location("_ui_template", f"{OUT}/_ui_template.py")
T = importlib.util.module_from_spec(_tp); _tp.loader.exec_module(T)

# Short names for the facet and the card; the file's own long names are kept for
# the card's title attribute. A case not listed here falls back to its long name.
CASE_SHORT = {"munich": "Munich", "paris": "Paris", "barcelona": "Barcelona",
              "ec": "European Commission", "un": "United Nations", "cms": "US CMS",
              "networks": "OSPO networks"}
LANG_NAME = {"en": "English", "de": "German", "fr": "French", "ca": "Catalan"}


def esc(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def human(v):
    """office_description -> Office description. Category and type values are
    data; humanised, never translated."""
    v = str(v or "").replace("_", " ").strip()
    return v[:1].upper() + v[1:]


def load():
    d = json.load(open(SRC))
    rs = d.get("resources")
    if not isinstance(rs, list) or not rs:
        raise SystemExit("build_resources: %s has no resources[]" % SRC)
    if d.get("total") not in (None, len(rs)):
        # The file states its own count; disagreeing with it means a truncated copy.
        raise SystemExit("build_resources: file says total=%s but carries %d records"
                         % (d.get("total"), len(rs)))
    add = json.load(open(ADD))
    clash = {r["id"] for r in add["resources"]} & {r["id"] for r in rs}
    if clash or any(r.get("added_by") != "govoss" for r in add["resources"]):
        raise SystemExit("build_resources: %s must use new ids and mark each record "
                         "added_by govoss (clash: %s)" % (ADD, sorted(clash)))
    return d, rs, add


def build(lang, d, rs, add):
    _ = lambda msg, **kw: i18n.t(lang, msg, **kw)
    N = lambda n: i18n.num(lang, n)
    cases = {c["id"]: c for c in (d.get("cases") or []) + (add.get("cases") or [])}
    short = lambda cid: CASE_SHORT.get(cid) or (cases.get(cid) or {}).get("name") or cid
    # the lede and description count the UN+NYC compilation; the cards are all of it
    n_compiled, n_cases = len(rs), len({r["case"] for r in rs})
    rs = rs + add["resources"]

    by_case = collections.Counter(r["case"] for r in rs)
    by_cat = collections.Counter(r["category"] for r in rs)
    by_lang = collections.Counter(r["language"] for r in rs)
    n_pb = sum(1 for r in rs if r.get("playbook_rank") is not None)

    def group(key, title, counter, label):
        opts = "".join(
            '<button type="button" class="rfopt" data-g="%s" data-v="%s" aria-pressed="false">'
            '<span>%s</span><span class="rn">%s</span></button>'
            % (key, esc(v), esc(label(v)), N(n)) for v, n in counter.most_common())
        return ('<div class="rfgroup"><h3>%s</h3><div class="rfopts">%s</div></div>'
                % (esc(title), opts))

    facets = (group("case", _("OSPO"), by_case, short)
              + group("cat", _("Category"), by_cat, human)
              + group("lang", _("Language"), by_lang, lambda v: LANG_NAME.get(v, v)))

    cards = []
    for i, r in enumerate(rs):
        pb = r.get("playbook_rank")
        meta = [esc(r.get("publisher")), esc(r.get("date") if r.get("date") != "n.d." else _("undated")),
                esc(LANG_NAME.get(r["language"], r["language"]))]
        tags = ('<span class="tag">%s</span><span class="tag">%s</span>'
                % (esc(human(r["category"])), esc(human(r["type"]))))
        if pb is not None:
            tags = '<span class="tag pb">%s</span>' % esc(_("Playbook #{n}", n=pb)) + tags
        extra = ""
        if r.get("notes"):
            extra += '<p class="rnote">%s</p>' % esc(r["notes"])
        if r.get("verification_status") and r["verification_status"] != "opened":
            extra += ('<p class="rnote">%s</p>'
                      % esc(_("Listed but not opened by the compilers - check the link before relying on it.")))
        cards.append(
            '<li class="res" id="%s" data-case="%s" data-cat="%s" data-lang="%s" data-pb="%s" '
            'data-date="%s" data-i="%d">'
            '<div class="reshead"><span class="rcase" title="%s">%s</span>%s</div>'
            '<h3><a href="%s" target="_blank" rel="noopener">%s</a></h3>'
            '<p class="rmeta">%s</p>'
            '<p class="rfor">%s</p>'
            '<p class="ruse"><b>%s</b> %s</p>%s'
            '<details><summary>%s</summary><p class="rcite">%s</p></details>'
            '</li>'
            % (esc(r["id"]), esc(r["case"]), esc(r["category"]), esc(r["language"]),
               "" if pb is None else pb, esc(r.get("date") or ""), i,
               esc((cases.get(r["case"]) or {}).get("name") or ""), esc(short(r["case"])), tags,
               esc(r["url"]), esc(r["title"]),
               " &middot; ".join(meta),
               esc(r["what_it_is_for"]),
               esc(_("For building an OSPO:")), esc(r["use_for_ospo_construction"]), extra,
               esc(_("Citation")), esc(r["citation"])))

    added = ""
    if add["resources"]:
        added = ('<p class="rcred">%s</p>'
                 % _("{n} more added by govoss, marked on each card: networks of open source "
                     "program offices rather than offices. In /resources.json they are kept apart "
                     "from the compilation, under added_by_govoss.", n=N(len(add["resources"]))))
    subs = {
        "__N__": N(n_compiled),
        "__NALL__": N(len(rs)),
        "__NCASES__": N(n_cases),
        "__ADDED__": added,
        "__NPB__": N(n_pb),
        "__FACETS__": facets,
        "__CARDS__": "".join(cards),
        "__VERSION__": esc(d.get("catalogue_version") or ""),
        "__LANG__": lang,
    }
    page = (theme.head(
        _("OSPO resources | govoss"),
        _("{n} documents, decisions and accounts from {k} public-sector open source program "
          "offices, each with what it is for and how to use it when building an OSPO.",
          n=N(n_compiled), k=n_cases), lang=lang, route="/resources")
        + "<style>\n" + theme.FONT_FACE_CSS + theme.CSS + T.PAGE_CSS + PAGE_CSS + "</style>\n"
        + theme.utility_bar(lang=lang) + theme.topbar("resources", lang, "/resources")
        + BODY + theme.footer(lang=lang) + SCRIPT)
    page = i18n.markers(page, lang)
    for k, v in subs.items():
        page = page.replace(k, v)
    left = sorted(set(re.findall(r"__[A-Z_]{3,}__", page)))
    if left:
        raise SystemExit("build_resources: unsubstituted placeholders %s" % left)
    page = i18n.links(page, lang)
    theme.assert_variant_live(page)
    page = page.encode("ascii", "xmlcharrefreplace").decode()
    out = f"{SITE}/resources.html" if lang == "en" else f"{SITE}/{lang}/resources.html"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(page)
    print("resources page [%s]: %d resources from %d OSPOs (%.0f KB)"
          % (lang, len(rs), len(by_case), len(page) / 1024))


PAGE_CSS = """
.rwrap{display:flex;gap:28px;align-items:flex-start;margin-top:28px;}
.rside{flex:0 0 250px;position:sticky;top:16px;max-height:calc(100vh - 32px);overflow:auto;
  background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);padding:16px;}
.rmain{flex:1 1 auto;min-width:0;}
@media (max-width:860px){.rwrap{flex-direction:column;}.rside{position:static;max-height:none;
  flex-basis:auto;width:100%;box-sizing:border-box;}}
.rfgroup + .rfgroup{margin-top:16px;}
.rfgroup h3{font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ink-faint);margin:0 0 6px;}
.rfopts{display:flex;flex-direction:column;gap:2px;}
.rfopt{display:flex;justify-content:space-between;gap:8px;font:inherit;font-size:13px;text-align:left;
  background:none;border:0;border-radius:6px;padding:5px 8px;color:var(--ink-600);cursor:pointer;}
.rfopt:hover{background:var(--bg-alt);color:var(--ink);}
.rfopt[aria-pressed="true"]{background:var(--primary-tint);color:var(--ink);font-weight:600;}
.rfopt .rn{color:var(--ink-faint);font-variant-numeric:tabular-nums;}
.rfopt:focus-visible,.rtog:focus-visible{outline:2px solid var(--primary);outline-offset:1px;}
.rbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}
.rbar input[type=search]{flex:1 1 260px;min-width:0;font:inherit;font-size:15px;padding:10px 14px;
  border:1px solid var(--border);border-radius:var(--r-chip);background:var(--surface);color:var(--ink);}
.rbar select{font:inherit;font-size:13px;padding:9px 10px;border:1px solid var(--border);
  border-radius:var(--r-chip);background:var(--surface);color:var(--ink);}
.rtog{font:inherit;font-size:13px;font-weight:600;padding:9px 12px;border:1px solid var(--border);
  border-radius:var(--r-chip);background:var(--surface);color:var(--ink-600);cursor:pointer;}
.rtog[aria-pressed="true"]{background:var(--primary-tint);color:var(--ink);}
.rcount{margin:14px 0 10px;font-size:13px;color:var(--ink-600);}
.rlist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px;}
.res{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);padding:16px 18px;}
.res .reshead{display:flex;flex-wrap:wrap;gap:6px;align-items:center;}
.rcase{font-family:var(--font-ui);font-size:11px;font-weight:600;letter-spacing:.1em;
  text-transform:uppercase;color:var(--primary);margin-right:4px;}
.tag{font-size:11px;padding:2px 8px;border-radius:var(--r-chip);background:var(--bg-alt);color:var(--ink-600);}
.tag.pb{background:var(--mint-100);color:var(--green-text);font-weight:600;}
.res h3{font-family:var(--font-display);font-size:17px;margin:8px 0 2px;line-height:1.3;}
.res h3 a{color:var(--ink);text-decoration:none;}
.res h3 a:hover{color:var(--primary);text-decoration:underline;}
.rmeta{font-size:12px;color:var(--ink-faint);margin:0 0 8px;}
.rfor{margin:0 0 6px;font-size:14px;color:var(--ink);line-height:1.5;text-wrap:pretty;}
.ruse{margin:0;font-size:13px;color:var(--ink-600);line-height:1.5;text-wrap:pretty;}
.rnote{margin:6px 0 0;font-size:12px;color:var(--ink-faint);}
.res details{margin-top:8px;font-size:12px;color:var(--ink-faint);}
.res summary{cursor:pointer;}
.rcite{margin:6px 0 0;word-break:break-word;}
.rcred{margin-top:18px;font-size:12px;color:var(--ink-faint);}
"""

BODY = """
<div class="hero hero-sw tex">
  <div class="inner">
    <p class="overline">⟪Resources⟫</p>
    <h1>⟪OSPO resources⟫</h1>
    <p class="lede">⟪__N__ documents, decisions and accounts from __NCASES__ public-sector open
      source program offices, each with what it is for and how to use it when building an
      OSPO. Compiled by <a href="https://un.opensource.nyc">UN+NYC</a>.⟫</p>
  </div>
</div>
<div class="wrap">
  <main id="main" class="rwrap">
    <aside class="rside" aria-label="⟪Filters⟫">__FACETS__</aside>
    <div class="rmain">
      <div class="rbar">
        <input type="search" id="rq" autocomplete="off" placeholder="⟪Search resources&hellip;⟫"
               aria-label="⟪Search resources⟫">
        <button type="button" class="rtog" id="rpb" aria-pressed="false">⟪In a playbook⟫ (__NPB__)</button>
        <select id="rsort" aria-label="⟪Sort resources⟫">
          <option value="case">⟪Sort: by OSPO⟫</option>
          <option value="pb">⟪Sort: playbook order⟫</option>
          <option value="new">⟪Sort: newest first⟫</option>
          <option value="title">⟪Sort: title A&ndash;Z⟫</option>
        </select>
      </div>
      <p class="rcount" id="rcount" aria-live="polite">⟪__NALL__ resources⟫</p>
      <ul class="rlist" id="rlist">__CARDS__</ul>
      <p class="rcred">⟪Catalogue version __VERSION__, compiled by
        <a href="https://un.opensource.nyc">UN+NYC</a>. Records are shown as compiled, in
        English. The same data as one file: <a href="/resources.json">/resources.json</a>.⟫</p>
      __ADDED__
    </div>
  </main>
</div>
"""

# The view lives in the address bar (q, case, cat, lang, pb, sort), read once
# and written by every change - the same contract as /software: every value is
# validated against what the page offers, and an unknown one is IGNORED.
SCRIPT = """
<script>
(function () {
  var el = function (id) { return document.getElementById(id); };
  var list = el('rlist'), cards = [].slice.call(list.children);
  // search reads each card's own text (title, publisher, both notes, citation,
  // tags), lower-cased once - not a hidden copy, which doubled the page
  var text = new Map(cards.map(function (c) { return [c, c.textContent.toLowerCase()]; }));
  var on = { 'case': new Set(), cat: new Set(), lang: new Set() };
  var opts = [].slice.call(document.querySelectorAll('.rfopt'));
  var offered = {};
  opts.forEach(function (b) {
    (offered[b.dataset.g] = offered[b.dataset.g] || new Set()).add(b.dataset.v);
  });
  var pbOnly = false, timer = null;
  var total = cards.length;

  function apply(write) {
    var q = (el('rq').value || '').trim().toLowerCase(), n = 0;
    cards.forEach(function (c) {
      var ok = (!q || text.get(c).indexOf(q) >= 0) &&
        (!on['case'].size || on['case'].has(c.dataset['case'])) &&
        (!on.cat.size || on.cat.has(c.dataset.cat)) &&
        (!on.lang.size || on.lang.has(c.dataset.lang)) &&
        (!pbOnly || c.dataset.pb !== '');
      c.hidden = !ok;
      if (ok) n++;
    });
    var sort = el('rsort').value;
    var idx = function (c) { return +c.dataset.i; };
    var dated = function (c) { return /^\\d{4}/.test(c.dataset.date); };
    var cmp = {
      // file order: grouped by OSPO, as the compilers ordered them
      'case': function (a, b) { return idx(a) - idx(b); },
      // ranked items first (rank counts within each OSPO's playbook), unranked after
      pb: function (a, b) {
        var x = a.dataset.pb === '' ? Infinity : +a.dataset.pb;
        var y = b.dataset.pb === '' ? Infinity : +b.dataset.pb;
        return x === y ? idx(a) - idx(b) : x < y ? -1 : 1;
      },
      // dated items newest first; undated ("n.d.") last, in file order
      'new': function (a, b) {
        if (dated(a) !== dated(b)) return dated(a) ? -1 : 1;
        return b.dataset.date.localeCompare(a.dataset.date) || idx(a) - idx(b);
      },
      title: function (a, b) {
        return a.querySelector('h3').textContent.localeCompare(b.querySelector('h3').textContent);
      }
    }[sort];
    cards.slice().sort(cmp).forEach(function (c) { list.appendChild(c); });
    el('rcount').textContent = n === total ? '⟪js:{n} resources⟫'.replace('{n}', total)
      : '⟪js:{n} of {t} resources⟫'.replace('{n}', n).replace('{t}', total);
    opts.forEach(function (b) {
      b.setAttribute('aria-pressed', on[b.dataset.g].has(b.dataset.v) ? 'true' : 'false');
    });
    el('rpb').setAttribute('aria-pressed', pbOnly ? 'true' : 'false');
    if (write) writeURL();
  }
  function writeURL() {
    var P = new URLSearchParams(), q = (el('rq').value || '').trim();
    if (q) P.set('q', q);
    ['case', 'cat', 'lang'].forEach(function (k) { on[k].forEach(function (v) { P.append(k, v); }); });
    if (pbOnly) P.set('pb', '1');
    if (el('rsort').value !== 'case') P.set('sort', el('rsort').value);
    var qs = P.toString(), url = location.pathname + (qs ? '?' + qs : '') + location.hash;
    clearTimeout(timer);
    timer = setTimeout(function () { try { history.replaceState(null, '', url); } catch (e) {} }, 250);
  }
  try {
    var P = new URLSearchParams(location.search);
    if (P.get('q')) el('rq').value = P.get('q');
    ['case', 'cat', 'lang'].forEach(function (k) {
      P.getAll(k).forEach(function (v) { if (offered[k] && offered[k].has(v)) on[k].add(v); });
    });
    if (P.get('pb') === '1') pbOnly = true;
    var s = P.get('sort');
    if (s && [].some.call(el('rsort').options, function (o) { return o.value === s; })) el('rsort').value = s;
  } catch (e) {}
  opts.forEach(function (b) {
    b.onclick = function () {
      var g = on[b.dataset.g];
      if (g.has(b.dataset.v)) g.delete(b.dataset.v); else g.add(b.dataset.v);
      apply(true);
    };
  });
  el('rpb').onclick = function () { pbOnly = !pbOnly; apply(true); };
  el('rq').oninput = function () { apply(true); };
  el('rsort').onchange = function () { apply(true); };
  apply(false);
})();
</script>
"""


if __name__ == "__main__":
    d, rs, add = load()
    for _lang in i18n.LANGS:
        build(_lang, d, rs, add)
    # the data as one request, for agents: the file as compiled, plus where it is shown,
    # and govoss's own additions under their own key - never mixed into resources[]
    with open(f"{SITE}/resources.json", "w") as fh:
        json.dump({"generated_at": NOW, "human_page": i18n.BASE + "/resources", **d,
                   "added_by_govoss": add}, fh, ensure_ascii=False, indent=1)
    i18n.report("build_resources")

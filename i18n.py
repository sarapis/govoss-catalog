#!/usr/bin/env python3
"""Page localisation: English source, Catalan (and any later language) from a file.

The pages are built once per language: English at /, Catalan at /ca/. The DATA
stays as it is - descriptions, source notes, survey write-ups and the API
contract (field rules, MCP tool definitions) are English on both, because they
are data or a contract, not page chrome. Phase 2 would translate the data.

Two ways text gets translated, both keyed on the ENGLISH text itself (a gettext
msgid), so the English template stays readable and a reworded string simply
stops matching instead of showing a stale translation:

  markers   in the static templates: ⟪English text⟫ for HTML, ⟪js:English text⟫
            inside a single-quoted JS string. Resolved while __PLACEHOLDERS__ are
            still intact, so a msgid like "Search __NENTRIES__ entries" is stable.
  t()       for strings built in Python: t(lang, "last good {n}d ago", n=5).
            Named arguments, because Catalan word order differs ("fa {n} d").

Why not a find-and-replace pass over rendered English: that is the "string-
replace patching fails silently" bug CLAUDE.md lists. Markers can be checked -
localize() fails the build if one survives - and a MISSING translation falls
back to English and is written to out/i18n_missing.json, which /sources.html
warns on, instead of vanishing.

⚠ JS context escapes. Catalan is full of apostrophes (l'entrada, d'una) and
accented letters; inside a single-quoted JS string the first breaks the script
and the second breaks the pure-ASCII rule, because entities are NOT decoded
inside <script>. ⟪js:…⟫ emits \\uXXXX for both.
"""
import json
import os
import re

OUT = os.path.dirname(os.path.abspath(__file__))
LANGS = ("en", "ca")
from sources import SITE_URL as BASE        # the one place the address is written
NAMES = {"en": "English", "ca": "Català"}

# Page routes that have a Catalan counterpart. Everything else root-relative
# (/entries.json, /fonts/, /llms.txt, /sarapis-mark.png) is language-neutral.
ROUTES = ("/", "/index.html", "/sources.html", "/api.html", "/products.html")

_MARK = re.compile(r"⟪(js:)?(.*?)⟫", re.S)
_TOKENS = re.compile(r"__[A-Z0-9_]{3,}__|\{[a-z_]+\}")

MISSING = set()


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def _load(lang):
    if lang == "en":
        return {}
    path = os.path.join(OUT, "i18n", "%s.json" % lang)
    raw = json.load(open(path, encoding="utf-8"))
    strings = {norm(k): v for k, v in raw.get("strings", {}).items()}
    # Our own file, so a broken translation FAILS the build: a translation that
    # drops or invents a placeholder would render "__NENTRIES__" or lose a number.
    bad = [k for k, v in strings.items()
           if sorted(_TOKENS.findall(k)) != sorted(_TOKENS.findall(v))]
    if bad:
        raise SystemExit("i18n/%s.json: placeholders differ from the English in %d "
                         "string(s): %s" % (lang, len(bad), bad[:3]))
    return {"strings": strings, "functions": raw.get("functions", {}),
            "countries": raw.get("countries", {})}


_CACHE = {}


def table(lang):
    if lang not in _CACHE:
        _CACHE[lang] = _load(lang)
    return _CACHE[lang]


def t(lang, msg, **kw):
    """Translate one English string; format named arguments afterwards."""
    out = msg
    if lang != "en":
        hit = table(lang)["strings"].get(norm(msg))
        if hit is None:
            MISSING.add((lang, norm(msg)))
        else:
            out = hit
    return out.format(**kw) if kw else out


def function(lang, key, english):
    return english if lang == "en" else table(lang)["functions"].get(key, english)


def country(lang, code, english):
    return english if lang == "en" else table(lang)["countries"].get(code, english)


def num(lang, n):
    """Thousands separator: 2,857 in English, 2.857 in Catalan."""
    s = "{:,}".format(n)
    return s.replace(",", ".") if lang == "ca" else s


def _js(s):
    out = []
    for ch in s:
        if ch in "'\\" or ord(ch) > 126:
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)


def markers(page, lang):
    """Resolve every ⟪…⟫ marker. Run BEFORE placeholder substitution."""
    def rep(m):
        js, text = m.group(1), m.group(2)
        out = t(lang, text) if lang != "en" else text
        return _js(out) if js else out
    page = _MARK.sub(rep, page)
    if "⟪" in page or "⟫" in page:
        raise SystemExit("i18n: an unbalanced ⟪…⟫ marker survived localisation")
    return page


def path_for(lang, route):
    """/sources.html -> /ca/sources.html; / -> /ca/."""
    if lang == "en":
        return route
    return "/%s%s" % (lang, "/" if route in ("/", "/index.html") else route)


_TAG = re.compile(r'<(?:a|link)\b[^>]*>')
_HREF_IN = re.compile(r'\shref="(/[^"]*)"')


def links(page, lang):
    """Point root-relative page links at this language's copy.

    Works on whole <a>/<link> tags. Anything carrying `hreflang` is left alone:
    that is the language switcher and the alternate links, which must point at
    the OTHER language. Language-neutral paths (/entries.json, /fonts/...) are
    left alone because they are not in ROUTES."""
    if lang == "en":
        return page

    def fix(href):
        cut = min([i for i in (href.find("?"), href.find("#")) if i >= 0] or [len(href)])
        route, rest = href[:cut] or "/", href[cut:]
        return path_for(lang, route) + rest if route in ROUTES else href

    def rep(m):
        tag = m.group(0)
        if "hreflang=" in tag:
            return tag
        return _HREF_IN.sub(lambda h: ' href="%s"' % fix(h.group(1)), tag)
    return _TAG.sub(rep, page)


def alternates(route):
    """<link rel=alternate hreflang> for every language, plus x-default."""
    out = ['<link rel="alternate" hreflang="%s" href="%s%s">' % (l, BASE, path_for(l, route))
           for l in LANGS]
    out.append('<link rel="alternate" hreflang="x-default" href="%s%s">' % (BASE, route))
    return "\n".join(out) + "\n"


def switcher(lang, route):
    """A link to every OTHER language's copy of this page, named in its own language."""
    return " ".join('<a class="langsw" hreflang="%s" lang="%s" href="%s">%s</a>'
                    % (l, l, path_for(l, route), NAMES[l]) for l in LANGS if l != lang)


def report(builder):
    """Record this builder's missing translations in out/i18n_missing.json.

    Merged per builder, because each page builder is its own process. A builder
    with nothing missing clears its own entry, so the file self-clears."""
    path = os.path.join(OUT, "out", "i18n_missing.json")
    try:
        cur = json.load(open(path, encoding="utf-8"))
    except Exception:
        cur = {}
    mine = sorted({"%s: %s" % (l, s) for l, s in MISSING})
    if mine:
        cur[builder] = mine
    else:
        cur.pop(builder, None)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(cur, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False, sort_keys=True)
    if mine:
        print("   [i18n] %d string(s) with no translation, shown in English: %s"
              % (len(mine), "; ".join(mine[:3])))

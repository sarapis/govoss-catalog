#!/bin/bash
# Assemble the Vercel deploy directory from tracked sources.
#
# site/ is gitignored (it holds an 821KB copy of catalogue.html plus a ~2.8MB
# JSON export), so it MUST be fully reproducible from tracked files — an earlier
# revision kept vercel.json only inside site/, where the next rebuild would have
# silently dropped the CORS and content-type headers.
#
# The redirects in deploy-vercel.json exist because the first agent to use this
# catalogue probed /api/entries, /api/catalog, /data.json and /catalog.json and
# got 404 from all of them. Cheaper to answer where callers already look than to
# expect them to read docs.
#
# Content-Type is scoped to *.json and "/" separately on purpose: a blanket
# text/html on /(.*) would serve entries.json as HTML.
#
# Fonts are VENDORED, not loaded from a CDN. The design system's own CSS pulls
# Space Grotesk / Archivo / Inter from fonts.googleapis.com, which fails two
# tests here: the pages are self-contained by rule, and the readership is
# European public-sector staff, for whom a Google Fonts request is a live GDPR
# objection. So fonts/ is tracked in the repo and copied to site/fonts/, served
# same-origin. The OFL requires the licence travel with the fonts, so the
# OFL-*.txt files are copied too - do not drop them to save bytes.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p site site/fonts
cp catalogue.html site/index.html
cp deploy-vercel.json site/vercel.json
cp fonts/*.woff2 fonts/OFL-*.txt site/fonts/
echo "site/ assembled: index.html + vercel.json + $(ls fonts/*.woff2 | wc -l | tr -d ' ') fonts"

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
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p site
cp catalogue.html site/index.html
cp deploy-vercel.json site/vercel.json
echo "site/ assembled: index.html + vercel.json"

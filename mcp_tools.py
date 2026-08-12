#!/usr/bin/env python3
"""The MCP server's shape, defined ONCE.

Both the /api.html page and the Worker that implements the server read this
file. That is the same rule sources.py established for source labels: two copies
of a contract are two contracts, and a page that documents a tool the server
does not implement is worse than no page at all - this one is read by agents,
which cannot tell the difference until the call fails.

ENDPOINT is None until the Worker is actually deployed. While it is None the API
page renders the MCP section as "not live yet" rather than printing a URL that
answers nothing. The design handoff invented an endpoint and five tool names;
the names survived because they turned out to describe what the data really
supports, but the URL is not invented here - it stays empty until it exists.
"""

# Set this to the deployed Worker URL. Nothing else needs changing: the page and
# the server both derive from it.
ENDPOINT = None

# Why a separate Worker rather than a Vercel function: the catalogue deployment
# is deliberately backend-free - it is a directory of static files behind a CDN,
# which is why it has never had an outage. Adding a serverless function to it
# would trade that guarantee for one feature. The Worker fetches the same public
# entries.json everyone else does, so the server has no privileged access and
# cannot drift from the published data.

TOOLS = [
    {
        "name": "search_entries",
        "args": "query?: string, country?: string, function?: string, "
                "source?: string, licence?: string, limit?: number = 20",
        "returns": "matching entries, most-catalogued first",
        "desc": "Full-text search over name, description, owner and also-known-as, "
                "with optional facet filters. Every filter is AND-ed.",
    },
    {
        "name": "find_replacements",
        "args": "product: string",
        "returns": "entries that can replace that product, with confidence and kind",
        "desc": "The procurement question, answered from an invoice line: give it "
                "'Qualtrics' and it returns the open source alternatives, each marked "
                "strong / partial / adjacent and software / service / paid-tier.",
    },
    {
        "name": "get_entry",
        "args": "id: string",
        "returns": "one entry, every field",
        "desc": "Fetch a single entry by its stable id, including the deep links back "
                "to each government catalogue that lists it.",
    },
    {
        "name": "list_sources",
        "args": "include_survey?: boolean = false",
        "returns": "the catalogues harvested, optionally those surveyed and rejected",
        "desc": "Where the data comes from, with each catalogue's access route and "
                "entry count. With include_survey, also the ones checked and rejected "
                "and why - which saves repeating a dead end.",
    },
    {
        "name": "get_stats",
        "args": "(none)",
        "returns": "counts, category enum, freshness",
        "desc": "How big the catalogue is, when it was last harvested, and the "
                "controlled vocabulary for functions and countries.",
    },
]

# Fields whose value carries a rule a consumer has to know about. Shown on the
# API page beside a real entry, because these are the ones where a naive reading
# is wrong in a way that matters.
FIELD_RULES = [
    ("licence", "null when the upstream catalogue did not state a real SPDX identifier. "
                "It is never guessed from the repository - an spdx-named field holding "
                "'GPLv3+' is worse than a null, because a consumer will trust the name."),
    ("entry_url", "null when a catalogue has no per-entry page. A constructed link would "
                  "404 for about 40% of one source, so it is left empty instead."),
    ("link_dead", "true only after TWO consecutive failed checks. Single 404s oscillate - "
                  "an unstable signal is worse than a steady wrong one, because it trains "
                  "you to ignore the report."),
    ("replaces", "hand-curated, not inferred. Each carries `confidence` "
                 "(strong/partial/adjacent) and `kind`: software replaces the software, "
                 "service means the paid item is hosting or content, paid-tier means it is "
                 "a commercial edition of something already open source."),
    ("excluded", "the entry was harvested but held out of the default view - forks, CI "
                 "plumbing, deployment recipes, locale bundles. It keeps `exclude_reason` "
                 "and stays in the data; it is flagged, never deleted."),
    ("translated_from", "set when the description is machine-translated, with the original "
                        "in `description_original`. Absent means the publisher wrote it in "
                        "English - the two are never conflated."),
    ("catalogues", "one object per government catalogue that lists this software, each with "
                   "a deep link, so a cross-listing claim can be verified upstream rather "
                   "than taken on trust."),
]

ETIQUETTE = [
    ("do", "Cache it for a week", "The catalogue is rebuilt on Mondays. Polling more often "
           "than that cannot return anything new; `generated_at` in /meta.json tells you "
           "when it last changed."),
    ("do", "Use the MCP server for interactive work", "If an agent needs a handful of "
           "entries rather than all 3,070, the server does the filtering server-side and "
           "returns kilobytes instead of megabytes."),
    ("dont", "Don't drive a browser at the HTML", "The first consumer of this catalogue "
             "probed eight dead API paths and then ran a headless browser. Everything the "
             "page shows comes from entries.json, which is one request and always current."),
    ("dont", "Don't probe for endpoints", "There are five, they are all on this page, and "
             "there is no /v2, no GraphQL and no undocumented search to discover. "
             "/api/entries, /api/catalog, /catalog.json and /data.json redirect here "
             "because they are what the first consumer tried."),
]

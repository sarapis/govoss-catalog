#!/usr/bin/env python3
"""Single source of truth for source identity: labels, links, access route.

Imported by build_ui.py, export_json.py and build_sources.py so a URL is never
written twice and can never disagree between the page, the JSON and the docs.

`survey` records catalogues found while looking globally that are NOT ingested,
with the reason. Recording a verified dead end is worth as much as recording a
live source — it stops the next person re-probing code.gov and concluding the
same thing three months later.
"""

# ---- ingested sources
SOURCES = {
    "IT/developers-italia": {
        "label": "Developers Italia", "country": "IT", "flag": "\U0001F1EE\U0001F1F9",
        "site": "https://developers.italia.it/en/software",
        "api": "https://api.developers.italia.it/v1/software",
        "route": "REST API", "claim": "built for public administration",
        "note": "The best of the ten: documented REST API, cursor pagination, "
                "publiccode.yml verbatim per entry.",
    },
    "FR/sill": {
        "label": "SILL", "country": "FR", "flag": "\U0001F1EB\U0001F1F7",
        "site": "https://code.gouv.fr/sill",
        "api": "https://code.gouv.fr/sill/api/sill.json",
        "route": "bulk JSON", "claim": "recommended to public agents",
        "note": "Socle Interministeriel de Logiciels Libres. Use the /sill/api/ export, "
                "NOT /data/sill.json - the latter has no url field at all and carries "
                "Wikidata QIDs nowhere.",
    },
    "FR/awesome-codegouvfr": {
        "label": "awesome-codegouvfr", "country": "FR", "flag": "\U0001F1EB\U0001F1F7",
        "site": "https://code.gouv.fr/",
        "api": "https://code.gouv.fr/data/awesome-codegouvfr.json",
        "route": "bulk JSON", "claim": "curated French public-sector",
    },
    "DE/openCode": {
        "label": "openCode", "country": "DE", "flag": "\U0001F1E9\U0001F1EA",
        "site": "https://opencode.de/en/software",
        "api": "https://gitlab.opencode.de/api/v4/projects",
        "route": "GitLab API", "claim": "built for public administration",
        "note": "No public API on the site, but its directory slugs embed the GitLab "
                "project id and the listing is generated from publiccode.yml in that "
                "GitLab - so the forge API reproduces the official directory exactly.",
    },
    "NL/code.overheid.nl": {
        "label": "code.overheid.nl", "country": "NL", "flag": "\U0001F1F3\U0001F1F1",
        "site": "https://code.overheid.nl/",
        "api": "https://code.overheid.nl/api/v1/repos/search",
        "route": "Forgejo API", "claim": "published by Dutch government bodies",
        "note": "The government's own self-hosted Forgejo. Open api/v1, no auth - which "
                "makes the separate OSS register's API key unnecessary for coverage.",
    },
    "BE/iMio": {
        "label": "iMio", "country": "BE", "flag": "\U0001F1E7\U0001F1EA",
        "site": "https://www.imio.be/",
        "api": "https://api.github.com/orgs/IMIO/repos",
        "route": "GitHub org", "claim": "built by Walloon municipalities",
        "note": "236 repos but only one publiccode.yml, so the rest are indexed from bare "
                "GitHub metadata and 32 forks are filtered out.",
    },
    "SE/offentligkod": {
        "label": "Offentligkod", "country": "SE", "flag": "\U0001F1F8\U0001F1EA",
        "site": "https://offentligkod.se/",
        "api": "https://gitlab.com/open-data-knowledge-sharing/katalogen",
        "route": "GNU recutils in git", "claim": "in use by Swedish public bodies",
        "note": "Unusual format - a plain-text recutils database in git - and arguably the "
                "most durable source here for exactly that reason.",
    },
    "FI/avoinkoodi": {
        "label": "Avoinkoodi", "country": "FI", "flag": "\U0001F1EB\U0001F1EE",
        "site": "https://avoinkoodi.fi/",
        "api": "https://avoinkoodi.fi/projects.json",
        "route": "static JSON", "claim": "Finnish public-sector project",
        "note": "Three files: national, municipal and education projects.",
    },
    "CA/code.open.canada.ca": {
        "label": "Open Resource Exchange", "country": "CA", "flag": "\U0001F1E8\U0001F1E6",
        "site": "https://code.open.canada.ca/en/index.html",
        "api": "https://code.open.canada.ca/code.json",
        "route": "code.json", "claim": "published by Canadian administrations",
        "note": "Uses the code.json schema the retired US code.gov defined, nested by "
                "government tier: federal, provincial, municipal and Indigenous. Every "
                "text field is localised {en, fr}, including repositoryURL.",
    },
    "TW/code.gov.tw": {
        "label": "Public Code Platform (moda)", "country": "TW", "flag": "\U0001F1F9\U0001F1FC",
        "site": "https://code.gov.tw/",
        "api": "https://code.gov.tw/api/OpenDataSet/PublicProgramInfoData/json",
        "route": "official open-data export", "claim": "published by Taiwanese agencies",
        "note": "Ministry of Digital Affairs. Use the PUBLISHED dataset export (JSON/XML/CSV), "
                "not the SPA's internal POST API - one GET, repo URLs included, officially "
                "published rather than reverse-engineered. Programme names stay in Chinese "
                "as published; descriptions are translated. No entry deep links: the site "
                "is a SPA whose detail route takes no path parameter and every URL returns "
                "the same shell, so a link cannot be verified.",
    },
    "GLOBAL/dpg": {
        "label": "Digital Public Goods Registry", "country": "GLOBAL", "flag": "\U0001F310",
        "site": "https://www.digitalpublicgoods.net/registry",
        "api": "https://app.digitalpublicgoods.net/api/dpgs",
        "route": "REST API", "claim": "vetted against the DPG Standard",
        "note": "Global and UN-affiliated. WIDER CRITERION than the rest: DPGs are vetted "
                "for relevance to the SDGs and many are NGO- or university-built rather "
                "than government-published, so entries are tagged dpg:true and country "
                "GLOBAL to be filterable. All 249 carry a repository and an OSI licence, "
                "so they join cleanly on repo URL. Deployment countries are used as the "
                "adopter signal.",
    },
    "EU/code.europa.eu": {
        "label": "code.europa.eu", "country": "EU", "flag": "\U0001F1EA\U0001F1FA",
        "site": "https://code.europa.eu/",
        "api": "https://code.europa.eu/api/v4/projects",
        "route": "GitLab API", "claim": "built by EU institutions",
        "note": "1,229 projects but only ~10 carry publiccode.yml - the institutions "
                "promoting the standard barely use it on their own forge.",
    },
}

# ---- verified while surveying globally, NOT ingested. Reason recorded.
SURVEY = [
    {"country": "US", "flag": "\U0001F1FA\U0001F1F8", "name": "code.gov",
     "url": "https://code.gov", "status": "retired",
     "detail": "302s to a Digital.gov policy page; api.code.gov returns the same HTML. "
               "The federal inventory that defined the code.json schema is gone. Its "
               "schema outlived it - Canada still uses it."},
    {"country": "IN", "flag": "\U0001F1EE\U0001F1F3", "name": "OpenForge",
     "url": "https://openforge.gov.in/", "status": "no-code",
     "detail": "Operational as a SERVICE but empty as a catalogue. Tuleap Community "
               "Edition 16.12 (current), CORS-open REST API, 1,502 active public projects "
               "with real names (DigiLocker toolkits, eGov SmartCity, EPrabandhan) - but "
               "ZERO accessible source code. /api/projects/<id>/git returns an empty "
               "repositories array for 40 of 40 sampled projects; frs_packages is empty; "
               "the file-release pages say \"empty\"; and 0 of 25 git plugin pages carry a "
               "clonable URL. Not auth-gated - there is simply nothing published. Adding it "
               "would inject 1,502 entries with no repository URL, which is both the dedupe "
               "identity and the whole promise of the catalogue. Re-check periodically: if "
               "code lands, this becomes the largest single source here."},
    {"country": "KR", "flag": "\U0001F1F0\U0001F1F7", "name": "oss.kr (Open Source Portal)",
     "url": "https://www.oss.kr/", "status": "wrong-shape",
     "detail": "Live and substantial, but it is a national OSS PROMOTION portal, not a "
               "catalogue of government-produced software: developer contests, a "
               "contribution academy, licence verification, Open Up centre, news. Its "
               "/opensource/hub/<id> pages profile UPSTREAM projects (Node.js and the like) "
               "rather than Korean public-sector code, with no adoption data. Closest "
               "analogue here is SILL's recommendation axis, minus the government-use "
               "signal that makes SILL worth having. Nothing to ingest without changing "
               "what the catalogue means."},
    {"country": "BR", "flag": "\U0001F1E7\U0001F1F7", "name": "Portal do Software Publico",
     "url": "https://www.softwarepublico.gov.br/", "status": "broken",
     "detail": "TLS certificate expired; /social/ 404s. Historically the most ambitious "
               "public software portal outside Europe - worth re-checking."},
    {"country": "ES", "flag": "\U0001F1EA\U0001F1F8", "name": "CTT",
     "url": "https://administracionelectronica.gob.es/ctt", "status": "bot-protected",
     "detail": "Centro de Transferencia de Tecnologia holds a real solutions directory, but "
               "every route is behind an F5/BIG-IP bot challenge (TSPD) that returns HTTP 200 "
               "with a CAPTCHA page instead of data - the HTML, the RSS feed and every /api/ "
               "path alike. Solving or bypassing a CAPTCHA is off the table, so this cannot "
               "be harvested as it stands. The legitimate route would be Spain asking to "
               "allowlist a harvester, or publishing the directory via datos.gob.es. "
               "Re-check rather than retry: the block is deliberate."},
    {"country": "global", "flag": "\U0001F310", "name": "State of Public Code / Software Heritage",
     "url": "https://www.softwareheritage.org/2026/07/01/public_code_2026_launch/",
     "status": "different-shape",
     "detail": "288,411 repositories with at least one government-email contribution across "
               "all 193 UN member states. A measurement dataset, not a curated catalogue - "
               "it answers 'who contributes' rather than 'what can we adopt'. Useful as "
               "discovery input for finding catalogues we have missed."},
    {"country": "IE/PT/CY", "flag": "\U0001F1EA\U0001F1FA", "name": "listed by the EU catalogue",
     "url": "https://interoperable-europe.ec.europa.eu/eu-oss-catalogue",
     "status": "unresolved",
     "detail": "Ireland, Portugal and Cyprus appear as EU-catalogue source facets, but no "
               "upstream could be identified - and the EU catalogue's own search is broken, "
               "so it cannot be asked either."},
]


def label(source_key):
    return (SOURCES.get(source_key) or {}).get("label", source_key)


def site(source_key):
    return (SOURCES.get(source_key) or {}).get("site")

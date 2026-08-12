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
        "checkpoint": "it",
        "label": "Developers Italia", "country": "IT", "flag": "\U0001F1EE\U0001F1F9",
        "site": "https://developers.italia.it/en/software",
        "api": "https://api.developers.italia.it/v1/software",
        "route": "REST API", "claim": "built for public administration",
        "note": "The best of the ten: documented REST API, cursor pagination, "
                "publiccode.yml verbatim per entry.",
    },
    "FR/sill": {
        "checkpoint": "fr",
        "label": "SILL", "country": "FR", "flag": "\U0001F1EB\U0001F1F7",
        "site": "https://code.gouv.fr/sill",
        "api": "https://code.gouv.fr/sill/api/sill.json",
        "route": "bulk JSON", "claim": "recommended to public agents",
        "note": "Socle Interministeriel de Logiciels Libres. Use the /sill/api/ export, "
                "NOT /data/sill.json - the latter has no url field at all and carries "
                "Wikidata QIDs nowhere.",
    },
    "FR/awesome-codegouvfr": {
        "checkpoint": "fr",
        "label": "awesome-codegouvfr", "country": "FR", "flag": "\U0001F1EB\U0001F1F7",
        "site": "https://code.gouv.fr/",
        "api": "https://code.gouv.fr/data/awesome-codegouvfr.json",
        "route": "bulk JSON", "claim": "curated French public-sector",
    },
    "DE/openCode": {
        "checkpoint": "de",
        "label": "openCode", "country": "DE", "flag": "\U0001F1E9\U0001F1EA",
        "site": "https://opencode.de/en/software",
        "api": "https://gitlab.opencode.de/api/v4/projects",
        "route": "GitLab API", "claim": "built for public administration",
        "note": "No public API on the site, but its directory slugs embed the GitLab "
                "project id and the listing is generated from publiccode.yml in that "
                "GitLab - so the forge API reproduces the official directory exactly.",
    },
    "DE/opensource.muenchen.de": {
        "checkpoint": "muc",
        "label": "Munich Open Source", "country": "DE", "flag": "\U0001F1E9\U0001F1EA",
        "site": "https://opensource.muenchen.de/software/",
        "api": "https://github.com/it-at-m/opensource.muenchen.de/tree/main/software",
        "route": "markdown files in git", "claim": "built or used by the City of Munich",
        "note": "MUNICIPAL, in scope on the same basis as iMio and Canada's municipal tier - "
                "the criterion is fitness for government use, not tier of government. The site "
                "is VitePress with no JSON API; its catalogue IS a directory of one markdown "
                "file per package, loaded at build time by createContentLoader, so the git repo "
                "is the source. 141 entries split two ways: 56 built in-house (tag "
                "eigenentwicklung, with a code: repo url) and 85 third-party products in "
                "production use - the same built-vs-recommended split as France's "
                "awesome-codegouvfr and SILL.",
    },
    "NL/code.overheid.nl": {
        "checkpoint": "nl",
        "label": "code.overheid.nl", "country": "NL", "flag": "\U0001F1F3\U0001F1F1",
        "site": "https://code.overheid.nl/",
        "api": "https://code.overheid.nl/api/v1/repos/search",
        "route": "Forgejo API", "claim": "published by Dutch government bodies",
        "note": "The government's own self-hosted Forgejo. Open api/v1, no auth - which "
                "makes the separate OSS register's API key unnecessary for coverage.",
    },
    "BE/iMio": {
        "checkpoint": "be",
        "label": "iMio", "country": "BE", "flag": "\U0001F1E7\U0001F1EA",
        "site": "https://www.imio.be/",
        "api": "https://api.github.com/orgs/IMIO/repos",
        "route": "GitHub org", "claim": "built by Walloon municipalities",
        "note": "236 repos but only one publiccode.yml, so the rest are indexed from bare "
                "GitHub metadata and 32 forks are filtered out.",
    },
    "DK/os2": {
        "checkpoint": "os2",
        "label": "OS2 Denmark", "country": "DK", "flag": "\U0001F1E9\U0001F1F0",
        "site": "https://os2.eu/",
        "api": "https://api.github.com/orgs/OS2web/repos",
        "route": "GitHub orgs (20)", "claim": "built by Danish municipalities",
        "note": "Municipal open source association; each product lives in its own GitHub "
                "org, so this is 20 verified orgs. The naming is a minefield - searching "
                "\"OS2\" also returns OS2World (2,446 repos of IBM OS/2 Warp and ArcaOS), "
                "os2edu (a Chinese OS project), OS2G (a US student club), os2sd (Android ROM "
                "trees) and OS23Portfolios (MySQL coursework). Every org was verified against "
                "os2.eu or a Danish location, so harvest.py carries an explicit allowlist "
                "(OS2_ORGS) and records the exclusions (OS2_EXCLUDED). Descriptions are mixed "
                "Danish/English; ~82 Danish strings are NOT yet translated.",
    },
    "BG/governmentbg": {
        "checkpoint": "bg",
        "label": "e-Government Ministry", "country": "BG", "flag": "\U0001F1E7\U0001F1EC",
        "site": "https://github.com/governmentbg",
        "api": "https://api.github.com/orgs/governmentbg/repos",
        "route": "GitHub org", "claim": "built for the Bulgarian government",
        "note": "Bulgaria legally requires custom software written for government to be open "
                "source, and this is where it lands: 186 repos from the Ministry of "
                "e-Government. Found via the OSOR list, which pointed at the agency's "
                "developer portal (dev.egov.bg, a JSF app with no data route) - the GitHub org "
                "is the actual code. Descriptions are Bulgarian; ~158 strings are NOT yet "
                "translated, and many are long EU-funding project titles rather than software "
                "summaries.",
    },
    "SE/offentligkod": {
        "checkpoint": "se",
        "label": "Offentligkod", "country": "SE", "flag": "\U0001F1F8\U0001F1EA",
        "site": "https://offentligkod.se/",
        "api": "https://gitlab.com/open-data-knowledge-sharing/katalogen",
        "route": "GNU recutils in git", "claim": "in use by Swedish public bodies",
        "note": "Unusual format - a plain-text recutils database in git - and arguably the "
                "most durable source here for exactly that reason.",
    },
    "FI/avoinkoodi": {
        "checkpoint": "fi",
        "label": "Avoinkoodi", "country": "FI", "flag": "\U0001F1EB\U0001F1EE",
        "site": "https://avoinkoodi.fi/",
        "api": "https://avoinkoodi.fi/projects.json",
        "route": "static JSON", "claim": "Finnish public-sector project",
        "note": "Three files: national, municipal and education projects.",
    },
    "CA/code.open.canada.ca": {
        "checkpoint": "ca",
        "label": "Open Resource Exchange", "country": "CA", "flag": "\U0001F1E8\U0001F1E6",
        "site": "https://code.open.canada.ca/en/index.html",
        "api": "https://code.open.canada.ca/code.json",
        "route": "code.json", "claim": "published by Canadian administrations",
        "note": "Uses the code.json schema the retired US code.gov defined, nested by "
                "government tier: federal, provincial, municipal and Indigenous. Every "
                "text field is localised {en, fr}, including repositoryURL.",
    },
    "PT/arte": {
        "checkpoint": "pt",
        "label": "ARTE Portugal", "country": "PT", "flag": "\U0001F1F5\U0001F1F9",
        "site": "https://github.com/amagovpt",
        "api": "https://api.github.com/orgs/amagovpt/repos",
        "route": "GitHub org", "claim": "built by Portugal's state technology agency",
        "note": "ARTE - Agencia para a Reforma Tecnologica do Estado (arte.gov.pt), formerly "
                "AMA, hence the amagovpt org name. 88 non-archived repos, actively developed: "
                "the dados.gov.pt open data portal, the Web Accessibility Observatory "
                "ecosystem, Autenticacao.Gov and Citizen Card middleware, ePortugal. Resolved "
                "from the Software Heritage domain registry's github-gov-orgs.csv, and it "
                "also identifies the EU catalogue facet hosting_platform:arte - which had "
                "been misread here as ARTE the Franco-German broadcaster.",
    },
    "IE/ogcio": {
        "checkpoint": "ie",
        "label": "OGCIO Ireland", "country": "IE", "flag": "\U0001F1EE\U0001F1EA",
        "site": "https://github.com/ogcio",
        "api": "https://api.github.com/orgs/ogcio/repos",
        "route": "GitHub org", "claim": "built by the Irish government CIO office",
        "note": "Office of the Government Chief Information Officer (ogcio.gov.ie). Small - "
                "5 non-archived repos - but genuine: govie-ds is the GOV.IE design system, "
                "actively developed, and two repos ship a publiccode.yml. Found via the EU "
                "catalogue's SOURCE FACET NAMES, which are readable in the HTML even though "
                "its search is broken.",
    },
    "TW/code.gov.tw": {
        "checkpoint": "tw",
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
        "checkpoint": "dpg",
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
        "checkpoint": "eu",
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
    {"country": "CY", "flag": "\U0001F1E8\U0001F1FE", "name": "Cyprus - no code platform found",
     "url": "https://www.cyprus.gov.cy/", "status": "none-found",
     "detail": "Checked properly rather than left open. The Software Heritage domain registry "
               "has collected 634 responding Cyprus government domains and NONE is a code "
               "platform or forge; there is no Cyprus entry in its github-gov-orgs.csv; and "
               "its candidate list names only parliament.cy. Keyword matches for git/code/repo "
               "across the subdomain list are false positives (digitalcoalition, "
               "reportdruginfo). Cyprus appears simply not to publish government source code "
               "centrally. EGDI rank 38 of 193, so this is a genuine gap rather than a "
               "discovery failure."},
    {"country": "EU facets", "flag": "\U0001F1EA\U0001F1FA", "name": "remaining EU catalogue facets",
     "url": "https://interoperable-europe.ec.europa.eu/eu-oss-catalogue",
     "status": "unresolved",
     "detail": "Reading the EU catalogue's SOURCE FACET NAMES from the page HTML resolved two "
               "of the three unknowns: hosting_platform:ogcio is Ireland's OGCIO, and "
               "hosting_platform:arte is Portugal's ARTE state technology agency - NOT the "
               "Franco-German broadcaster, which is what it was first read as here. Both are "
               "now ingested. Still unidentified: hosting_platform:city_of_ghent (a Belgian "
               "municipality, likely a handful of repos) and hosting_platform:dmrid_dits "
               "(github.com/DMRID is an individual user with one repo, not a registry)."},
    {"country": "DK/BG", "flag": "\u26A0", "name": "translation debt (OS2 + Bulgaria)",
     "url": "https://govoss-catalog.vercel.app/status.html", "status": "needs-research",
     "detail": "English coverage dropped from 100% to 91% when OS2 Denmark and Bulgaria were "
               "added: 265 strings remain untranslated (171 Bulgarian, 82 Danish, 12 other). "
               "Recorded rather than papered over - every entry still carries description_lang "
               "so a consumer can tell, and meta.json reports the real figure. The Bulgarian "
               "set is mostly long EU-funding project titles rather than software summaries, "
               "so it needs judgement about what is worth translating at all."},
    {"country": "meta", "flag": "\U0001F4D6", "name": "OSOR \"OSS repositories\" list",
     "url": "https://interoperable-europe.ec.europa.eu/collection/open-source-observatory-osor/oss-repositories",
     "status": "discovery-source",
     "detail": "The best discovery resource found so far, and it should have been checked "
               "first: a hand-curated, server-rendered directory of ~29 public-sector OSS "
               "catalogues with owner, language and geographic coverage. Unlike the EU OSS "
               "Catalogue on the same portal, this page renders fine. It confirmed 6 sources "
               "already ingested and surfaced these NOT yet evaluated in depth: OS2 (os2.eu, "
               "Danish municipal community - the Denmark source never found by guessing), "
               "dev.egov.bg (Bulgaria's e-government dev portal), ICT ReUse Belgium, "
               "Helsingborg City (SE municipal), Adullact (FR, runs gitlab.adullact.net), "
               "Forja redIRIS (ES academic) and OW2. publiccode.directory is a dead domain."},
    {"country": "MD", "flag": "\U0001F1F2\U0001F1E9", "name": "OpenCode Moldova",
     "url": "https://opencode.md/en/registry/", "status": "needs-research",
     "detail": "\"Registry of Open Source Solutions\" - a real national portal covering DPGs, "
               "open licences, approved git repositories and requirements for open source "
               "solutions. But it is WordPress with only stock post types (no custom "
               "solutions type in /wp-json/wp/v2/types) and the registry page contains zero "
               "repository links, so what is published looks like policy and guidance rather "
               "than a structured software list. Worth a closer read before writing off - it "
               "would be a new country."},
    {"country": "ES", "flag": "\U0001F1EA\U0001F1F8", "name": "Comptoir du Libre (crosswalk)",
     "url": "https://comptoir-du-libre.org/api/v1/softwares.json", "status": "ready",
     "detail": "Not a national catalogue but a CROSSWALK, and an open one: 780 entries in a "
               "single JSON with url_repository, wikidata, sill, cnll, framalibre and "
               "wikipedia ids on the same row. Would improve dedupe rather than add coverage - "
               "it maps SILL ids to Wikidata QIDs to repo URLs, which is exactly the identity "
               "resolution this catalogue does by hand."},
    {"country": "n/a", "flag": "\u26A0", "name": "UNODC GlobE \"Directory of Open-Source Registries\"",
     "url": "https://globenetwork.unodc.org/globenetwork/en/directory-of-open-source-registries/index.html",
     "status": "false-lead",
     "detail": "NOT about open-source software. GlobE is UNODC's Global Operational Network of "
               "Anti-Corruption Law Enforcement Authorities, and \"open-source registries\" "
               "here means open-source INTELLIGENCE - publicly available official records such "
               "as company and beneficial-ownership registries. Its stated purpose: "
               "\"Information from open-source registries is useful for anti-corruption law "
               "enforcement authorities... collected by investigators and prosecutors without "
               "the need of a formal mutual legal assistance request.\" Recorded because it "
               "surfaced in a software-catalogue search and reads plausibly relevant from the "
               "title alone."},
    {"country": "NL", "flag": "\U0001F1F3\U0001F1F1",
     "name": "Dutch OSS register (api.developer.overheid.nl)",
     "url": "https://api.developer.overheid.nl/oss-register/v1",
     "status": "ready",
     "detail": "A real register, and the one source here that is blocked only by paperwork: "
               "every read returns 401 without an x-api-key, and a key has not been requested. "
               "Not urgent - the Dutch CODE PLATFORM at code.overheid.nl is harvested and needs "
               "no key, and is arguably the better source anyway (first-hand repositories rather "
               "than a register of pointers). Recorded here because it was previously visible "
               "only as a '0 records' warning on the status page; when that page merged into "
               "this one the warning had nowhere to live, and a known gap with no home is a gap "
               "that gets forgotten."},
]


def label(source_key):
    return (SOURCES.get(source_key) or {}).get("label", source_key)


def site(source_key):
    return (SOURCES.get(source_key) or {}).get("site")

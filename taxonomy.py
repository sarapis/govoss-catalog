#!/usr/bin/env python3
"""Collapse 233 inconsistent source category values onto one functional taxonomy.

The sources disagree structurally, not just cosmetically:
  * publiccode.yml ships a controlled kebab-case vocabulary ("data-visualization")
  * SILL ships free-text Title Case ("Web Applications", "Testing & CI/CD")
  * Offentligkod ships Swedish ("kommunikation", "utvecklarverktyg")
  * openCode has free-text creep ("Identity- und Access-Management" vs "IAM" vs "IDM")

So the mapping is explicit, not fuzzy. Anything unmapped is reported rather than
silently bucketed into "other" — an unmapped value is a bug in this file.

Entries with no categories at all get functions inferred from name + description
via multilingual keyword rules; those are marked inferred=True so the guess is
never mistaken for source data.
"""
import json, os, re, collections

OUT = os.path.dirname(os.path.abspath(__file__))

FUNCTIONS = {
    "case-workflow":        "Case & Workflow Management",
    "documents":           "Documents & Records",
    "web-content":         "Content & Web Publishing",
    "collaboration":       "Collaboration & Communication",
    "data-analytics":      "Data, Analytics & Visualisation",
    "geospatial":          "Geospatial & Mapping",
    "identity-security":   "Identity, Access & Security",
    "citizen-services":    "Citizen Services & Participation",
    "finance-procurement": "Finance, Procurement & Accounting",
    "hr-workforce":        "HR & Workforce",
    "crm-service":         "CRM & Service Desk",
    "dev-tools":           "Developer Tools & Platform",
    "infrastructure":      "Infrastructure & Operations",
    "integration":         "Integration, APIs & Data Exchange",
    "learning-knowledge":  "Learning & Knowledge",
    "health-social":       "Health & Social Care",
    "environment-transport": "Environment, Energy & Transport",
    "office":              "Office & Productivity",
    "registers":           "Registers & Reference Data",
}

# ---- explicit map: every source value seen in the data -> function key(s)
M = {
 # workflow / case
 "workflow-management":"case-workflow","business-process-management":"case-workflow",
 "task-management":"case-workflow","project-management":"case-workflow",
 "agile-project-management":"case-workflow","enterprise-project-management":"case-workflow",
 "project-collaboration":"case-workflow","Project Management & Collaboration":"case-workflow",
 "projekthantering":"case-workflow","time-management":"case-workflow",
 "time-tracking":"case-workflow","resource-management":"case-workflow",
 "event-management":"case-workflow","conference-management":"case-workflow",
 "appointment-scheduling":"case-workflow","online-booking":"case-workflow",
 "booking-and-reservation":"case-workflow","calendar-management":"case-workflow",
 "termine":"case-workflow","veranstaltungen":"case-workflow",
 "visitor-management":"case-workflow","test-management":"case-workflow",
 "krav":"case-workflow","erp":"case-workflow","compliance-management":"case-workflow",
 "regulations-and-directives":"case-workflow","policies":"case-workflow",
 "grant-management":"case-workflow","whistleblowing":"case-workflow",
 # documents
 "document-management":"documents","digital-asset-management":"documents",
 "e-signature":"documents","signing":"documents","arkiv":"documents",
 "dokumentation":"documents","whitepaper":"documents",
 "integrated-library-system":"documents","library":"documents",
 # web / content
 "content-management":"web-content","cms":"web-content","website-builder":"web-content",
 "Content Management Systems":"web-content","blog":"web-content",
 "Web Applications":"web-content","web-development":"web-content",
 "Web Frameworks":"web-content","ramverk":"web-content","web-components":"web-content",
 "angular":"web-content","react":"web-content","vue":"web-content",
 "design-system":"web-content","design":"web-content","graphic-design":"web-content",
 "accessibility":"web-content","Portal":"web-content","marketing":"web-content",
 "email-marketing":"web-content","social-media-management":"web-content",
 "e-commerce":"finance-procurement","webbanalys":"data-analytics",
 "Web Browsers & Extensions":"office","Web Servers":"infrastructure",
 # collaboration
 "collaboration":"collaboration","web-collaboration":"collaboration",
 "communications":"collaboration","communication":"collaboration",
 "kommunikation":"collaboration","instant-messaging":"collaboration",
 "video-conferencing":"collaboration","web-conferencing":"collaboration",
 "conferencing":"collaboration","voip":"collaboration","call-center-management":"crm-service",
 "email-management":"collaboration","email":"collaboration",
 "Email Clients & Servers":"collaboration","contact-management":"collaboration",
 "contacts-management":"collaboration","online-community":"collaboration",
 "community":"collaboration","enterprise-social-networking":"collaboration",
 "video-editing":"office","translation":"office","mind-mapping":"collaboration",
 # data
 "data-visualization":"data-analytics","data-visualisation":"data-analytics",
 "visualization":"data-analytics","data-collection":"data-analytics",
 "data-analytics":"data-analytics","analytics":"data-analytics",
 "dataanalys":"data-analytics","dataprocessering":"data-analytics",
 "business-intelligence":"data-analytics","predictive-analysis":"data-analytics",
 "dashboard":"data-analytics","apache-superset":"data-analytics",
 "survey":"data-analytics","feedback":"data-analytics",
 "feedback-and-reviews-management":"data-analytics",
 "artificial-intelligence":"data-analytics","ml":"data-analytics",
 "sprakmodeller":"data-analytics","classification":"data-analytics",
 "outlier detection":"data-analytics","denoising":"data-analytics",
 "spectral analysis":"data-analytics","laboratory software":"data-analytics",
 "scientific-research":"data-analytics","search":"data-analytics",
 "data":"data-analytics","data-quality-tools":"data-analytics",
 "Databases":"infrastructure","databas":"infrastructure","database":"infrastructure",
 # geo
 "geographic-information-systems":"geospatial","geospatial":"geospatial",
 "GeoSpatial":"geospatial","geodata":"geospatial","cad":"geospatial",
 "smart-city":"geospatial","urban-issues":"geospatial",
 # identity / security
 "identity-management":"identity-security","IAM":"identity-security",
 "IDM":"identity-security","Identity- und Access-Management":"identity-security",
 "identitätsdatenabgleich":"identity-security","single-sign-on":"identity-security",
 "Single Sign-On":"identity-security","Authentication":"identity-security",
 "authorization":"identity-security","eID":"identity-security","NFC":"identity-security",
 "it-security":"identity-security","security":"identity-security",
 "Security & Privacy":"identity-security","bsi":"identity-security",
 # citizen services
 "digital-citizenship":"citizen-services","digital citizenship":"citizen-services",
 "citizen-services":"citizen-services","public-services":"citizen-services",
 "public services":"citizen-services","e-service":"citizen-services",
 "egoverment":"citizen-services","gamification":"citizen-services",
 # finance / procurement
 "procurement":"finance-procurement","accounting":"finance-procurement",
 "budgeting":"finance-procurement","financial-reporting":"finance-procurement",
 "billing-and-invoicing":"finance-procurement","payment-gateway":"finance-procurement",
 "mobile-payment":"finance-procurement","taxes-management":"finance-procurement",
 "sales-management":"finance-procurement","inventory-management":"finance-procurement",
 "warehouse-management":"finance-procurement",
 # hr
 "hr":"hr-workforce","employee-management":"hr-workforce",
 "applicant-tracking":"hr-workforce",
 # crm / service desk
 "crm":"crm-service","customer-service-and-support":"crm-service",
 "customer service and support":"crm-service","help-desk":"crm-service",
 "service-desk":"crm-service","it-service-management":"crm-service",
 "remote-support":"crm-service","chatbot":"crm-service",
 # dev tools
 "application-development":"dev-tools","it-development":"dev-tools",
 "software-development":"dev-tools","ide":"dev-tools","IDEs & Text Editors":"dev-tools",
 "Other Development Tools":"dev-tools","utvecklarverktyg":"dev-tools",
 "utvecklingsplattform":"dev-tools","Testing & CI/CD":"dev-tools",
 "devops":"dev-tools","Version Control":"dev-tools","software-quality":"dev-tools",
 "Programming Languages":"dev-tools","cloud-development-environment":"dev-tools",
 "Desktop Applications":"dev-tools","metadata-validation":"dev-tools",
 # infrastructure
 "it-management":"infrastructure","it-infrastructure":"infrastructure",
 "cloud-management":"infrastructure","Virtualization & Containers":"infrastructure",
 "container":"infrastructure","kubernetes":"infrastructure",
 "Operating Systems":"infrastructure","operativsystem":"infrastructure",
 "network":"infrastructure","network-management":"infrastructure",
 "monitoring":"infrastructure","Monitoring & Logging":"infrastructure",
 "Configuration Management":"infrastructure","backup":"infrastructure",
 "it-asset-management":"infrastructure","facility-management":"infrastructure",
 "building-management":"infrastructure","real-estate-management":"infrastructure",
 "property-management":"infrastructure","iot":"infrastructure",
 "software-operator":"infrastructure","plattform-operator":"infrastructure",
 "service-consolidation":"infrastructure",
 # integration
 "integration":"integration","data-integration":"integration",
 "API Management & Networking":"integration","middleware":"integration",
 "datadelning":"integration","data-management":"integration",
 "metadata-management":"integration",
 # learning / knowledge
 "knowledge-management":"learning-knowledge","learning-management-system":"learning-knowledge",
 "e-learning":"learning-knowledge","E-Learning & Education":"learning-knowledge",
 "educational-content":"learning-knowledge","education":"learning-knowledge",
 # health
 "healthcare":"health-social",
 # environment / transport
 "energy":"environment-transport","transport":"environment-transport",
 "fleet-management":"environment-transport",
 # office
 "office":"office","Office & Productivity":"office","productivity-suite":"office",
 # registers
 "organisationen":"registers","registermodernisierung":"registers",
 # explicit non-signal
 "seo":"web-content","api":"integration",
 "Miscellaneous":None,"other":None,"Other":None,"as":None,
}

# multilingual keyword rules for entries with NO source categories
KW = [
 ("geospatial",       r"\b(geo|karte|karta|kartta|carto|map(ping|s)?|gis|spatial|geodat|address|adres)"),
 ("identity-security", r"\b(auth|ident|sso|login|anmeld|sicherheit|säkerhet|security|crypt|signatur|certificat|rgpd|gdpr|dsgvo|anonymis|pseudonym)"),
 ("documents",        r"\b(dokument|document|akte|archiv|arkiv|record|pdf|formular|formul|scan|ocr)"),
 ("web-content",      r"\b(website|webseite|webbplats|sito|site web|cms|portal|redaktion|design system|theme|template)"),
 ("collaboration",    r"\b(chat|messag|mail|forum|conferen|konferenz|möte|riunion|collabor|zusammenarbeit|samarbet|kalender|calend)"),
 ("data-analytics",   r"\b(data|dati|donnée|statistik|statistic|analys|analyt|dashboard|report|rapport|visualis|visualiz|indicat|open ?data|etl|ki\b|ai\b|machine learning)"),
 ("case-workflow",    r"\b(workflow|prozess|process|antrag|demande|pratic|dossier|ticket|aufgab|task|projekt|project|planung|genehmig|verfahren|ärende)"),
 ("citizen-services", r"\b(bürger|citoyen|cittadin|medborgar|kansalais|beteiligung|participat|partecipa|consultation|petition|vote|wahl|élection|elezion)"),
 ("finance-procurement", r"\b(rechnung|factur|fattur|invoice|zahlung|paiement|pagament|payment|budget|haushalt|comptab|buchhalt|steuer|impôt|tribut|beschaffung|marché public|appalt|procurement|ekonomi)"),
 ("hr-workforce",     r"\b(personal|mitarbeit|employé|dipendent|hr\b|recrut|bewerb|lohn|paie|gehalt)"),
 ("crm-service",      r"\b(crm|kunden|client|helpdesk|support|servicedesk|assistenz)"),
 ("dev-tools",        r"\b(library|librairie|libreria|bibliothek|sdk|api client|framework|cli\b|compiler|test|ci/cd|pipeline|lint|boilerplate|starter|template repo|plugin|modul)"),
 ("infrastructure",   r"\b(server|docker|kubernetes|container|deploy|infra|netzwerk|réseau|rete|monitor|backup|cloud|ansible|terraform|betrieb|drift)"),
 ("integration",      r"\b(api|schnittstelle|interface|connect|integrat|middleware|schema|xsd|json-?schema|austausch|échange|scambio)"),
 ("learning-knowledge", r"\b(lern|learn|schul|école|scuola|skola|kurs|course|moodle|wiki|wissen|savoir|conoscen|training)"),
 ("health-social",    r"\b(gesundheit|santé|salut|sanit|hospital|krankenhaus|patient|social|sozial|pflege|care)"),
 ("environment-transport", r"\b(umwelt|environnement|ambient|miljö|klima|climat|energie|energy|energi|verkehr|transport|mobilit|abfall|waste|wasser|water|eau)"),
 ("office",           r"\b(office|bureautique|tabell|spreadsheet|texte|editor|pdf reader|druck|print)"),
 ("registers",        r"\b(register|registre|registro|verzeichnis|katalog|catalog|repertor|annuaire|inventar)"),
]


def normalize(v):
    v = (v or "").strip()
    # one source packs two values into one string: "geographic-information-systems, api"
    return [p.strip() for p in v.split(",") if p.strip()] if "," in v else ([v] if v else [])


def classify(rec):
    fns, unmapped = set(), []
    for raw in (rec.get("categories") or []):
        for v in normalize(raw):
            if v in M:
                if M[v]:
                    fns.add(M[v])
            elif v.lower() in M:
                if M[v.lower()]:
                    fns.add(M[v.lower()])
            else:
                unmapped.append(v)
    if fns:
        return sorted(fns), False, unmapped

    # no usable source category -> infer from text
    # keywords are usually strings but at least one source ships dicts
    kws = [k if isinstance(k, str) else str(k.get("name") or k.get("value") or "")
           for k in (rec.get("keywords") or [])]
    hay = " ".join(filter(None, [
        rec.get("name"), rec.get("short_desc"), rec.get("desc_src"),
        " ".join(kws), rec.get("repo") or ""])).lower()
    for key, pat in KW:
        if re.search(pat, hay):
            return [key], True, unmapped
    return [], True, unmapped


if __name__ == "__main__":
    c = json.load(open(f"{OUT}/catalog.json"))
    unmapped = collections.Counter()
    stats = collections.Counter()
    fcount = collections.Counter()
    for r in c:
        fns, inferred, um = classify(r)
        r["functions"] = fns
        r["functions_inferred"] = inferred and bool(fns)
        unmapped.update(um)
        stats["from_source" if (fns and not inferred) else
              ("inferred" if fns else "unclassified")] += 1
        fcount.update(fns)

    json.dump(c, open(f"{OUT}/catalog.json", "w"), indent=1, default=str)

    print(f"{len(c)} entries classified onto {len(FUNCTIONS)} functions\n")
    for k, n in stats.most_common():
        print(f"   {k:14} {n:>5}  ({100*n/len(c):.0f}%)")
    print("\n== entries per function")
    for k, n in fcount.most_common():
        print(f"   {n:>5}  {FUNCTIONS[k]}")
    if unmapped:
        print(f"\n!! {len(unmapped)} UNMAPPED source values (fix in M):")
        for k, n in unmapped.most_common(30):
            print(f"   {n:>4}  {k!r}")
    else:
        print("\nall source category values mapped")

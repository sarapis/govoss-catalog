#!/usr/bin/env python3
"""Rebuild proprietary.json as the FULL proprietary-software catalogue.

Every product the catalogue names - with alternatives or without - gets a
description and one of the 19 govoss functions, so the merged table can filter
on function and nothing renders as an empty cell.

Descriptions: NYC's own `purpose` string where the product appears in its
licence export (sourced, marked desc_src=nyc), hand-written otherwise
(desc_src=curated). Functions are hand-assigned throughout: deriving them from
the alternatives' categories was tried and is too noisy - it put Bitbucket in
"Case & Workflow Management" because that is where the catalogue files GitLab.

Run by hand, output checked in. run.sh never touches api.databook.nyc.
"""
import csv, json, collections, importlib.util, sys, os

# The NYC licence export is NOT vendored - it is NYC's to publish and the URL is
# the durable reference. Pass the CSV path, or set NYC_LICENCES.
#   curl -s https://api.databook.nyc/oce/licenses/export -o nyc.csv
SP = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NYC_LICENCES", ""))
if not SP or not os.path.exists(SP):
    raise SystemExit(__doc__.strip().splitlines()[0] +
                     "\n\nusage: python3 %s <nyc_licences.csv>\n"
                     "  curl -s https://api.databook.nyc/oce/licenses/export -o nyc.csv"
                     % os.path.basename(__file__))

_s = importlib.util.spec_from_file_location("taxonomy", "taxonomy.py")
T = importlib.util.module_from_spec(_s); _s.loader.exec_module(T)

# name -> (description or None to use NYC's, function key)
M = {
 # ---- content, web, CMS
 "Adobe Experience Manager": ("Enterprise web content management and digital asset management", "web-content"),
 "Sitecore": ("Enterprise web content management and personalisation", "web-content"),
 "Optimizely CMS": ("Enterprise web content management and experimentation", "web-content"),
 "Contentful": ("Headless content management delivered as a hosted service", "web-content"),
 "Squarespace": ("Hosted website builder and publishing platform", "web-content"),
 "Wix": ("Hosted website builder and publishing platform", "web-content"),
 "Notion": ("Team wiki, notes and lightweight project tracking", "web-content"),
 "HackMD": ("Hosted collaborative markdown editing", "web-content"),
 "Google Docs": ("Hosted collaborative document editing", "office"),
 "M-Files": ("Metadata-driven document and content management", "documents"),
 "Higher Logic": ("Online community and member engagement platform", "collaboration"),
 "Brightcove": ("Enterprise video hosting and streaming", "collaboration"),
 "Kaltura": ("Video platform for education and enterprise", "collaboration"),
 "Panopto": ("Lecture capture and video management", "learning-knowledge"),
 "Vimeo": ("Video hosting and streaming", "collaboration"),
 "SmugMug": ("Hosted photo gallery and image sharing", "documents"),
 # ---- office and desktop
 "Microsoft 365": ("Hosted office productivity, email and collaboration suite", "office"),
 "Microsoft Office": (None, "office"),
 "Google Workspace": ("Hosted office productivity, email and collaboration suite", "office"),
 "Microsoft Word": ("Word processing and document authoring", "office"),
 "Microsoft OneNote": ("Freeform note taking and notebooks", "office"),
 "Evernote": ("Note taking and personal knowledge capture", "office"),
 "Grammarly": ("Writing assistance and grammar checking", "office"),
 "Adobe Acrobat Pro": ("PDF authoring, editing and pre-press", "documents"),
 "Adobe Acrobat Reader": ("PDF viewing and annotation", "documents"),
 "PDFsam Enhanced": ("PDF splitting, merging and editing", "documents"),
 "WinRAR": ("File compression and archiving", "office"),
 "WinZip": ("File compression and archiving", "office"),
 "Snagit": ("Screen capture and annotation", "office"),
 "Sublime Text": ("Programmer's text editor", "dev-tools"),
 "UltraEdit": ("Programmer's text editor", "dev-tools"),
 "TextPad": ("Programmer's text editor", "dev-tools"),
 "Visio": ("Diagramming and flowcharting", "office"),
 "Lucidchart": ("Hosted diagramming and flowcharting", "office"),
 "MindManager": ("Mind mapping and visual planning", "office"),
 "XMind": ("Mind mapping and visual planning", "office"),
 "EndNote": ("Reference management and citation", "learning-knowledge"),
 "RefWorks": ("Reference management and citation", "learning-knowledge"),
 # ---- creative
 "Adobe Photoshop": ("Raster image editing and retouching", "office"),
 "Adobe Illustrator": ("Vector illustration and design", "office"),
 "Adobe InDesign": ("Page layout and desktop publishing", "documents"),
 "QuarkXPress": ("Page layout and desktop publishing", "documents"),
 "Adobe XD": ("Interface design and prototyping", "dev-tools"),
 "Figma": (None, "dev-tools"),
 "Corel Painter": ("Digital painting and illustration", "office"),
 "Adobe Premiere Pro": ("Professional video editing", "office"),
 "Adobe Premiere Elements": ("Consumer video editing", "office"),
 "Final Cut Pro": ("Professional video editing", "office"),
 "Camtasia": ("Screen recording and video editing for training", "learning-knowledge"),
 "vMix": ("Live video production and streaming", "collaboration"),
 "Adobe Audition": ("Audio editing and post-production", "office"),
 "Autodesk Maya": ("3D modelling, animation and rendering", "office"),
 "3ds Max": ("3D modelling, animation and rendering", "office"),
 "Cinema 4D": ("3D modelling, animation and rendering", "office"),
 "AutoCAD": (None, "geospatial"),
 "SolidWorks": ("3D mechanical CAD and engineering design", "geospatial"),
 "Fusion 360": ("Cloud CAD, CAM and engineering design", "geospatial"),
 "Adobe FrameMaker": ("Structured technical documentation authoring", "documents"),
 # ---- collaboration and comms
 "Dropbox": ("Cloud file sync and sharing", "collaboration"),
 "Google Drive": ("Cloud file storage, sync and sharing", "collaboration"),
 "Box": (None, "collaboration"),
 "Microsoft OneDrive for Business": ("Cloud file storage and sync for organisations", "collaboration"),
 "SharePoint": ("Intranet, document libraries and team sites", "collaboration"),
 "Slack": (None, "collaboration"),
 "Microsoft Teams": ("Team chat, meetings and calling", "collaboration"),
 "Zoom": (None, "collaboration"),
 "Webex": (None, "collaboration"),
 "GoToMeeting": (None, "collaboration"),
 "Blackboard Collaborate": ("Virtual classroom and web conferencing", "learning-knowledge"),
 "Outlook": ("Desktop email and calendar client", "collaboration"),
 "Microsoft Exchange Server": ("Enterprise mail, calendaring and mailbox hosting", "collaboration"),
 "Airtable": ("Hosted relational spreadsheet and lightweight database", "data-analytics"),
 "Calendly": ("Hosted meeting scheduling", "collaboration"),
 "Doodle": ("Group meeting poll and scheduling", "collaboration"),
 "Twilio": (None, "integration"),
 "Twilio Studio": ("Visual builder for messaging and voice workflows", "integration"),
 "Granicus GovDelivery": (None, "citizen-services"),
 "Everbridge": (None, "citizen-services"),
 "Mailchimp": ("Email marketing and bulk mailing", "web-content"),
 "Brevo": ("Email marketing and transactional messaging", "web-content"),
 "Marketo": ("Marketing automation and campaign management", "web-content"),
 "HubSpot Marketing Hub": (None, "crm-service"),
 "LISTSERV": ("Mailing list management", "collaboration"),
 "Hootsuite": (None, "web-content"),
 "3CX Phone System": ("IP telephony and PBX", "collaboration"),
 "Cisco Unified Communications Manager": ("Enterprise IP telephony and call control", "collaboration"),
 "Avaya Aura": ("Enterprise unified communications platform", "collaboration"),
 "Cisco Jabber": ("Desktop softphone and instant messaging client", "collaboration"),
 "Bria": ("SIP softphone client", "collaboration"),
 # ---- dev tools and platform
 "Bitbucket": ("Git hosting, code review and CI", "dev-tools"),
 "GitHub Enterprise": ("Self-hosted Git, code review and CI", "dev-tools"),
 "GitHub Actions": ("Hosted CI and workflow automation", "dev-tools"),
 "GitLab Premium": ("Commercial tier of GitLab", "dev-tools"),
 "Azure DevOps": ("Repositories, boards, pipelines and artefacts", "dev-tools"),
 "Bamboo": ("Continuous integration and deployment server", "dev-tools"),
 "TeamCity": ("Continuous integration and deployment server", "dev-tools"),
 "CircleCI": ("Hosted continuous integration", "dev-tools"),
 "IntelliJ IDEA Ultimate": ("Commercial Java and polyglot IDE", "dev-tools"),
 "PyCharm Professional": ("Commercial Python IDE", "dev-tools"),
 "Visual Studio Professional": ("Commercial IDE for .NET and C++", "dev-tools"),
 "Posit Workbench": ("Commercial hosted R and Python analysis environment", "dev-tools"),
 "MATLAB": ("Numerical computing and engineering analysis", "data-analytics"),
 "Coverity": ("Static application security testing", "dev-tools"),
 "Checkmarx One": ("Application security testing platform", "dev-tools"),
 "Fortify Static Code Analyzer": ("Static application security testing", "dev-tools"),
 "SonarQube Server (Developer and Enterprise editions)": ("Commercial tiers of SonarQube code quality analysis", "dev-tools"),
 "ALM Quality Center": ("Test and requirements management", "dev-tools"),
 "TestRail": ("Test case management and reporting", "dev-tools"),
 "LoadRunner": (None, "dev-tools"),
 "NeoLoad": ("Load and performance testing", "dev-tools"),
 "BlazeMeter": ("Hosted load and performance testing", "dev-tools"),
 "DBeaver PRO": ("Commercial tier of the DBeaver database client", "dev-tools"),
 "Navicat": ("Database administration and development client", "dev-tools"),
 "Toad": (None, "dev-tools"),
 # ---- infrastructure and ops
 "Datadog": ("Hosted infrastructure and application monitoring", "infrastructure"),
 "New Relic": ("Hosted application performance monitoring", "infrastructure"),
 "PRTG Network Monitor": ("Network and infrastructure monitoring", "infrastructure"),
 "SolarWinds": (None, "infrastructure"),
 "Nagios XI": ("Commercial edition of Nagios monitoring", "infrastructure"),
 "Checkmk Enterprise": ("Commercial edition of Checkmk monitoring", "infrastructure"),
 "Graylog Enterprise": ("Commercial edition of Graylog log management", "infrastructure"),
 "Splunk": (None, "data-analytics"),
 "Pingdom": ("Hosted uptime and performance checks", "infrastructure"),
 "StatusPage": ("Hosted status page and incident communication", "infrastructure"),
 "Docker Desktop": ("Local container development environment", "infrastructure"),
 "Red Hat OpenShift Container Platform": ("Commercial Kubernetes platform with build and deploy tooling", "infrastructure"),
 "VMware Tanzu": ("Commercial Kubernetes platform and application runtime", "infrastructure"),
 "VMware vSphere": ("Server virtualisation and cluster management", "infrastructure"),
 "VMware ESXi": ("Bare-metal hypervisor", "infrastructure"),
 "VMware Cloud Foundation": ("Integrated private-cloud virtualisation stack", "infrastructure"),
 "VMware vSAN": ("Software-defined storage for virtualised clusters", "infrastructure"),
 "VMware Workstation Pro": ("Desktop virtualisation", "infrastructure"),
 "VMware Aria Automation": ("Cloud infrastructure automation and provisioning", "infrastructure"),
 "Hyper-V": ("Server virtualisation on Windows", "infrastructure"),
 "HCP Terraform": ("Hosted Terraform state, runs and policy", "infrastructure"),
 "Red Hat Ansible Automation Platform": ("Commercial Ansible automation with support and control plane", "infrastructure"),
 "Puppet Enterprise": (None, "infrastructure"),
 "Red Hat Satellite": ("Content, patch and lifecycle management for Red Hat estates", "infrastructure"),
 "Microsoft Configuration Manager": ("Endpoint deployment, patching and configuration", "infrastructure"),
 "Acronis Snap Deploy": ("Disk imaging and mass workstation deployment", "infrastructure"),
 "PagerDuty Runbook Automation": ("Operational runbook and job automation", "infrastructure"),
 "Red Hat Enterprise Linux": (None, "infrastructure"),
 "CentOS": ("Community rebuild of Red Hat Enterprise Linux", "infrastructure"),
 "Windows Server": ("Server operating system", "infrastructure"),
 "Windows Server file services": ("Windows file and print sharing role", "infrastructure"),
 "Active Directory Domain Services": ("Directory, authentication and Windows domain management", "identity-security"),
 "Internet Information Services (IIS)": ("Windows web server", "infrastructure"),
 "Oracle iPlanet Web Server": ("Enterprise web server", "infrastructure"),
 "NGINX Plus": (None, "infrastructure"),
 "Varnish Enterprise": ("Commercial edition of the Varnish HTTP cache", "infrastructure"),
 "Akamai": (None, "infrastructure"),
 "Amazon S3": ("Cloud object storage", "infrastructure"),
 "Dell PowerScale (Isilon)": ("Scale-out network-attached storage", "infrastructure"),
 "NetApp ONTAP": ("Enterprise storage operating system", "infrastructure"),
 "Symantec ProxySG": ("Secure web gateway and proxy appliance", "identity-security"),
 "Zscaler Internet Access": ("Cloud secure web gateway", "identity-security"),
 "Commvault": (None, "infrastructure"),
 "Veeam Backup & Replication": ("Backup and recovery for virtual and physical estates", "infrastructure"),
 "Acronis Cyber Protect": ("Backup with integrated endpoint security", "infrastructure"),
 "CrashPlan": ("Hosted endpoint backup", "infrastructure"),
 "GoodSync": ("File synchronisation and backup", "infrastructure"),
 "Beyond Compare": ("File and folder comparison and sync", "office"),
 "Ivanti Neurons": (None, "infrastructure"),
 "Lansweeper": (None, "infrastructure"),
 "Nerdio": ("Azure virtual desktop provisioning and management", "infrastructure"),
 "Citrix Virtual Apps": ("Application and desktop virtualisation", "infrastructure"),
 "AnyDesk": ("Remote desktop access and support", "crm-service"),
 "TeamViewer": (None, "crm-service"),
 "LogMeIn": ("Remote desktop access and support", "crm-service"),
 "GoToMyPC": (None, "crm-service"),
 "SecureCRT": ("SSH and terminal emulation client", "dev-tools"),
 "Xshell": ("SSH and terminal emulation client", "dev-tools"),
 "WS_FTP Professional": ("Secure file transfer client", "infrastructure"),
 "CuteFTP": ("Secure file transfer client", "infrastructure"),
 # ---- data and analytics
 "Tableau": (None, "data-analytics"),
 "Power BI": ("Business intelligence dashboards and reporting", "data-analytics"),
 "Qlik Sense": ("Business intelligence and data discovery", "data-analytics"),
 "Metabase Pro": ("Commercial tier of Metabase analytics", "data-analytics"),
 "Google Analytics": ("Hosted web analytics", "data-analytics"),
 "Adobe Analytics": ("Enterprise web and marketing analytics", "data-analytics"),
 "SAS": (None, "data-analytics"),
 "IBM SPSS Statistics": ("Statistical analysis and modelling", "data-analytics"),
 "Stata": ("Statistical analysis and econometrics", "data-analytics"),
 "Oracle Database": ("Enterprise relational database", "infrastructure"),
 "Microsoft SQL Server": ("Enterprise relational database", "infrastructure"),
 "Microsoft SQL Server Integration Services": ("ETL and data integration for SQL Server", "integration"),
 "Informatica PowerCenter": (None, "integration"),
 "Control-M": ("Enterprise workload and job scheduling", "integration"),
 "Pentaho Enterprise": ("Commercial edition of Pentaho data integration and BI", "integration"),
 "dbt Cloud": ("Hosted analytics transformation and orchestration", "data-analytics"),
 "Confluent Platform": ("Commercial Kafka distribution and stream platform", "integration"),
 "IBM MQ": ("Enterprise message queuing", "integration"),
 "TIBCO Messaging": ("Enterprise messaging and integration", "integration"),
 "MongoDB Atlas": ("Hosted document database", "infrastructure"),
 "MySQL Enterprise": ("Commercial edition of MySQL", "infrastructure"),
 "Redis Enterprise": ("Commercial edition of Redis", "infrastructure"),
 "Elasticsearch": (None, "data-analytics"),
 "Elasticsearch (Elastic Licence tiers)": ("Elastic-licensed tiers of Elasticsearch", "data-analytics"),
 "Elastic Cloud": ("Hosted Elasticsearch and observability", "data-analytics"),
 "Coveo": (None, "data-analytics"),
 "Algolia": ("Hosted search API and indexing", "data-analytics"),
 "Socrata Open Data": (None, "data-analytics"),
 "OpenDataSoft": ("Open data portal and dataset publishing", "data-analytics"),
 "Qualtrics": (None, "data-analytics"),
 "SurveyMonkey": (None, "data-analytics"),
 "SurveyGizmo": (None, "data-analytics"),
 "Alchemer": (None, "data-analytics"),
 "Typeform": ("Online forms and surveys", "data-analytics"),
 "Formstack": ("Online forms and workflow automation", "citizen-services"),
 "Fulcrum": (None, "data-analytics"),
 "Survey123": ("Field survey and form data collection for GIS", "geospatial"),
 # ---- geospatial
 "ArcGIS Pro": ("Desktop GIS analysis and cartography", "geospatial"),
 "ArcGIS Desktop": (None, "geospatial"),
 "ArcGIS Enterprise": ("Server GIS, hosting and geospatial services", "geospatial"),
 "ArcGIS Server": ("Map and geospatial service publishing", "geospatial"),
 "ArcGIS Hub": ("Open data and community engagement portal for GIS", "geospatial"),
 "ArcGIS Field Maps": ("Mobile field data capture for GIS", "geospatial"),
 "Google Maps Platform": ("Hosted mapping, geocoding and routing APIs", "geospatial"),
 "Mapbox GL JS": ("Interactive web mapping library and tile service", "geospatial"),
 "HERE Maps": ("Mapping, geocoding and traffic data services", "geospatial"),
 # ---- identity and security
 "1Password": ("Password management for teams", "identity-security"),
 "LastPass": ("Password management for teams", "identity-security"),
 "Okta": ("Identity, single sign-on and access management", "identity-security"),
 "Auth0": ("Developer identity and authentication platform", "identity-security"),
 "Entra ID": ("Cloud identity, single sign-on and conditional access", "identity-security"),
 "CyberArk": ("Privileged access and secrets management", "identity-security"),
 "BitLocker": ("Full-disk encryption for Windows", "identity-security"),
 "Symantec Endpoint Encryption": ("Full-disk and removable media encryption", "identity-security"),
 "Boxcryptor": ("Client-side encryption for cloud storage", "identity-security"),
 "Symantec Endpoint Protection": ("Endpoint antivirus and threat protection", "identity-security"),
 "Sophos Endpoint Protection": ("Endpoint antivirus and threat protection", "identity-security"),
 "IBM QRadar": ("Security information and event management", "identity-security"),
 "Microsoft Sentinel": ("Cloud security information and event management", "identity-security"),
 "Splunk Enterprise Security": ("Security analytics built on Splunk", "identity-security"),
 "Anomali ThreatStream": ("Threat intelligence aggregation and sharing", "identity-security"),
 "Recorded Future": ("Threat intelligence subscription and analysis", "identity-security"),
 "Aqua Security Platform": ("Container and cloud-native security", "identity-security"),
 "Snyk Container": ("Container image vulnerability scanning", "identity-security"),
 "Qualys Container Security": ("Container vulnerability and compliance scanning", "identity-security"),
 "FortiGate": ("Next-generation firewall and network security", "identity-security"),
 "SonicWall": ("Next-generation firewall and network security", "identity-security"),
 "pfSense Plus": ("Commercial edition of the pfSense firewall", "identity-security"),
 "OPNsense Business Edition": ("Commercial edition of the OPNsense firewall", "identity-security"),
 "DocuSign": (None, "documents"),
 "Adobe Acrobat Sign": ("Electronic signature and approval workflows", "documents"),
 # ---- CRM, service desk, ERP
 "Salesforce": (None, "crm-service"),
 "Salesforce Sales Cloud": ("Sales CRM and pipeline management", "crm-service"),
 "Dynamics 365 Sales": ("Sales CRM and customer engagement", "crm-service"),
 "SugarCRM": ("Customer relationship management", "crm-service"),
 "ServiceNow": ("IT service management and enterprise workflow", "crm-service"),
 "Zendesk": ("Customer support ticketing and help desk", "crm-service"),
 "Freshdesk": ("Customer support ticketing and help desk", "crm-service"),
 "IssueTrak": (None, "crm-service"),
 "Track-It!": (None, "crm-service"),
 "NetSuite": ("Cloud ERP, financials and business management", "finance-procurement"),
 "SAP Business One": ("ERP for small and mid-sized organisations", "finance-procurement"),
 "QuickBooks": ("Accounting and bookkeeping", "finance-procurement"),
 # ---- project and work management
 "Jira": (None, "case-workflow"),
 "Confluence": (None, "learning-knowledge"),
 "Trello": ("Kanban boards and lightweight task tracking", "case-workflow"),
 "Asana": ("Work and project management", "case-workflow"),
 "Monday.com": (None, "case-workflow"),
 "Smartsheet": (None, "case-workflow"),
 "Microsoft Project": (None, "case-workflow"),
 "Tuleap Enterprise": ("Commercial edition of Tuleap ALM", "case-workflow"),
 # ---- learning
 "Blackboard": ("Virtual learning environment and courseware", "learning-knowledge"),
 "Canvas": ("Virtual learning environment and courseware", "learning-knowledge"),
 "LinkedIn Learning": (None, "learning-knowledge"),
 "Pluralsight": (None, "learning-knowledge"),
 "GO1": (None, "learning-knowledge"),
 # ---- citizen services and civic
 "EngagementHQ": ("Online community consultation and civic engagement", "citizen-services"),
 "Neighborland": ("Community engagement and public idea gathering", "citizen-services"),
 "SeeClickFix": ("Citizen issue reporting and municipal work orders", "citizen-services"),
 "Accela Citizen Relationship Management": ("Citizen request tracking and permitting", "citizen-services"),
 "CivicPlus municipal app": ("Municipal resident app and communications", "citizen-services"),
 "Convercent": ("Ethics and compliance case management", "case-workflow"),
 "NAVEX EthicsPoint": ("Whistleblowing hotline and case management", "case-workflow"),
 "Relativity": ("E-discovery and legal document review", "documents"),
 # ---- health
 "Epic": ("Electronic health records for hospitals", "health-social"),
 "Cerner Millennium": ("Electronic health records for hospitals", "health-social"),
 # ---- library
 "Ex Libris Alma": ("Library services platform and resource management", "learning-knowledge"),
 "SirsiDynix Symphony": ("Integrated library management system", "learning-knowledge"),
 "OCLC WorldShare Management Services": ("Hosted library management and cataloguing", "learning-knowledge"),
 # ---- accessibility, misc
 "JAWS": (None, "office"),
 "Dolphin ScreenReader": ("Screen reader for blind and partially sighted users", "office"),
 "Granicus Forms": ("Government online forms and digital services", "citizen-services"),
 "Four Winds Interactive": ("Digital signage content and screen management", "crm-service"),
 "ScreenCloud": ("Digital signage content and screen management", "crm-service"),
 "GeoServer (commercial support tiers)": ("Commercial support tiers for GeoServer", "geospatial"),
 "Seafile Professional": ("Commercial edition of Seafile file sync", "collaboration"),
 "ownCloud Enterprise": ("Commercial edition of ownCloud file sync", "collaboration"),
 "Alfresco Content Services Enterprise": (None, "documents"),
 "OpenText Documentum": (None, "documents"),
 "Oracle Directory Server Enterprise Edition": ("Enterprise LDAP directory server", "identity-security"),
}

# ---- functions for the products with NO alternative (descriptions come from NYC)
G = {
 "18B Case Tracking and Voucher System": "case-workflow",
 "Accellion Kiteworks": "collaboration", "Admins Software": "case-workflow",
 "AgileAssets": "environment-transport", "AlertMedia": "citizen-services",
 "Amazon Web Services": "infrastructure", "Archibus": "environment-transport",
 "AssetWorks": "environment-transport", "AT&T Vehicle Tracking": "environment-transport",
 "Axon": "case-workflow", "Binti": "health-social", "BioVault/AFIS": "identity-security",
 "Broadcom (CA)": "infrastructure", "Care4": "health-social", "Casebuilder": "case-workflow",
 "Caseload Explorer": "case-workflow", "Check Point": "identity-security",
 "Citrix": "infrastructure", "ClaimsVISION": "case-workflow", "CoherentRx": "health-social",
 "Compliance Wage Monitoring": "hr-workforce", "Conduent Public Health Solutions": "health-social",
 "Conduent StrataWare": "case-workflow", "ConvergeOne Call Center Solution": "crm-service",
 "Cyclomedia": "geospatial", "Dataminr": "data-analytics", "Domino Data Lab": "data-analytics",
 "Dun & Bradstreet": "registers", "Dynatrace": "infrastructure",
 "e-Builder": "environment-transport", "Eccovia HMIS": "health-social",
 "eXFORMA / MobiTask": "case-workflow", "Forcepoint": "identity-security",
 "Geotab": "environment-transport", "GlobalLink": "office", "Infor": "finance-procurement",
 "Information Builders (WebFOCUS)": "data-analytics", "Innovee CJ Data Research Platform": "data-analytics",
 "INRIX": "environment-transport", "Integrated Health Resources (BHL)": "health-social",
 "Intellidact AI": "documents", "Intergraph CAD": "citizen-services",
 "Itineris UMAX": "finance-procurement", "Ivalua": "finance-procurement",
 "iWise": "infrastructure", "Keefe Group Commissary Software": "finance-procurement",
 "Kiteworks": "collaboration", "LabVantage LIMS": "health-social",
 "LeadsOnline": "registers", "LegalStratus": "case-workflow", "LexisNexis": "registers",
 "Liferay": "web-content", "LIMS BEAST": "health-social", "LRS": "infrastructure",
 "Meridian Learning Management System": "learning-knowledge", "Mindbreeze": "documents",
 "MRI Software": "environment-transport", "Nerdio": "infrastructure",
 "NICE": "case-workflow", "Office Space Software": "environment-transport",
 "PeerPlace": "health-social", "PowerSchool TIENET": "learning-knowledge",
 "Precisely": "data-analytics", "Rocket Software": "infrastructure",
 "SafeMeasures": "health-social", "Sanborn Maps": "geospatial", "SANSIO EPCR": "health-social",
 "SAP": "finance-procurement", "SoundThinking (ShotSpotter)": "citizen-services",
 "STARLIMS": "health-social", "Streetscape": "registers", "Summer": "hr-workforce",
 "Talkspace": "health-social", "Tyler Technologies Property Tax System": "finance-procurement",
 "Unite Us": "health-social", "Vision CAMA": "finance-procurement", "Westlaw": "registers",
 "Zencity": "citizen-services", "Zimperium": "identity-security",
}

purp = {}
for r in csv.DictReader(open(SP)):
    for k in (r["product"], r["family"]):
        p = (r["purpose"] or "").strip()
        if k and p and len(p) > len(purp.get(k.lower(), "")):
            purp[k.lower()] = p

bp = json.load(open("site/by-product.json"))
al = json.load(open("product_aliases.json"))["aliases"]
rev = collections.defaultdict(list)
for a, vs in al.items():
    for v in vs:
        rev[v].append(a)
old = {p["name"]: p for p in json.load(open("proprietary.json"))["products"]}

out, missing = [], []
for name in sorted(set(bp) | set(old), key=str.lower):
    nyc = purp.get(name.lower()) or next((purp[a] for a in rev.get(name, []) if a in purp), "")
    if name in bp:
        hand, fn = M.get(name, (None, None))
    else:
        hand, fn = None, G.get(name)
    desc = hand or nyc or (old.get(name, {}).get("purpose") or "")
    if not fn or not desc:
        missing.append((name, "fn" if not fn else "", "desc" if not desc else ""))
        continue
    rec = {"name": name, "description": desc,
           "desc_src": "curated" if hand else "nyc",
           "function": fn,
           "kind": old.get(name, {}).get("kind", "software"),
           "seen_in": old.get(name, {}).get("seen_in") or (["us-nyc"] if nyc else [])}
    out.append(rec)

if missing:
    print(f"!! {len(missing)} incomplete:")
    for m in missing[:40]:
        print("   ", m)
    raise SystemExit(1)

bad = [r for r in out if r["function"] not in T.FUNCTIONS]
if bad:
    raise SystemExit("bad function keys: %s" % [(r["name"], r["function"]) for r in bad])

doc = json.load(open("proprietary.json"))
doc["_README"]["purpose"] = (
    "The proprietary software this catalogue names: every product mapped in "
    "replaces.json, plus products governments are known to buy for which there is "
    "NO open source alternative here. Whether a product has one is derived from "
    "by-product.json at build time, never stored, so the two cannot disagree.")
doc["_README"]["fields"] = {
    "description": "what the product does",
    "desc_src": "nyc = NYC's own purpose string from its licence export; "
                "curated = hand-written for this catalogue, unverified",
    "function": "one of the 19 govoss functions. HAND-ASSIGNED. Deriving it from "
                "the alternatives' categories was tried and is too noisy - it filed "
                "Bitbucket under Case & Workflow Management because that is where "
                "the catalogue files GitLab.",
    "kind": "software | data-service",
    "seen_in": "jurisdictions whose procurement data lists it",
}
doc["products"] = out
open("proprietary.json", "w").write(json.dumps(doc, indent=1, ensure_ascii=True))

c = collections.Counter(r["desc_src"] for r in out)
f = collections.Counter(r["function"] for r in out)
print(f"proprietary.json: {len(out)} products  desc {dict(c)}")
print(f"  functions used: {len(f)} of 19  top {dict(f.most_common(5))}")

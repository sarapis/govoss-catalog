#!/usr/bin/env python3
"""Regression test for harvest.detect_lang().

    python3 test_detect_lang.py

This exists because language tagging has broken FOUR times, each time in a way
that reported success:

  1. Tagged per-source, so 72 Finnish and 7 Swedish descriptions were skipped
     while the queue said 100%.
  2. 12 entries declared `description.en` and were German.
  3. All 88 Portuguese strings were labelled English.
  4. 45 English strings were called Danish, because English `for` is also a
     Danish stopword. A single-marker rule was raised to two markers...
  5. ...and English text that repeats the homograph still slipped through:
     "used FOR enabling ... FOR Dexterity content" scored two Danish markers,
     "print A rss feed from A given URL" scored two Portuguese ones.

Every case below is REAL text from the catalogue, not invented. The English
block is the point of the test: those strings must never be classified as a
foreign language just because they contain a word that is also a stopword
somewhere else. The foreign block is equally load-bearing — the first attempt at
fixing #5 over-corrected and started calling Italian, French and Dutch English,
which is the worse failure, since it drops real text out of the translation
queue instead of putting the wrong text in.
"""
import importlib.util
import sys

_s = importlib.util.spec_from_file_location("harvest", "harvest.py")
h = importlib.util.module_from_spec(_s)
_s.loader.exec_module(h)

CASES = [
    # ---- English that previously scored 2+ foreign markers. The regressions.
    ("en", "behavior used for enabling the plone.app.iterate functionality for Dexterity content"),
    ("en", "A cert-manager webhook for creating an ACME DNS01 solver webhook for Gandi DNS"),
    ("en", "Products to print a rss feed from a given URL."),
    ("en", "Plone behavior to get (and set) global E-Guichet/Teleservices configuration into a "
           "Plone Application. Expose E-Guichet procedures in a select field."),
    ("en", "Script to convert emails to PDF from the command-line, as well as detach recognized "
           "attachments."),
    # the original single-marker case, from CLAUDE.md
    ("en", "Admin for OS2Display version 2"),
    # plain English that must stay put
    ("en", "OS2web Drupal feature for importing jobs from Emply to a content type in Drupal"),
    ("en", "A wrapper for Terraform with support for hooks and environments."),

    # ---- Real foreign text. Must still be detected.
    ("it", "App nativa ufficiale per il Bonus Cultura 18app"),
    ("it", "Applicazione web per la gestione collaborativa delle pratiche d'ufficio"),
    ("fr", "Plateforme logicielle libre pour l'automatisation de la configuration et la gestion "
           "des ordinateurs"),
    ("fr", "Outil de gestion des dépendances entre les différents composants d'un projet"),
    ("pt", 'Repositório da API dos serviços de "A Minha Rua"'),
    ("pt", "O plugin Autenticação.Gov permite realizar o procedimento de autenticação com o "
           "Cartão de Cidadão"),
    ("da", "Dette repository er lavet til deling af lokalt udviklede komponenter til OS2mo."),
    # Diacritics are load-bearing, not decoration: transcribing this case as
    # "gor ... Faelleskommunal" while writing the test made it fail, because
    # ø and æ ARE the evidence. Keep these strings byte-exact from the catalogue.
    ("da", "Adgangskomponent gør det muligt at forbinde OIDC-baserede authentifikations-"
           "mekanismer til Fælleskommunal"),
    ("de", "AI Low Code Plattform für digitale Fachverfahren in der öffentlichen Verwaltung"),
    ("nl", "Software voor het optellen van verkiezingsuitslagen en berekenen van de "
           "zetelverdeling."),

    # ---- ä/ö are shared by German, Swedish and Finnish (the sixth recurrence).
    # Counted for German alone, these read as German; dropped from German, the
    # German one read as English. Real strings, DIGG and Avoinkoodi.
    ("fi", "Omaolosta löydät sosiaali- ja terveyspalvelut nopeasti ja esteettömästi, ympäri vuorokauden."),
    ("fi", "Lupapiste on sähköinen palvelu, jossa rakennus-, ympäristö- ja yleisten alueiden käyttölupiin liittyvät asiat"),
    ("sv", "Ett ramverk för att förenkla applikationsutveckling."),
    ("sv", "Granskar kodkvalitet och kodsäkerhetsverktyg."),
    ("de", "Digitale Koordination von Einsatzkräften im Katastrophenfall"),

    # ---- Script detection is decisive and must not be reachable by stopwords.
    ("bg", "Регистър на информационните ресурси"),
    ("zh", "GOV.UK Forms 是英國 GDS 政府數位服務團隊維運之公部門線上表單平台"),

    # ---- No text is not a language. 139 entries with empty descriptions used to
    # ---- carry a per-source tag; asserting a language for "" is what that was.
    (None, ""),
    (None, "   "),
    (None, None),
]

# lang_with_prior(): for SILL (prior "fr") and code.overheid.nl (prior "nl"),
# which used to hardcode their language. detect_lang() cannot replace that tag —
# it called 532 of 672 SILL descriptions English, because a short French phrase
# carries no stopword at all. The prior stays unless the text is PROVABLY English.
# The first block is the direction that must never happen: every string there is
# one detect_lang() calls English.
PRIOR_CASES = [
    ("fr", "fr", "Logiciel d'\u00e9dition de vid\u00e9o"),
    ("fr", "fr", "Compression: Cr\u00e9ation de .zip, .rar, .tar.gz etc."),
    ("fr", "fr", "Serveur Web & Reverse Proxy"),
    ("fr", "fr", "Framework Javascript."),
    ("fr", "fr", "Version libre d'Ansible Tower, pour l'administration d'Ansible."),
    ("fr", "fr", "Service de stockage et de partage de fichiers"),
    ("fr", "fr", "Solution de reporting et de business intelligence, permettant un "
                 "d\u00e9ploiement rapide des r\u00e9sultats de requ\u00eate"),
    ("nl", "nl", "Documentatie voor Abacus"),
    ("nl", "nl", "Openbare beleidsontwikkeling"),
    ("nl", "nl", "Elektronisch kandidaatstellingssysteem"),
    ("nl", "nl", "Test repository voor Logius"),
    ("nl", "nl", "Proof of Concept voor MijnOverheid Zakelijk"),
    ("nl", "nl", "Vergunning Controle Service is een tool om ingediende BIM-modellen "
                 "geautomatiseerd te toetsen op de geldende regels"),
    # ONE English marker, from an expanded acronym or a product's English name.
    # These are what the two-marker threshold exists for.
    ("fr", "fr", "Aussi appel\u00e9 \"PDF Split and Merge\". Outil de fusion, extraction et d\u00e9coupage de fichiers PDF. Il permet aussi de changer le sens des pages."),
    ("fr", "fr", "OptimOffice est une suite bureautique Wysiwym (What You See Is What You Mean) qui permet d'automatiser la publication d'un contenu sous trois formes ( site web, papier, diaporama )  et de faciliter la r\u00e9utilisation de fragments de contenus."),
    # ---- English published under a French/Dutch catalogue. Must come OUT.
    ("en", "fr", "Small utility to launch a different browser depending on the domain "
                 "of the url being launched."),
    ("en", "fr", "JavaScript library that extends HTML via custom attributes to implement "
                 "client-server interactions"),
    ("en", "nl", "Migration from gitlab.com/logius/nldoc to code.overheid.nl/Logius is "
                 "currently paused."),
    ("en", "nl", "Learn more about NLdoc and how to use it within your own organization."),
    ("en", "nl", "Convert Dutch election .EML files to a SQLite database with no loss of data"),
    (None, "nl", ""),
    (None, "fr", None),
]


# lang_assume_en(): for Munich and the DPG registry, which publish in English.
# The mirror of the above. Bare detect_lang() flags the three English strings
# below as foreign on stopword collisions (`os` in "OS X", `la`/`no`), so a
# foreign verdict also needs the text to lack two English markers.
ASSUME_EN_CASES = [
    ("de", "Epitaph erm\u00f6glicht die lokale Positionsbestimmung auf mobilen Ger\u00e4ten. Die Open-Source-Bibliothek verwendet die Programmiersprache Dart und das Flutter-Framework."),
    ("en", "FreeFileSync is a free open source file synchronization program. It is available on Windows, Linux and OS X. ---"),
    ("en", "Scribus is a free desktop publishing program for Linux, Unix, Mac OS X, OS/2 and Windows systems, licensed under the GNU General Public License. ---"),
    ("en", "Powered by LiveKit, La Suite Meet is a video conference software that offers Zoom-level performance with high-quality video and audio. No installation required\u2014simply join calls directly from your browser. "),
    ("en", "Mozilla Firefox is a free web browser installed on all city devices. ---"),
    ("en", "Decidim is a digital platform for citizen participation"),
    ("zh", "GOV.UK Forms \u662f\u82f1\u570b GDS \u653f\u5e9c\u6578\u4f4d\u670d\u52d9"),
    (None, ""),
]


def main():
    failed = []
    for expect, text in CASES:
        got = h.detect_lang(text)
        if got != expect:
            failed.append((expect, got, text))
    for expect, prior, text in PRIOR_CASES:
        got = h.lang_with_prior(text, prior)
        if got != expect:
            failed.append((expect, got, text))
    for expect, text in ASSUME_EN_CASES:
        got = h.lang_assume_en(text)
        if got != expect:
            failed.append((expect, got, text))

    for expect, got, text in failed:
        print(f"FAIL  expected {expect!r}, got {got!r}\n      {(text or '')[:88]!r}")

    # A tie between languages sharing ä/ö is broken by the org's hint, and ".se"
    # is Sweden's code, never Finnish `se`. DIGG passes hint="sv".
    for expect, hint, text in [("sv", "sv", "Källkod för dataportal.se")]:
        got = h.detect_lang(text, hint=hint)
        if got != expect:
            failed.append((expect, got, text))
    n = len(CASES) + len(PRIOR_CASES) + len(ASSUME_EN_CASES) + 1
    print(f"\n{n - len(failed)}/{n} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

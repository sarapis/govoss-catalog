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

    # ---- Script detection is decisive and must not be reachable by stopwords.
    ("bg", "Регистър на информационните ресурси"),
    ("zh", "GOV.UK Forms 是英國 GDS 政府數位服務團隊維運之公部門線上表單平台"),

    # ---- No text is not a language. 139 entries with empty descriptions used to
    # ---- carry a per-source tag; asserting a language for "" is what that was.
    (None, ""),
    (None, "   "),
    (None, None),
]


def main():
    failed = []
    for expect, text in CASES:
        got = h.detect_lang(text)
        if got != expect:
            failed.append((expect, got, text))

    for expect, got, text in failed:
        print(f"FAIL  expected {expect!r}, got {got!r}\n      {(text or '')[:88]!r}")

    print(f"\n{len(CASES) - len(failed)}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

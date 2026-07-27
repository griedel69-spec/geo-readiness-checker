"""
Kurz-Befund-Logik: macht aus den drei Signal-Ergebnissen (geo-radar-Module)
einen einheitlichen Befund für App-Anzeige, PDF und E-Mail.

Reine Funktionen ohne Streamlit/Netz — leicht testbar.
"""
from __future__ import annotations

from signals import compute_overall

AMPEL_FARBEN = {
    "GRÜN": "#27ae60",
    "GELB": "#e67e22",
    "ROT": "#c0392b",
    "UNBEKANNT": "#7f8c8d",
}

AMPEL_SYMBOL = {"GRÜN": "🟢", "GELB": "🟡", "ROT": "🔴", "UNBEKANNT": "⚪"}

SIGNAL_NAMEN = {
    "s1": "KI-Zugang (robots.txt)",
    "s2": "Strukturierte Betriebsdaten (Schema.org)",
    "s3": "Maschinenlesbarkeit der Startseite",
}

GESAMT_KLARTEXT = {
    "GRÜN": "Ihr Betrieb ist für KI-Systeme technisch gut auffindbar. "
            "Jetzt lohnt der Feinschliff bei den Inhalten.",
    "GELB": "Ihr Betrieb ist für KI-Systeme nur eingeschränkt lesbar. "
            "Mit wenigen gezielten Maßnahmen ist deutlich mehr Sichtbarkeit möglich.",
    "ROT": "Mindestens ein Blocker verhindert, dass KI-Systeme Ihren Betrieb "
           "zuverlässig finden und empfehlen können. Hier besteht Handlungsbedarf.",
    "UNBEKANNT": "Die Website war für die automatische Prüfung nicht erreichbar. "
                 "Es ist keine seriöse Aussage möglich — bitte später erneut prüfen.",
}

# Empfehlungs-Bibliothek je Signal und Status (Klartext, ohne Fachjargon).
# Jede Empfehlung ist bewusst als AUFTRAG formuliert, nicht nur als Diagnose:
# ein Satz für die Selbstumsetzung (häufigster Fall: WordPress), ein Satz als
# direkt weitergebbares Briefing an Webentwickler/Agentur — beides ohne
# weitere Rückfrage ausführbar.
_EMPFEHLUNGEN = {
    ("s1", "ROT"): "Öffnen Sie die robots.txt Ihrer Website für die gesperrten KI-Dienste — "
                   "solange z. B. ChatGPT- oder Perplexity-Suchdienste blockiert sind, kann "
                   "Ihr Betrieb dort nicht empfohlen werden. Selbst umsetzbar über den "
                   "Datei-Manager Ihres Hosters (Datei robots.txt im Hauptverzeichnis). "
                   "Auftrag an Webentwickler/Agentur: „In der robots.txt die Disallow-Regeln "
                   "für OAI-SearchBot, ChatGPT-User, PerplexityBot, Google-Extended und "
                   "Bingbot entfernen bzw. durch Allow: / ersetzen.“",
    ("s1", "GELB"): "Prüfen Sie die robots.txt: einzelne KI-Dienste (Trainings-Bots) sind "
                    "gesperrt. Das wirkt langsam, aber dauerhaft auf Ihre Sichtbarkeit. Auftrag "
                    "an Webentwickler/Agentur: „In der robots.txt die Disallow-Regeln für "
                    "GPTBot, ClaudeBot, CCBot und Applebot-Extended entfernen.“",
    ("s1", "UNBEKANNT"): "Die robots.txt Ihrer Website war nicht abrufbar. Auftrag an "
                         "Webentwickler/Agentur: „Bitte robots.txt unter <IhreWebsite>/robots.txt "
                         "prüfen — warum liefert sie keinen Status 200, und ist ein "
                         "Bot-Blocker (z. B. Cloudflare-Bot-Management) aktiv, der auch "
                         "legitime KI-Suchdienste ausschließt?“",
    ("s2", "ROT"): "Lassen Sie eine Schema.org-Auszeichnung (JSON-LD) als Beherbergungsbetrieb "
                   "einbauen — erst damit kann eine KI Ihre Fakten (Name, Adresse, Telefon) "
                   "sicher zuordnen. Bei WordPress erledigt das ein SEO-Plugin wie „Schema & "
                   "Structured Data for WP“ automatisch, wenn Sie den Betriebstyp (Hotel/"
                   "BedAndBreakfast/VacationRental) einstellen. Auftrag an Webentwickler/"
                   "Agentur: „Im <head> der Startseite ein JSON-LD-Datenobjekt vom Typ Hotel/"
                   "BedAndBreakfast/LodgingBusiness mit name, address (PostalAddress), "
                   "telephone, url und image einbetten.“",
    ("s2", "GELB"): "Ihre Schema.org-Daten sind vorhanden, aber unvollständig — fehlende "
                    "Kernfelder ergänzen. Bei WordPress: im selben SEO-Plugin die noch leeren "
                    "Felder (Adresse, Telefon, Bild) nachtragen. Auftrag an Webentwickler/"
                    "Agentur: „Im bestehenden JSON-LD-Datensatz die fehlenden Felder ergänzen "
                    "(siehe Beleg oben) sowie, falls noch nicht vorhanden, FAQPage und sameAs "
                    "(Links zu Google-Profil/Buchungsportalen) einbauen.“",
    ("s2", "UNBEKANNT"): "Die strukturierten Daten Ihrer Seite konnten nicht geprüft werden. "
                         "Auftrag an Webentwickler/Agentur: „Bitte klären, warum die Startseite "
                         "beim automatisierten Abruf nicht ladbar war (Serverfehler, "
                         "SSL-Zertifikat, Bot-Sperre?) und danach erneut auf JSON-LD-Markup "
                         "prüfen.“",
    ("s3", "ROT"): "Ihre Startseite liefert KI-Crawlern praktisch keinen lesbaren Inhalt "
                   "(JavaScript-Baustelle) — die wichtigsten Inhalte müssen bereits im "
                   "ausgelieferten HTML stehen, nicht erst nach dem Laden im Browser. Das ist "
                   "keine reine Text-Änderung mehr, sondern ein technischer Eingriff. Auftrag "
                   "an Webentwickler/Agentur: „Server-Side-Rendering oder statisches "
                   "Pre-Rendering für die Startseite einrichten, sodass Name, Adresse, "
                   "Telefon und Kernangebot bereits im initialen HTML enthalten sind — prüfbar "
                   "über 'Seitenquelltext anzeigen' im Browser.“",
    ("s3", "GELB"): "Stellen Sie sicher, dass Adresse, Telefon und die wichtigsten Inhalte "
                    "direkt im HTML der Startseite stehen — nicht erst nach Klicks oder "
                    "Skripten. Selbst prüfbar: Rechtsklick auf die Startseite → "
                    "„Seitenquelltext anzeigen“ → mit Strg+F nach Ihrer Telefonnummer suchen. "
                    "Auftrag an Webentwickler/Agentur: „Adresse und Telefonnummer als reinen "
                    "Text (nicht als Bild, nicht nur im Kontaktformular) im Footer oder "
                    "Kontaktbereich der Startseite ergänzen.“",
    ("s3", "UNBEKANNT"): "Die Startseite war für die automatische Prüfung nicht erreichbar. "
                         "Auftrag an Webentwickler/Agentur: „Bitte Erreichbarkeit der "
                         "Startseite prüfen (Serverstatus, SSL-Zertifikat) und klären, ob ein "
                         "Bot-/Sicherheitsfilter automatisierte Abrufe blockiert.“",
}

# Wird als eigener Absatz gezeigt, bevor die Empfehlungen aufgelistet werden —
# stellt unmissverständlich klar, wer was liefert.
POSITIONIERUNG_HINWEIS = (
    "Diese Prüfung liefert die Analyse und die konkreten Umsetzungsempfehlungen. Die "
    "technische Umsetzung selbst erfolgt bei Ihnen im Haus oder durch Ihren Webentwickler "
    "bzw. Ihre Agentur — jede Empfehlung unten ist so formuliert, dass Sie sie bei "
    "ausreichender technischer Erfahrung selbst umsetzen oder unverändert als Auftrag "
    "weitergeben können."
)

# Konkrete, nicht quantifizierte Nutzenargumente — keine erfundenen Statistiken,
# nur nachvollziehbare Mechanik (Null-Halluzination-Regel gilt auch hier).
VORTEILE_MEHR_SICHTBARKEIT = [
    "Gäste fragen zunehmend KI-Assistenten statt (nur) Google — wer dort technisch nicht "
    "lesbar ist, wird bei der Antwort schlicht nicht erwähnt, unabhängig von der Qualität "
    "des eigenen Angebots.",
    "Strukturierte Daten wirken nicht nur bei KI-Systemen, sondern verbessern auch die "
    "klassische Google-Darstellung (Rich Results, Sternebewertung, FAQ-Aufklappboxen direkt "
    "im Suchergebnis).",
    "Ohne saubere, maschinenlesbare Fakten füllt eine KI Lücken im Zweifel selbst — mit "
    "sauberen Daten wird der Betrieb korrekt statt geraten dargestellt (falsche Öffnungszeiten "
    "oder Preise in einer KI-Antwort schaden mehr, als gar nicht erwähnt zu werden).",
    "Die Maßnahmen sind überwiegend einmalige technische Einrichtung, keine laufenden Kosten "
    "wie bei bezahlter Werbung — der Effekt bleibt bestehen, solange die Daten aktuell "
    "gehalten werden.",
    "Wer diese Lücken jetzt schließt, wird in einem noch jungen Themenfeld bevorzugt "
    "zitiert, bevor mehr Mitbewerber nachziehen.",
]


# Bausteine, die unabhängig vom Befund immer Teil des GEO-Optimierungspakets
# sind (Content-/Marketing-Ebene, kein technischer Fix).
_IMMER_ENTHALTEN = [
    "H1-Titel + Subheadline", "USP-Box (4 Merkmale)", "20 lokale Keywords",
    "Google-Business-Text", "3 Meta-Descriptions", "Über-uns-Text neu",
]


def _pakete_bausteine(signale) -> list:
    """
    Welche der 8 Bausteine sind für DIESEN Befund tatsächlich relevant.
    Schema-Datensatz/FAQ nur, wenn Signal 2 nicht schon GRÜN ist — bei
    GRÜN sind Kernfelder, FAQPage und sameAs bereits vollständig, ein neuer
    Datensatz/eine neue FAQ wäre nichts als eine Wiederholung des
    Vorhandenen. Reihenfolge wie in der Produktionsstufe: FAQ zuerst,
    dann Schema-Datensatz, dann die Content-Bausteine.
    """
    s2 = next(s for s in signale if s["key"] == "s2")
    bausteine = list(_IMMER_ENTHALTEN)
    if s2["status"] != "GRÜN":
        bausteine.insert(0, "Strukturierter Datensatz (digitaler Steckbrief)")
        # "keine FAQPage" heißt fehlend -> FAQ-Baustein noetig. Vorsicht:
        # ein Treffer nur auf "faqpage" reicht NICHT - der Beleg kann auch
        # "kein sameAs (FAQPage auf /pfad/)" lauten (Glocknerhof-Fix: FAQ
        # existiert bereits auf einer Unterseite), das ist das Gegenteil.
        if "keine faqpage" in s2["grund"].lower():
            bausteine.insert(0, "FAQ mit 10 Fragen")
    return bausteine


def _paket_umfang(overall: str, signale: list) -> str:
    """
    "reduziert" (GRÜN/Fast-GRÜN — GEO-Optimierungspaket zum gleichen Preis,
    aber ohne die technisch nicht nötigen Bausteine) vs. "voll" (echter
    Blocker oder mehrere offene Baustellen gleichzeitig).

    ROT ist IMMER "voll" — ein Blocker ("KI findet den Betrieb gar nicht")
    ist etwas anderes als eine kleine Lücke, unabhängig davon, wie viele
    Signale betroffen sind. UNBEKANNT-Signale zählen als "offen": ohne
    belastbaren Befund darf der Umfang nicht leise reduziert werden.
    """
    if overall == "ROT" or any(s["status"] == "UNBEKANNT" for s in signale):
        return "voll"
    offene_signale = sum(1 for s in signale if s["status"] != "GRÜN")
    if overall == "GRÜN" or (overall == "GELB" and offene_signale <= 1):
        return "reduziert"
    return "voll"


def baue_befund(s1, s2, s3) -> dict:
    """
    Nimmt RobotsResult, SchemaResult, RenderingResult und liefert ein
    einheitliches Befund-Dict für Anzeige, PDF und Mail.
    """
    signale = []
    for key, res in (("s1", s1), ("s2", s2), ("s3", s3)):
        signale.append({
            "key": key,
            "name": SIGNAL_NAMEN[key],
            "status": res.overall_status,
            "grund": res.reason or "",
        })

    overall = compute_overall([s["status"] for s in signale])

    empfehlungen = []
    for s in signale:
        e = _EMPFEHLUNGEN.get((s["key"], s["status"]))
        if e:
            empfehlungen.append(e)

    return {
        "overall": overall,
        "farbe": AMPEL_FARBEN[overall],
        "symbol": AMPEL_SYMBOL[overall],
        "klartext": GESAMT_KLARTEXT[overall],
        "signale": signale,
        "empfehlungen": empfehlungen,
        "positionierung": POSITIONIERUNG_HINWEIS if empfehlungen else "",
        "vorteile": VORTEILE_MEHR_SICHTBARKEIT,
        "verkaufsbruecke": overall in ("GELB", "ROT"),
        "paket_umfang": _paket_umfang(overall, signale),
        "paket_bausteine": _pakete_bausteine(signale),
    }


def signal_kurzzeile(befund: dict) -> str:
    """Kompakte Einzeiler-Darstellung, z. B. für Google Sheets / Mail-Betreff."""
    return " | ".join(f"S{i+1} {s['status']}" for i, s in enumerate(befund["signale"]))

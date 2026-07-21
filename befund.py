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
_EMPFEHLUNGEN = {
    ("s1", "ROT"): "Geben Sie die gesperrten KI-Dienste in Ihrer robots.txt frei — "
                   "solange z. B. ChatGPT- oder Perplexity-Suchdienste blockiert sind, "
                   "kann Ihr Betrieb dort nicht empfohlen werden.",
    ("s1", "GELB"): "Prüfen Sie die robots.txt: einzelne KI-Dienste (Trainings-Bots) "
                    "sind gesperrt. Das wirkt langsam, aber dauerhaft auf Ihre Sichtbarkeit.",
    ("s1", "UNBEKANNT"): "Die robots.txt Ihrer Website war nicht abrufbar — bitte vom "
                         "Webentwickler prüfen lassen, ob ein Bot-Blocker aktiv ist.",
    ("s2", "ROT"): "Lassen Sie eine Schema.org-Auszeichnung als Beherbergungsbetrieb "
                   "(z. B. Hotel, BedAndBreakfast) mit Name, Adresse, Telefon und Website "
                   "einbauen — erst damit kann eine KI Ihre Fakten sicher zuordnen.",
    ("s2", "GELB"): "Ihre Schema.org-Daten sind vorhanden, aber unvollständig — "
                    "fehlende Kernfelder (z. B. Adresse, Telefon, Bild) ergänzen lassen.",
    ("s2", "UNBEKANNT"): "Die strukturierten Daten Ihrer Seite konnten nicht geprüft "
                         "werden — technischen Zustand vom Webentwickler klären lassen.",
    ("s3", "ROT"): "Ihre Startseite liefert KI-Crawlern praktisch keinen lesbaren Inhalt "
                   "(JavaScript-Baustelle). Wichtigste Inhalte müssen ins ausgelieferte HTML.",
    ("s3", "GELB"): "Stellen Sie sicher, dass Adresse, Telefon und die wichtigsten Inhalte "
                    "direkt im HTML der Startseite stehen — nicht erst nach Klicks oder Skripten.",
    ("s3", "UNBEKANNT"): "Die Startseite war für die automatische Prüfung nicht erreichbar — "
                         "Erreichbarkeit und Bot-Freigaben prüfen lassen.",
}


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
        "verkaufsbruecke": overall in ("GELB", "ROT"),
    }


def signal_kurzzeile(befund: dict) -> str:
    """Kompakte Einzeiler-Darstellung, z. B. für Google Sheets / Mail-Betreff."""
    return " | ".join(f"S{i+1} {s['status']}" for i, s in enumerate(befund["signale"]))

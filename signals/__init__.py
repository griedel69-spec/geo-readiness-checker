"""
Gemeinsame GEO-Prüf-Logik — übernommen aus dem geo-radar-Repo.

HERKUNFT (nicht hier weiterentwickeln!):
    Repo:   github.com/griedel69-spec/geo-radar (privat)
    Stand:  Commit 56d2d4d8b1d189d754d76ea19e72553b3a831d1c (14.09.2026)
    Dateien: src/signal1_robots.py, src/signal2_schema.py,
             src/signal3_rendering.py, src/netz_diagnose.py

Die Dateien sind unverändert kopiert (Vendoring), weil geo-radar privat ist
und der Render-Build des Checkers ohne Deploy-Schlüssel nicht auf private
Repos zugreifen kann. Änderungen an der Prüf-Logik gehören ins geo-radar-Repo;
danach die Dateien hierher nachkopieren und den Commit-Stand oben
aktualisieren.

netz_diagnose.py wird seit diesem Stand mitkopiert, weil die drei Signal-
Module es importieren (klartextliche Fehlerdiagnose bei UNBEKANNT). Es hängt
nur an `requests` (im Checker ohnehin vorhanden) und braucht keine weitere
Abhängigkeit.

Ergebnis-relevante Änderungen seit dem vorigen Stand (c6546a3, 21.07.2026):
  - Signal 2 erkennt zusätzlich die Lodging-Typen Campground und Motel
    (ein Campingplatz/Motel mit korrektem Schema-Datensatz bekam vorher
    fälschlich ROT statt GRÜN).
  - Signal 3 normalisiert &nbsp;-Varianten vor der Adress-/Telefon-Erkennung
    (eine mit &nbsp; verbundene PLZ+Ort-Adresse galt vorher fälschlich als
    "Adresse fehlt" → GELB statt GRÜN).
  - Signal 2 kann optional gegen Ausflugsziel-Typen prüfen (betriebstyp=
    "ausflugsziel"); der Checker nutzt das nicht (Default "unterkunft"),
    das Verhalten bleibt für ihn unverändert.

Ampel-Konvention (aus geo-radar CLAUDE.md):
    GRÜN / GELB / ROT / UNBEKANNT — "Null Halluzination: UNBEKANNT statt raten".
    Gesamt-Ampel rollenbasiert (NICHT unmarkiertes Worst-of): ROT nur bei
    einem echten Blocker (Signal 1 oder 3 ROT) oder Kern-Gate-Mangel (4/5);
    Signal 2 löst NIE allein ROT aus. GRÜN ist nur mit grünem Kern-Gate
    (S4 UND S5) erreichbar — der kostenlose 1-3-Check misst die Google-Seite
    nicht und vergibt deshalb nie GRÜN, nur max. GELB; GRÜN bestätigt erst
    der vollständige, kostenpflichtige Check (1-6). Alle UNBEKANNT ->
    UNBEKANNT; sonst GELB. Siehe berechne_gesamtampel/compute_overall unten.
"""
from pathlib import Path
import sys

_HERE = str(Path(__file__).parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from signal1_robots import check_robots, RobotsResult      # noqa: E402,F401
from signal2_schema import check_schema, SchemaResult      # noqa: E402,F401
from signal3_rendering import check_rendering, RenderingResult  # noqa: E402,F401

def _norm_status(wert: str) -> str:
    """Status vereinheitlichen; Unbekanntes/Leeres -> UNBEKANNT, nie GRÜN
    (ein geschönter Befund wäre schlimmer als ein ehrliches UNBEKANNT)."""
    w = (wert or "").strip().upper().replace("GRUEN", "GRÜN")
    return w if w in ("GRÜN", "GELB", "ROT", "UNBEKANNT") else "UNBEKANNT"


def berechne_gesamtampel(status_je_signal: dict) -> str:
    """
    Gesamt-Ampel — rollenbasierte, evidenzbasierte Regel, deckungsgleich mit
    geo-radar (scanner.gesamt_ampel / build_report.berechne_gesamtampel,
    Regel seit 2026-11-09). Erwartet ein Mapping {signalnummer: status}.

    Rollen: Blocker (S1/S3) und Kern-Gate (S4/S5) dürfen ROT auslösen;
    Reputation (S6) ist ampel-weich; Hygiene (S2, strukturierte Daten) ist
    nie deckelnd. **Signal 2 löst NIE allein ROT aus** (Basishygiene, kein
    belegter KI-Sichtbarkeitshebel: Ahrefs, searchVIU, Google "Mythbusting
    generative AI search"; ChatGPT ordnet Unterkünfte zu ~88,8 % über Google
    Places zu, nicht über Website-Markup).

    **GRÜN ist nur erreichbar, wenn das Kern-Gate (S4 Google-Profil-/NAP-
    Konsistenz UND S5 Google-Business-Profil) gemessen und grün ist.** Der
    kostenlose Check erhebt nur die Signale 1-3 (technische Basis) und sieht
    die Google-Seite nicht — er kann deshalb nie GRÜN vergeben, nur maximal
    GELB. GRÜN bestätigt erst der vollständige, kostenpflichtige GEO-Check
    (Signale 1-6). Das ist bewusst so: ein 1-3-Check misst nur ein Drittel
    der für KI-Empfehlungen entscheidenden Signale.

    ROT: Blocker (S1/S3) oder Kern-Gate (S4/S5) ROT. Alle erhobenen
    UNBEKANNT -> UNBEKANNT. Sonst GELB.
    """
    werte = {nr: _norm_status(s) for nr, s in status_je_signal.items() if s}
    if not werte:
        return "UNBEKANNT"
    if all(s == "UNBEKANNT" for s in werte.values()):
        return "UNBEKANNT"
    if any(werte.get(nr) == "ROT" for nr in (1, 3, 4, 5)):
        return "ROT"
    s1, s3, s4, s5 = werte.get(1), werte.get(3), werte.get(4), werte.get(5)
    # GRÜN nur mit grünem Kern-Gate (S4+S5) — im reinen 1-3-Check nicht
    # erhoben, also dort nie GRÜN (max. GELB). S2/S6 gaten nicht.
    if (s4 == "GRÜN" and s5 == "GRÜN"
            and s1 in (None, "GRÜN", "UNBEKANNT")
            and s3 in (None, "GRÜN", "UNBEKANNT")):
        return "GRÜN"
    return "GELB"


def compute_overall(statuses: list) -> str:
    """
    Signal-geordnete Liste [s1, s2, s3, (s4, s5)] -> Gesamt-Ampel.

    WICHTIG: Die Liste ist signal-geordnet (Index 0 = Signal 1). Das Mapping
    Index+1 -> Signalnummer ist zwingend — sonst griffe die "Signal 2 nie
    allein ROT"-Ausnahme am falschen Signal. befund.py übergibt genau
    [s1, s2, s3] in dieser Reihenfolge.
    """
    return berechne_gesamtampel({i + 1: s for i, s in enumerate(statuses) if s})

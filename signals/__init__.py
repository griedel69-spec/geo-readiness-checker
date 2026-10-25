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
    Gesamt-Ampel: ein ROT -> ROT; sonst GELB, wenn GELB oder UNBEKANNT dabei;
    GRÜN nur, wenn alle Signale GRÜN sind (compute_overall in report.py).
"""
from pathlib import Path
import sys

_HERE = str(Path(__file__).parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from signal1_robots import check_robots, RobotsResult      # noqa: E402,F401
from signal2_schema import check_schema, SchemaResult      # noqa: E402,F401
from signal3_rendering import check_rendering, RenderingResult  # noqa: E402,F401

STATUS_ORDER = {"ROT": 0, "GELB": 1, "UNBEKANNT": 2, "GRÜN": 3}


def compute_overall(statuses: list) -> str:
    """Gesamt-Ampel nach geo-radar CLAUDE.md: ein ROT -> ROT; UNBEKANNT ist kein GRÜN."""
    if "ROT" in statuses:
        return "ROT"
    if "GELB" in statuses:
        return "GELB"
    if "UNBEKANNT" in statuses:
        return "GELB"
    return "GRÜN"

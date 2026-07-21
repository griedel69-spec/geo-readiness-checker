"""
Gemeinsame GEO-Prüf-Logik — übernommen aus dem geo-radar-Repo.

HERKUNFT (nicht hier weiterentwickeln!):
    Repo:   github.com/griedel69-spec/geo-radar (privat)
    Stand:  Commit c6546a3839829776ccbfc3b24d384057e4ad1817 (21.07.2026)
    Dateien: src/signal1_robots.py, src/signal2_schema.py, src/signal3_rendering.py

Die Dateien sind unverändert kopiert (Vendoring), weil geo-radar privat ist
und der Render-Build des Checkers ohne Deploy-Schlüssel nicht auf private
Repos zugreifen kann. Änderungen an der Prüf-Logik gehören ins geo-radar-Repo;
danach die drei Dateien hierher nachkopieren und den Commit-Stand oben
aktualisieren.

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

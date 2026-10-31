"""Tests für die Ampel-/Befund-Logik (befund.py + signals/compute_overall)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from itertools import product                              # noqa: E402

from befund import baue_befund, signal_kurzzeile          # noqa: E402
from signals import compute_overall                        # noqa: E402


def _res(status, reason="Testgrund"):
    return SimpleNamespace(overall_status=status, reason=reason)


# ── compute_overall: signalbewusste, evidenzbasierte Regel (deckungsgleich
#    mit geo-radar scanner.gesamt_ampel / build_report.berechne_gesamtampel).
#    Liste ist signal-geordnet: [s1, s2, s3]. ──

def test_overall_echter_blocker_s1_oder_s3_treibt_rot():
    # Signal 1 (KI-Zugang) oder Signal 3 (Maschinenlesbarkeit) ROT = Blocker.
    assert compute_overall(["ROT", "GRÜN", "GRÜN"]) == "ROT"
    assert compute_overall(["GRÜN", "GRÜN", "ROT"]) == "ROT"
    assert compute_overall(["UNBEKANNT", "GELB", "ROT"]) == "ROT"

def test_overall_signal2_treibt_nie_allein_rot():
    # Johannesweg (Mühlviertel): S1 GRÜN, S2 ROT (kein JSON-LD), S3 GRÜN.
    # Früher (Worst-of) fälschlich ROT, korrekt (evidenzbasiert) GELB.
    assert compute_overall(["GRÜN", "ROT", "GRÜN"]) == "GELB"
    # Signal 2 ROT darf in KEINER Kombination allein ROT auslösen:
    for s1, s3 in product(("GRÜN", "GELB", "UNBEKANNT"), repeat=2):
        assert compute_overall([s1, "ROT", s3]) != "ROT"

def test_overall_gelb_bei_gelb():
    assert compute_overall(["GRÜN", "GELB", "GRÜN"]) == "GELB"

def test_overall_unbekannt_ist_kein_gruen():
    assert compute_overall(["GRÜN", "UNBEKANNT", "GRÜN"]) == "GELB"

def test_overall_alle_unbekannt_bleibt_unbekannt():
    assert compute_overall(["UNBEKANNT", "UNBEKANNT", "UNBEKANNT"]) == "UNBEKANNT"

def test_overall_gruen_nur_wenn_alles_gruen():
    assert compute_overall(["GRÜN", "GRÜN", "GRÜN"]) == "GRÜN"


# ── baue_befund ──

def test_befund_gruen_ohne_verkaufsbruecke():
    b = baue_befund(_res("GRÜN"), _res("GRÜN"), _res("GRÜN"))
    assert b["overall"] == "GRÜN"
    assert b["verkaufsbruecke"] is False
    assert b["empfehlungen"] == []
    assert len(b["signale"]) == 3

def test_befund_s2_mangel_ist_gelb_mit_verkaufsbruecke_und_empfehlung():
    # Fehlendes Schema (S2 ROT) ist kein Blocker -> Gesamt GELB, aber die
    # Verkaufsbrücke (GELB/ROT) und die Schema-Empfehlung greifen weiter.
    b = baue_befund(_res("GRÜN"), _res("ROT", "keine Lodging-Entität"), _res("GRÜN"))
    assert b["overall"] == "GELB"
    assert b["verkaufsbruecke"] is True
    assert len(b["empfehlungen"]) == 1
    assert "Schema.org" in b["empfehlungen"][0]

def test_befund_haelt_signal_gruende_fest():
    b = baue_befund(_res("GELB", "Bots blockiert"), _res("GRÜN"), _res("GRÜN"))
    assert b["signale"][0]["grund"] == "Bots blockiert"
    assert b["overall"] == "GELB"

def test_signal_kurzzeile():
    b = baue_befund(_res("GRÜN"), _res("ROT"), _res("GELB"))
    assert signal_kurzzeile(b) == "S1 GRÜN | S2 ROT | S3 GELB"

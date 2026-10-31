"""Tests für die Ampel-/Befund-Logik (befund.py + signals/compute_overall)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from itertools import product                              # noqa: E402

from befund import (                                        # noqa: E402
    baue_befund, signal_kurzzeile, schema_betriebstyp,
    BETRIEBSTYP_OPTIONEN, _NICHT_UNTERKUNFT_TYPEN,
)
from signals import compute_overall                        # noqa: E402


# ── schema_betriebstyp: Formular-Typ -> geo-radar-Prüftyp (Signal 2) ──

def test_schema_betriebstyp_unterkunft_default():
    for t in ("Hotel (3–4 Sterne)", "Pension / Gasthof",
              "Ferienwohnung / Appartement", "Wellnesshotel", ""):
        assert schema_betriebstyp(t) == "unterkunft"

def test_schema_betriebstyp_nicht_unterkunft_wird_ausflugsziel():
    assert schema_betriebstyp("Ausflugsziel / Sehenswürdigkeit") == "ausflugsziel"
    assert schema_betriebstyp("Tourismusverband / DMO") == "ausflugsziel"
    assert schema_betriebstyp("Sonstiges") == "ausflugsziel"

def test_jeder_nicht_unterkunft_typ_ist_eine_echte_formular_option():
    # Schützt vor Label-Drift: jedes gemappte Label muss im Dropdown existieren,
    # sonst griffe die Ausflugsziel-Zuordnung an einem Tippfehler vorbei.
    for label in _NICHT_UNTERKUNFT_TYPEN:
        assert label in BETRIEBSTYP_OPTIONEN

def test_alle_formular_optionen_sauber_gemappt():
    # Jede Option ergibt genau einen der beiden geo-radar-Prüftypen.
    for label in BETRIEBSTYP_OPTIONEN:
        assert schema_betriebstyp(label) in ("unterkunft", "ausflugsziel")


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

def test_s2_rot_empfehlung_ist_typabhaengig():
    # Unterkunft: Vorschlag spricht von Beherbergungsbetrieb (Hotel/B&B).
    b_u = baue_befund(_res("GRÜN"), _res("ROT"), _res("GRÜN"), betriebstyp="unterkunft")
    assert "Beherbergungsbetrieb" in b_u["empfehlungen"][0]
    assert "TouristAttraction" not in b_u["empfehlungen"][0]
    # Ausflugsziel: Vorschlag spricht von Attraktions-/Betriebs-Typen, nicht Hotel.
    b_a = baue_befund(_res("GRÜN"), _res("ROT"), _res("GRÜN"), betriebstyp="ausflugsziel")
    assert "TouristAttraction" in b_a["empfehlungen"][0]
    assert "Beherbergungsbetrieb" not in b_a["empfehlungen"][0]
    # Default bleibt unterkunft (keine Signatur-Überraschung für Altaufrufer).
    b_d = baue_befund(_res("GRÜN"), _res("ROT"), _res("GRÜN"))
    assert "Beherbergungsbetrieb" in b_d["empfehlungen"][0]

def test_befund_haelt_signal_gruende_fest():
    b = baue_befund(_res("GELB", "Bots blockiert"), _res("GRÜN"), _res("GRÜN"))
    assert b["signale"][0]["grund"] == "Bots blockiert"
    assert b["overall"] == "GELB"

def test_signal_kurzzeile():
    b = baue_befund(_res("GRÜN"), _res("ROT"), _res("GELB"))
    assert signal_kurzzeile(b) == "S1 GRÜN | S2 ROT | S3 GELB"

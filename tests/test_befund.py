"""Tests für die Ampel-/Befund-Logik (befund.py + signals/compute_overall)."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from befund import (                                        # noqa: E402
    baue_befund, signal_kurzzeile, _EMPFEHLUNGEN,
    VORTEILE_MEHR_SICHTBARKEIT, POSITIONIERUNG_HINWEIS,
)
from signals import compute_overall                        # noqa: E402


def _res(status, reason="Testgrund"):
    return SimpleNamespace(overall_status=status, reason=reason)


# ── compute_overall: Regel aus geo-radar CLAUDE.md ──

def test_overall_rot_gewinnt_immer():
    assert compute_overall(["GRÜN", "ROT", "GRÜN"]) == "ROT"
    assert compute_overall(["UNBEKANNT", "GELB", "ROT"]) == "ROT"

def test_overall_gelb_bei_gelb():
    assert compute_overall(["GRÜN", "GELB", "GRÜN"]) == "GELB"

def test_overall_unbekannt_ist_kein_gruen():
    assert compute_overall(["GRÜN", "UNBEKANNT", "GRÜN"]) == "GELB"

def test_overall_gruen_nur_wenn_alles_gruen():
    assert compute_overall(["GRÜN", "GRÜN", "GRÜN"]) == "GRÜN"


# ── baue_befund ──

def test_befund_gruen_ohne_verkaufsbruecke():
    b = baue_befund(_res("GRÜN"), _res("GRÜN"), _res("GRÜN"))
    assert b["overall"] == "GRÜN"
    assert b["verkaufsbruecke"] is False
    assert b["empfehlungen"] == []
    assert len(b["signale"]) == 3

def test_befund_rot_mit_verkaufsbruecke_und_empfehlung():
    b = baue_befund(_res("GRÜN"), _res("ROT", "keine Lodging-Entität"), _res("GRÜN"))
    assert b["overall"] == "ROT"
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


# ── Positionierung (Analyse+Empfehlung von uns, Umsetzung beim Betrieb) ──

def test_alle_9_empfehlungen_vorhanden_und_eindeutig():
    """Regressionsschutz: ein doppelter Dict-Key wuerde eine Kombination
    stillschweigend verschlucken (Python-Dict-Literale ueberschreiben sich)."""
    erwartet = {
        (s, status)
        for s in ("s1", "s2", "s3")
        for status in ("ROT", "GELB", "UNBEKANNT")
    }
    assert set(_EMPFEHLUNGEN.keys()) == erwartet
    assert len(_EMPFEHLUNGEN) == 9


def test_jede_empfehlung_nennt_selbst_und_agentur_weg():
    """Jede Empfehlung muss konkret genug sein, um entweder selbst umgesetzt
    oder unveraendert als Auftrag weitergegeben zu werden."""
    for text in _EMPFEHLUNGEN.values():
        assert "Auftrag an Webentwickler" in text or "Webentwickler" in text


def test_befund_traegt_positionierung_nur_wenn_empfehlungen_vorhanden():
    b_mit = baue_befund(_res("GRÜN"), _res("ROT", "keine Lodging-Entität"), _res("GRÜN"))
    assert b_mit["positionierung"] == POSITIONIERUNG_HINWEIS

    b_ohne = baue_befund(_res("GRÜN"), _res("GRÜN"), _res("GRÜN"))
    assert b_ohne["positionierung"] == ""


def test_befund_traegt_vorteile_immer_auch_bei_gruen():
    """Der Nutzen-Hinweis soll auch bei GRÜN gezeigt werden koennen (z. B. als
    Bruecke zu ReviewRadar/weiteren Leistungen), daher unabhaengig vom Befund."""
    b = baue_befund(_res("GRÜN"), _res("GRÜN"), _res("GRÜN"))
    assert b["vorteile"] == VORTEILE_MEHR_SICHTBARKEIT
    assert len(b["vorteile"]) >= 3


# ── Paket-Umfang (GRÜN/Fast-GRÜN: reduzierter Umfang, gleicher Preis) ──

def test_paket_umfang_gruen_ist_reduziert():
    b = baue_befund(_res("GRÜN"), _res("GRÜN"), _res("GRÜN"))
    assert b["paket_umfang"] == "reduziert"
    # Bei durchgehend GRÜN sind weder Schema-Datensatz noch FAQ noetig.
    assert b["paket_bausteine"] == [
        "H1-Titel + Subheadline", "USP-Box (4 Merkmale)", "20 lokale Keywords",
        "Google-Business-Text", "3 Meta-Descriptions", "Über-uns-Text neu",
    ]


def test_paket_umfang_fast_gruen_ist_reduziert_mit_einem_offenen_baustein():
    """GELB, aber nur EIN Signal nicht GRÜN ('Fast-GRÜN') -> reduzierter Umfang,
    Schema-Datensatz bleibt drin (Signal 2 nicht perfekt), FAQ nicht (vorhanden)."""
    b = baue_befund(_res("GRÜN"), _res("GELB", "kein sameAs"), _res("GRÜN"))
    assert b["overall"] == "GELB"
    assert b["paket_umfang"] == "reduziert"
    assert "Strukturierter Datensatz (digitaler Steckbrief)" in b["paket_bausteine"]
    assert "FAQ mit 10 Fragen" not in b["paket_bausteine"]


def test_paket_umfang_gelb_mit_zwei_offenen_signalen_ist_voll():
    b = baue_befund(_res("GRÜN"), _res("GELB", "keine FAQPage"), _res("GELB", "Adresse fehlt"))
    assert b["overall"] == "GELB"
    assert b["paket_umfang"] == "voll"
    assert "FAQ mit 10 Fragen" in b["paket_bausteine"]
    assert "Strukturierter Datensatz (digitaler Steckbrief)" in b["paket_bausteine"]


def test_paket_umfang_rot_ist_immer_voll_auch_mit_nur_einem_offenen_signal():
    """ROT ist ein echter Blocker, unabhaengig davon, wie viele Signale
    betroffen sind - NIE reduzierter Umfang."""
    b = baue_befund(_res("GRÜN"), _res("ROT", "kein JSON-LD"), _res("GRÜN"))
    assert b["overall"] == "ROT"
    assert b["paket_umfang"] == "voll"


def test_paket_umfang_mit_unbekanntem_signal_bleibt_vorsichtshalber_voll():
    """UNBEKANNT zaehlt als 'offen' - ohne belastbaren Befund darf der Umfang
    nicht leise reduziert werden, selbst wenn die anderen zwei GRÜN sind."""
    b = baue_befund(_res("GRÜN"), _res("UNBEKANNT", "HTML nicht ladbar"), _res("GRÜN"))
    assert b["overall"] == "GELB"
    assert b["paket_umfang"] == "voll"

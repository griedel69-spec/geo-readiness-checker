"""Tests für den „2. Messung / Update"-Modus — ohne Netz, ohne echten Versand."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import zweite_messung as zm                     # noqa: E402


def _res(status, reason="Grund"):
    return SimpleNamespace(overall_status=status, reason=reason)


def _checks(s1, s2, s3):
    """Baut injizierbare check_*-Stubs, die feste Signal-Ergebnisse liefern."""
    return (
        lambda dom: _res(s1),
        lambda dom, betriebstyp="unterkunft": _res(s2),
        lambda dom: _res(s3),
    )


def _pdf_stub(lead, befund):
    return b"%PDF-stub"


# ── Parsing ──

def test_parse_gueltige_und_fehlerzeilen():
    text = (
        "Hotel Alpenblick; Maria Alm; https://alpenblick.at; Hotel (3–4 Sterne); info@alpenblick.at\n"
        "\n"
        "# Kommentarzeile wird ignoriert\n"
        "Nur drei; Felder; hier\n"
        "KeineMail; Ort; https://x.at; Hotel; keinemail\n"
        "Pension Tal; ; tal.at; Pension / Gasthof; tal@example.at\n"
    )
    eintraege, fehler = zm.parse_batch_eingabe(text)
    assert len(eintraege) == 2
    assert eintraege[0].betrieb == "Hotel Alpenblick"
    assert eintraege[1].website == "tal.at"          # Ort darf leer sein
    assert len(fehler) == 2                            # zu wenig Felder + ungültige Mail


# ── Einzel-Entscheidung (Faktentreue-Kern) ──

def test_gelb_wird_versendet():
    gesendet = []
    def sender(lead, befund, pdf, secrets=None):
        gesendet.append((lead["email"], befund["overall"], pdf))
        return True, ""
    e = zm.BatchEintrag("Hotel X", "Ort", "https://x.at", "Hotel (3–4 Sterne)", "x@example.at")
    r = zm.pruefe_und_update_eintrag(
        e, secrets=None, _checks=_checks("GRÜN", "ROT", "GRÜN"),   # -> Gesamt GELB
        _pdf=_pdf_stub, _sender=sender,
    )
    assert r.ampel == "GELB"
    assert r.status == "versendet"
    assert gesendet and gesendet[0][0] == "x@example.at"
    assert gesendet[0][2] == b"%PDF-stub"


def test_rot_wird_uebersprungen_kein_versand():
    # Signal 1 ROT = echter Blocker -> Gesamt ROT -> keine „jetzt GELB"-Mail.
    gesendet = []
    e = zm.BatchEintrag("Hotel Y", "Ort", "https://y.at", "Hotel (3–4 Sterne)", "y@example.at")
    r = zm.pruefe_und_update_eintrag(
        e, _checks=_checks("ROT", "ROT", "GRÜN"),
        _pdf=_pdf_stub, _sender=lambda *a, **k: (gesendet.append(1), (True, ""))[1],
    )
    assert r.ampel == "ROT"
    assert r.status == "übersprungen"
    assert gesendet == []                              # NICHTS verschickt


def test_unbekannt_wird_uebersprungen_kein_versand():
    # Der nicht-GELB-Riegel aus pruefe_und_update_eintrag, geprüft am im
    # kostenlosen 1-3-Checker tatsächlich erreichbaren Fall: ist nichts
    # messbar (alle Signale UNBEKANNT), wird NICHT versendet (Faktentreue).
    gesendet = []
    e = zm.BatchEintrag("Hotel Z", "Ort", "https://z.at", "Hotel (3–4 Sterne)", "z@example.at")
    r = zm.pruefe_und_update_eintrag(
        e, _checks=_checks("UNBEKANNT", "UNBEKANNT", "UNBEKANNT"),
        _pdf=_pdf_stub, _sender=lambda *a, **k: (gesendet.append(1), (True, ""))[1],
    )
    assert r.ampel == "UNBEKANNT"
    assert r.status == "übersprungen"
    assert gesendet == []


def test_technisch_sauber_nutzt_gratis_top_mail():
    # Seit der Rollen-Ampel ist das Kern-Gate (S4/S5) im kostenlosen 1-3-
    # Checker ungemessen -> ein reiner 1-3-Lauf erreicht NIE GRÜN, höchstens
    # GELB. Ein technisch sauberer Betrieb (1-3 alle grün) ist damit GELB.
    # Sonderfall: NICHT die Standard-Update-Mail (die fälschlich fehlende
    # strukturierte Daten behaupten würde), sondern die faktentreue
    # "Gratis-Signale top"-Mail wird verschickt.
    standard, top = [], []
    e = zm.BatchEintrag("Hotel Z", "Ort", "https://z.at", "Hotel (3–4 Sterne)", "z@example.at")
    r = zm.pruefe_und_update_eintrag(
        e, _checks=_checks("GRÜN", "GRÜN", "GRÜN"), _pdf=_pdf_stub,
        _sender=lambda *a, **k: (standard.append(1), (True, ""))[1],
        _sender_top=lambda *a, **k: (top.append(1), (True, ""))[1],
    )
    assert r.ampel == "GELB"
    assert r.status == "versendet"
    assert top == [1] and standard == []        # Sondermail, nicht Standard


def test_echte_1_3_luecke_nutzt_standard_mail():
    # Gegenstück: GELB mit echter Lücke auf einem Gratis-Signal (S2 ROT =
    # fehlendes Markup) ist KEIN Sonderfall -> weiterhin die Standard-
    # Update-Mail (ROT→GELB), nicht die Gratis-top-Mail.
    standard, top = [], []
    e = zm.BatchEintrag("Hotel Y", "Ort", "https://y.at", "Hotel (3–4 Sterne)", "y@example.at")
    r = zm.pruefe_und_update_eintrag(
        e, _checks=_checks("GRÜN", "ROT", "GRÜN"), _pdf=_pdf_stub,
        _sender=lambda *a, **k: (standard.append(1), (True, ""))[1],
        _sender_top=lambda *a, **k: (top.append(1), (True, ""))[1],
    )
    assert r.ampel == "GELB"
    assert r.status == "versendet"
    assert standard == [1] and top == []         # Standard, nicht Sondermail


def test_trockenlauf_sendet_nicht():
    gesendet = []
    e = zm.BatchEintrag("Hotel X", "Ort", "https://x.at", "Hotel (3–4 Sterne)", "x@example.at")
    r = zm.pruefe_und_update_eintrag(
        e, nur_pruefen=True, _checks=_checks("GRÜN", "ROT", "GRÜN"),
        _pdf=_pdf_stub, _sender=lambda *a, **k: (gesendet.append(1), (True, ""))[1],
    )
    assert r.status == "bereit"
    assert gesendet == []


def test_versandfehler_wird_einmal_wiederholt_dann_gemeldet():
    versuche = {"n": 0}
    def flaky(lead, befund, pdf, secrets=None):
        versuche["n"] += 1
        return False, "SMTP-Timeout"
    e = zm.BatchEintrag("Hotel X", "Ort", "https://x.at", "Hotel (3–4 Sterne)", "x@example.at")
    r = zm.pruefe_und_update_eintrag(
        e, _checks=_checks("GRÜN", "ROT", "GRÜN"),
        _pdf=_pdf_stub, _sender=flaky, retry=1, sleep_fn=lambda s: None,
    )
    assert r.status == "fehler"
    assert versuche["n"] == 2                           # ein Erstversuch + ein Retry
    assert "SMTP-Timeout" in r.detail


# ── Batch-Orchestrierung ──

def test_batch_fehler_bricht_nicht_ab_und_zaehlt_richtig():
    text = (
        "A; O; https://a.at; Hotel (3–4 Sterne); a@example.at\n"   # GELB -> versendet
        "B; O; https://b.at; Hotel (3–4 Sterne); b@example.at\n"   # ROT  -> übersprungen
        "nur; zwei felder\n"                                       # Parse-Fehler
    )
    # A -> GELB, B -> ROT: über die URL steuern wir das Ergebnis.
    def checks_fuer(dom_s1s2s3):
        pass
    def cr(dom): return _res("ROT" if "b.at" in dom else "GRÜN")
    def cs(dom, betriebstyp="unterkunft"): return _res("ROT")
    def crend(dom): return _res("GRÜN")

    erg = zm.verarbeite_batch(
        text, secrets=None, pause_sek=0, sleep_fn=lambda s: None,
        _checks=(cr, cs, crend), _pdf=_pdf_stub,
        _sender=lambda *a, **k: (True, ""),
    )
    assert len(erg.versendet) == 1 and erg.versendet[0].eintrag.betrieb == "A"
    assert len(erg.uebersprungen) == 1 and erg.uebersprungen[0].eintrag.betrieb == "B"
    assert len(erg.parse_fehler) == 1

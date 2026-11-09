"""
„2. Messung / Update"-Modus: Betriebe, die VOR dem Ampel-Fix einen ROT-
Kurzbefund erhalten haben, bekommen eine Update-Mail mit dem jetzt
korrigierten (GELB-)Ergebnis.

Streamlit-frei gehalten (wie befund.py / mailer.py / sheets.py), damit die
Batch-Logik ohne UI testbar ist. Der Admin-Bereich in geo_checker_app.py
ruft hier nur hinein und kümmert sich um Anzeige + Sheet-Logging.

WICHTIG (Faktentreue): Der Update-Text behauptet „steht jetzt auf GELB".
Deshalb wird pro Eintrag LIVE neu gemessen und nur dann versendet, wenn die
Neumessung tatsächlich GELB ergibt. Ergibt sie etwas anderes (ROT/GRÜN/
UNBEKANNT), wird der Eintrag ÜBERSPRUNGEN und im Ergebnis gemeldet — nie eine
unzutreffende „jetzt GELB"-Mail verschickt.

Der tatsächliche Versand wird ausschließlich über den Admin-Bereich
ausgelöst; dieses Modul wird nie vom öffentlichen Erstcheck-Flow benutzt.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

from signals import check_robots, check_schema, check_rendering
from befund import baue_befund, signal_kurzzeile, schema_betriebstyp
from befund_pdf import erzeuge_kurzbefund_pdf
from mailer import sende_update_zweite_messung


def _domain(url: str) -> str:
    """Hostname aus einer URL/Eingabe ziehen (wie im Hauptformular)."""
    u = (url or "").strip()
    if not u:
        return ""
    if not u.startswith("http"):
        u = "https://" + u
    return urlparse(u).netloc or u


@dataclass
class BatchEintrag:
    betrieb: str
    ort: str
    website: str
    typ: str
    email: str


def parse_batch_eingabe(text: str) -> tuple[list[BatchEintrag], list[str]]:
    """
    Eine Zeile je Betrieb, Felder per Semikolon getrennt:

        Name; Ort; URL; Betriebstyp; E-Mail

    Semikolon statt Komma, weil Betriebsnamen oft Kommas enthalten. Leere
    Zeilen und Zeilen, die mit '#' beginnen, werden übersprungen.

    Rückgabe: (gültige Einträge, Fehlermeldungen je verworfener Zeile).
    """
    eintraege: list[BatchEintrag] = []
    fehler: list[str] = []
    for i, roh in enumerate(text.splitlines(), 1):
        zeile = roh.strip()
        if not zeile or zeile.startswith("#"):
            continue
        teile = [t.strip() for t in zeile.split(";")]
        if len(teile) < 5:
            fehler.append(
                f"Zeile {i}: erwarte 5 Felder (Name; Ort; URL; Typ; E-Mail), "
                f"{len(teile)} gefunden — übersprungen: {zeile[:80]}"
            )
            continue
        betrieb, ort, website, typ, email = teile[0], teile[1], teile[2], teile[3], teile[4]
        if not betrieb or not website or "@" not in email:
            fehler.append(
                f"Zeile {i}: Name, URL oder gültige E-Mail fehlt — "
                f"übersprungen: {zeile[:80]}"
            )
            continue
        eintraege.append(BatchEintrag(betrieb, ort, website, typ, email))
    return eintraege, fehler


@dataclass
class EintragErgebnis:
    eintrag: BatchEintrag
    ampel: str = ""
    signale: str = ""
    status: str = ""       # "versendet" | "bereit" | "übersprungen" | "fehler"
    detail: str = ""
    pdf_bytes: bytes | None = None


# Status-Vermerk fürs Lead-Register (macht 2. Messung von Erstkontakt unterscheidbar).
VERSAND_OK = "update versendet (2. Messung)"
VERSAND_FEHLER = "2. Messung FEHLER"


def pruefe_und_update_eintrag(
    e: BatchEintrag, secrets=None, *,
    nur_pruefen: bool = False,
    retry: int = 1,
    sleep_fn=time.sleep,
    _checks=None,
    _pdf=erzeuge_kurzbefund_pdf,
    _sender=sende_update_zweite_messung,
) -> EintragErgebnis:
    """
    Ein Betrieb: live neu messen -> bei GELB Update-Mail (bzw. im Trockenlauf
    nur vorbereiten). Alles andere wird übersprungen (Faktentreue).

    Die check_*/PDF-/Sende-Funktionen sind injizierbar, damit Tests ohne Netz
    und ohne echten Versand laufen können. retry=1 => ein Wiederholungsversuch
    bei Versandfehler (die Register-Historie zeigt vereinzelte SMTP-Timeouts).
    """
    cr, cs, crend = (_checks if _checks else (check_robots, check_schema, check_rendering))
    dom = _domain(e.website)
    bt = schema_betriebstyp(e.typ)

    try:
        s1 = cr(dom)
        s2 = cs(dom, betriebstyp=bt)
        s3 = crend(dom)
        befund = baue_befund(s1, s2, s3, betriebstyp=bt)
    except Exception as exc:
        return EintragErgebnis(e, status="fehler",
                               detail=f"Messung fehlgeschlagen: {type(exc).__name__}: {exc}")

    erg = EintragErgebnis(e, ampel=befund["overall"], signale=signal_kurzzeile(befund))

    if befund["overall"] != "GELB":
        erg.status = "übersprungen"
        erg.detail = (f"Neumessung ergibt {befund['overall']}, nicht GELB — "
                      f"die 2.-Messung-Mail (ROT→GELB) würde nicht zutreffen.")
        return erg

    lead = {"betrieb": e.betrieb, "ort": e.ort, "email": e.email,
            "website": e.website, "typ": e.typ}
    try:
        erg.pdf_bytes = _pdf(lead, befund)
    except Exception as exc:
        erg.status = "fehler"
        erg.detail = f"PDF-Erzeugung fehlgeschlagen: {type(exc).__name__}: {exc}"
        return erg

    if nur_pruefen:
        erg.status = "bereit"
        erg.detail = "GELB — würde Update-Mail senden (Trockenlauf, nichts verschickt)."
        return erg

    letzter = ""
    for versuch in range(retry + 1):
        ok, info = _sender(lead, befund, erg.pdf_bytes, secrets=secrets)
        if ok:
            erg.status = "versendet"
            erg.detail = info or ""
            return erg
        letzter = info
        if versuch < retry:
            sleep_fn(2.0)
    erg.status = "fehler"
    erg.detail = letzter
    return erg


@dataclass
class BatchErgebnis:
    ergebnisse: list[EintragErgebnis]
    parse_fehler: list[str]

    @property
    def versendet(self): return [r for r in self.ergebnisse if r.status == "versendet"]
    @property
    def bereit(self): return [r for r in self.ergebnisse if r.status == "bereit"]
    @property
    def uebersprungen(self): return [r for r in self.ergebnisse if r.status == "übersprungen"]
    @property
    def fehler(self): return [r for r in self.ergebnisse if r.status == "fehler"]


def verarbeite_batch(
    text: str, secrets=None, *,
    nur_pruefen: bool = False,
    pause_sek: float = 1.0,
    sleep_fn=time.sleep,
    fortschritt=None,
    **einzel_kwargs,
) -> BatchErgebnis:
    """
    Ganze Batch-Eingabe verarbeiten. `fortschritt(i, n, eintrag)` wird vor
    jedem Eintrag aufgerufen (für eine UI-Fortschrittsanzeige). Zwischen
    echten Versänden wird `pause_sek` gewartet (schonend für den Mailserver).
    Ein Fehler bei einem Eintrag bricht den Batch NICHT ab.
    """
    eintraege, parse_fehler = parse_batch_eingabe(text)
    ergebnisse: list[EintragErgebnis] = []
    n = len(eintraege)
    for i, e in enumerate(eintraege, 1):
        if fortschritt:
            fortschritt(i, n, e)
        r = pruefe_und_update_eintrag(e, secrets, nur_pruefen=nur_pruefen,
                                      sleep_fn=sleep_fn, **einzel_kwargs)
        ergebnisse.append(r)
        if not nur_pruefen and r.status == "versendet" and i < n and pause_sek:
            sleep_fn(pause_sek)
    return BatchErgebnis(ergebnisse=ergebnisse, parse_fehler=parse_fehler)

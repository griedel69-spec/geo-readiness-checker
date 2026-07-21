"""Smoke-Tests für das Kurz-Befund-PDF."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from befund import baue_befund              # noqa: E402
from befund_pdf import erzeuge_kurzbefund_pdf  # noqa: E402

LEAD = {
    "betrieb": "Hotel Teststern",
    "ort": "Kitzbühel",
    "email": "test@example.com",
    "website": "https://www.hotel-teststern.at",
    "typ": "Hotel (3–4 Sterne)",
}


def _res(status, reason="Testgrund"):
    return SimpleNamespace(overall_status=status, reason=reason)


def test_pdf_rot_mit_verkaufsbruecke():
    befund = baue_befund(_res("ROT", "Klasse-A-Bot blockiert"),
                         _res("ROT", "keine Lodging-Entität"),
                         _res("GELB", "Telefon fehlt im rohen HTML"))
    pdf = erzeuge_kurzbefund_pdf(LEAD, befund)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 2000

def test_pdf_gruen_ohne_verkaufsbruecke():
    befund = baue_befund(_res("GRÜN"), _res("GRÜN"), _res("GRÜN"))
    pdf = erzeuge_kurzbefund_pdf(LEAD, befund)
    assert pdf.startswith(b"%PDF")

def test_pdf_unbekannt():
    befund = baue_befund(_res("UNBEKANNT", "robots.txt nicht ladbar"),
                         _res("UNBEKANNT", "HTML nicht ladbar"),
                         _res("UNBEKANNT", "HTML nicht ladbar"))
    pdf = erzeuge_kurzbefund_pdf(LEAD, befund)
    assert pdf.startswith(b"%PDF")

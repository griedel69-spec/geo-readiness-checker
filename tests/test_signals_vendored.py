"""
Regressionstest für die übernommenen Signal-Module: Der Befund, der den
Umbau ausgelöst hat (haus-steger.at, generische WordPress-Schema-Typen),
muss von Signal 2 dauerhaft als ROT erkannt werden — nie wieder als bestanden.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "signals"))

from signal2_schema import evaluate_html     # noqa: E402

WORDPRESS_GENERIC = """<!DOCTYPE html><html lang="de"><head><title>Haus Test</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"WebPage","url":"https://example.at/","name":"Haus Test",
  "potentialAction":[{"@type":"ReadAction","target":["https://example.at/"]}]},
 {"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Home"}]},
 {"@type":"WebSite","url":"https://example.at/","name":"Haus Test"}
]}
</script></head><body>Startseite</body></html>"""

LODGING_OK = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Hotel","name":"Hotel Teststern",
 "address":{"@type":"PostalAddress","streetAddress":"Hauptstr. 1","addressLocality":"Kitzbühel"},
 "telephone":"+43 5356 12345","url":"https://example.at","image":"https://example.at/bild.jpg",
 "geo":{"@type":"GeoCoordinates","latitude":47.4,"longitude":12.4}}
</script></head><body>x</body></html>"""


def test_generische_wordpress_typen_sind_rot():
    res = evaluate_html(WORDPRESS_GENERIC, http_status=200, domain="example.at")
    assert res.overall_status == "ROT"
    assert "keine Lodging-Entität" in res.reason
    assert "WebPage" in res.all_types

def test_echte_lodging_entitaet_ist_nicht_rot():
    res = evaluate_html(LODGING_OK, http_status=200, domain="example.at")
    assert res.overall_status in ("GRÜN", "GELB")
    assert res.lodging is not None

def test_nicht_abrufbar_ist_unbekannt():
    res = evaluate_html("", http_status=503, domain="example.at")
    assert res.overall_status == "UNBEKANNT"


# ---------------------------------------------------------------------------
# Glocknerhof-Regression (uebernommen aus geo-radar PR #40): FAQPage-Markup
# gehoert auf die FAQ-Unterseite — Signal 2 darf "keine FAQPage" nicht mehr
# behaupten, wenn eine korrekt ausgezeichnete Unterseite existiert.
# ---------------------------------------------------------------------------

import signal2_schema  # noqa: E402
from signal2_schema import check_schema  # noqa: E402

_STARTSEITE_MIT_FAQ_LINK = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Hotel","name":"Hotel Glocknerhof",
 "address":{"@type":"PostalAddress","streetAddress":"Berg 55","addressLocality":"Berg im Drautal"},
 "telephone":"+43 4712 555","url":"https://glocknerhof.at","image":"https://glocknerhof.at/bild.jpg",
 "geo":{"@type":"GeoCoordinates","latitude":46.7,"longitude":13.1}}
</script></head><body>
<a href="/zimmer-preise/wissenswertes-faq/">Wissenswertes &amp; FAQ</a>
</body></html>"""

_FAQ_UNTERSEITE = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
 {"@type":"Question","name":"Muss ich eine Anzahlung leisten?",
  "acceptedAnswer":{"@type":"Answer","text":"Ja."}}]}
</script></head><body>FAQ</body></html>"""


def test_evaluate_html_faqpage_extern_wird_uebernommen():
    res = signal2_schema.evaluate_html(
        _STARTSEITE_MIT_FAQ_LINK, 200, domain="glocknerhof.at",
        faqpage_extern="/zimmer-preise/wissenswertes-faq/")
    assert res.has_faqpage is True
    assert "keine FAQPage" not in res.reason
    assert "FAQPage auf /zimmer-preise/wissenswertes-faq/" in res.reason


def test_check_schema_glocknerhof_regression(monkeypatch):
    class _Resp:
        def __init__(self, url, text, status=200):
            self.url, self.text, self.status_code = url, text, status

    def fake_fetch_html(domain, user_agent=None, timeout=None, **_kw):
        return ("https://www.glocknerhof.at/", _STARTSEITE_MIT_FAQ_LINK, 200)

    def fake_get(url, **_kw):
        if "wissenswertes-faq" in url:
            return _Resp(url, _FAQ_UNTERSEITE)
        return _Resp(url, "<html></html>", 404)

    monkeypatch.setattr(signal2_schema, "_fetch_html", fake_fetch_html)
    monkeypatch.setattr(signal2_schema.requests, "get", fake_get)

    res = check_schema("glocknerhof.at")
    assert res.has_faqpage is True
    assert res.faqpage_quelle == "/zimmer-preise/wissenswertes-faq/"
    assert "keine FAQPage" not in res.reason

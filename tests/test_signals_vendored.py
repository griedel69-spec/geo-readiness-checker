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
        # 4. Rückgabewert = Netz-Diagnose-String (leer bei Erfolg), seit
        # Vendoring-Stand 56d2d4d Teil der _fetch_html-Signatur.
        return ("https://www.glocknerhof.at/", _STARTSEITE_MIT_FAQ_LINK, 200, "")

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


# ---------------------------------------------------------------------------
# Schindler-Regression: sichtbare FAQ-Seite OHNE FAQPage-Markup darf nicht
# mehr als "keine FAQPage" / fehlende FAQ gemeldet werden. Der Betrieb
# (hotel-schindler.at) hatte eine umfangreiche /faq (29 Fragen), aber kein
# FAQPage-JSON-LD — der Befund "keine FAQPage" war technisch korrekt, für den
# Betrieb aber peinlich (es wirkt, als fehle die FAQ, die sichtbar dasteht).
# ---------------------------------------------------------------------------

# Hotel-Startseite mit vollständiger Lodging-Entität -> GELB (kein FAQPage,
# kein sameAs). Verlinkt auf /faq.
_SCHINDLER_STARTSEITE = """<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Hotel","name":"Hotel Schindler",
 "address":{"@type":"PostalAddress","streetAddress":"Dorf 1","addressLocality":"Ort"},
 "telephone":"+43 1 234","url":"https://hotel-schindler.at","image":"https://hotel-schindler.at/b.jpg",
 "geo":{"@type":"GeoCoordinates","latitude":47.1,"longitude":12.1}}
</script></head><body>
<a href="/faq">Häufige Fragen</a>
</body></html>"""

# FAQ-Unterseite: sichtbare Accordion-Fragen, aber KEIN FAQPage-JSON-LD.
_SCHINDLER_FAQ_SEITE = """<html><head><title>Das Schindler FAQ</title></head><body>
<h1>Das Schindler FAQ</h1>
<div class="faq-module">
  <button class="faq__trigger" role="button" data-gtm-label="Gibt es WLAN?">Gibt es WLAN?</button>
  <button class="faq__trigger" role="button" data-gtm-label="Gibt es eine Sauna?">Gibt es eine Sauna?</button>
  <button class="faq__trigger" role="button">Ab wann steht mein Zimmer bereit?</button>
  <button class="faq__trigger" role="button">Gibt es einen Parkplatz?</button>
  <button class="faq__trigger" role="button">Kann ich Ski mieten?</button>
</div>
</body></html>"""


def test_hat_sichtbaren_faq_inhalt_positiv_und_negativ():
    assert signal2_schema.hat_sichtbaren_faq_inhalt(_SCHINDLER_FAQ_SEITE) is True
    # Startseite ohne Accordion/Frage-Trigger -> kein FAQ-Inhalt
    assert signal2_schema.hat_sichtbaren_faq_inhalt(_SCHINDLER_STARTSEITE) is False
    assert signal2_schema.hat_sichtbaren_faq_inhalt(LODGING_OK) is False


def test_evaluate_html_faq_inhalt_extern_statt_keine_faqpage():
    res = signal2_schema.evaluate_html(
        _SCHINDLER_STARTSEITE, 200, domain="hotel-schindler.at",
        faq_inhalt_extern="/faq")
    assert res.has_faqpage is False
    assert res.faq_inhalt_quelle == "/faq"
    assert "keine FAQPage" not in res.reason
    assert "FAQ-Inhalte" in res.reason
    assert "/faq" in res.reason


def test_evaluate_html_faq_inhalt_auf_startseite_erkannt():
    # Lodging-Entität + sichtbare FAQ im Body derselben Seite
    html = _SCHINDLER_STARTSEITE.replace(
        '<a href="/faq">Häufige Fragen</a>',
        _SCHINDLER_FAQ_SEITE.split("<body>", 1)[1].rsplit("</body>", 1)[0])
    res = signal2_schema.evaluate_html(html, 200, domain="hotel-schindler.at")
    assert res.faq_inhalt_quelle == "Startseite"
    assert "keine FAQPage" not in res.reason
    assert "FAQ-Inhalte" in res.reason


def test_check_schema_schindler_sichtbare_faq_ohne_markup(monkeypatch):
    class _Resp:
        def __init__(self, url, text, status=200):
            self.url, self.text, self.status_code = url, text, status

    def fake_fetch_html(domain, user_agent=None, timeout=None, **_kw):
        return ("https://www.hotel-schindler.at/", _SCHINDLER_STARTSEITE, 200, "")

    def fake_get(url, **_kw):
        if url.rstrip("/").endswith("/faq"):
            return _Resp("https://www.hotel-schindler.at/faq", _SCHINDLER_FAQ_SEITE)
        return _Resp(url, "<html></html>", 404)

    monkeypatch.setattr(signal2_schema, "_fetch_html", fake_fetch_html)
    monkeypatch.setattr(signal2_schema.requests, "get", fake_get)

    res = check_schema("hotel-schindler.at")
    assert res.overall_status == "GELB"           # Markup fehlt weiter -> GELB
    assert res.has_faqpage is False
    assert res.faq_inhalt_quelle == "/faq"
    assert "keine FAQPage" not in res.reason
    assert "FAQ-Inhalte" in res.reason


def test_check_schema_echt_keine_faq_behaelt_phrase(monkeypatch):
    """Ohne jede FAQ (weder Markup noch Inhalt) bleibt 'keine FAQPage' erhalten
    — die Produktions-Weiche (bausteine_aus_befund) hängt an dieser Phrase."""
    class _Resp:
        def __init__(self, url, text, status=200):
            self.url, self.text, self.status_code = url, text, status

    # Startseite ohne FAQ-Link, Lodging-Entität -> GELB
    startseite = _SCHINDLER_STARTSEITE.replace(
        '<a href="/faq">Häufige Fragen</a>', "<p>Willkommen</p>")

    def fake_fetch_html(domain, user_agent=None, timeout=None, **_kw):
        return ("https://www.example.at/", startseite, 200, "")

    def fake_get(url, **_kw):
        # Standard-Pfade (/faq, /faqs, ...) existieren nicht
        return _Resp(url, "<html><body>nix</body></html>", 404)

    monkeypatch.setattr(signal2_schema, "_fetch_html", fake_fetch_html)
    monkeypatch.setattr(signal2_schema.requests, "get", fake_get)

    res = check_schema("example.at")
    assert res.faq_inhalt_quelle is None
    assert "keine FAQPage" in res.reason

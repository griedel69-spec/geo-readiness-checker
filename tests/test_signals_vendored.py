"""
Regressionstest für die übernommenen Signal-Module: Der Befund, der den
Umbau ausgelöst hat (haus-steger.at, generische WordPress-Schema-Typen),
muss von Signal 2 dauerhaft als ROT erkannt werden — nie wieder als bestanden.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "signals"))

import signal2_schema                                              # noqa: E402
from signal2_schema import (                                       # noqa: E402
    evaluate_html, check_schema, finde_faq_kandidaten,
    hat_faqpage_markup, _gleiche_domain,
)

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


# ===========================================================================
# FAQ-Unterseiten-Prüfung (Glocknerhof-Fix, wortgleich portiert aus
# griedel69-spec/geo-radar, src/signal2_schema.py, PR #40) — Regressionsschutz:
# der vendored Kurz-Befund-Checker dieses Repos darf für dieselbe Domain nie
# wieder "keine FAQPage" melden, wenn geo-radar/geo-radar-chat "vorhanden"
# melden. Genau diese Divergenz war schon einmal real (Live-Check am
# 27.07.2026 zeigte "keine FAQPage" für glocknerhof.at, obwohl der
# fixierte geo-radar-Scan seit PR #40 "FAQPage auf /zimmer-preise/
# wissenswertes-faq/" findet).

def _hotel_ohne_faq_und_sameas() -> dict:
    return {
        "@context": "https://schema.org", "@type": "Hotel", "name": "Hotel Alpenblick",
        "address": {"@type": "PostalAddress", "streetAddress": "Bergstrasse 12",
                     "postalCode": "6370", "addressLocality": "Kitzbühel"},
        "geo": {"@type": "GeoCoordinates", "latitude": 47.4467, "longitude": 12.3922},
        "telephone": "+43 5356 12345", "url": "https://example.at",
        "image": "https://example.at/bild.jpg",
    }


def _glocknerhof_startseite() -> str:
    """Startseite wie beim echten Glocknerhof: Hotel-Entität komplett,
    kein FAQPage, kein sameAs — aber ein Link zur FAQ-Unterseite."""
    return (
        '<!doctype html><html><head>'
        f'<script type="application/ld+json">{json.dumps(_hotel_ohne_faq_und_sameas())}</script>'
        '</head><body>'
        '<a href="/zimmer-preise/wissenswertes-faq/">Wissenswertes &amp; FAQ</a>'
        '</body></html>'
    )


def _faq_unterseite() -> str:
    faqpage = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": "Sind Hunde erlaubt?",
         "acceptedAnswer": {"@type": "Answer", "text": "Ja, gegen Aufpreis."}},
    ]}
    return f'<html><head><script type="application/ld+json">{json.dumps(faqpage)}</script></head><body>x</body></html>'


def test_gleiche_domain_faelle():
    assert _gleiche_domain("www.glocknerhof.at", "glocknerhof.at") is True
    assert _gleiche_domain("fremdes-hotel.at", "glocknerhof.at") is False


def test_finde_faq_kandidaten_link_mit_faq_im_pfad():
    urls = finde_faq_kandidaten(
        _glocknerhof_startseite(), "https://www.glocknerhof.at/", "glocknerhof.at")
    assert urls[0] == "https://www.glocknerhof.at/zimmer-preise/wissenswertes-faq/"


def test_hat_faqpage_markup():
    assert hat_faqpage_markup(_faq_unterseite()) is True
    assert hat_faqpage_markup(_glocknerhof_startseite()) is False


def test_evaluate_html_faqpage_extern_zaehlt_als_vorhanden():
    html = f'<html><head><script type="application/ld+json">{json.dumps(_hotel_ohne_faq_und_sameas())}</script></head><body>x</body></html>'
    res = evaluate_html(html, 200, domain="x.at",
                        faqpage_extern="/zimmer-preise/wissenswertes-faq/")
    assert res.has_faqpage is True
    assert res.faqpage_quelle == "/zimmer-preise/wissenswertes-faq/"
    assert "keine FAQPage" not in res.reason
    assert "FAQPage auf /zimmer-preise/wissenswertes-faq/" in res.reason


def test_check_schema_glocknerhof_regression(monkeypatch):
    """Der reale Glocknerhof-Fall End-zu-End (Netz gemockt): Startseite
    ohne FAQPage, FAQ-Unterseite mit gültigem FAQPage-Markup — Signal 2
    darf NICHT mehr 'keine FAQPage' melden."""
    class _Resp:
        def __init__(self, url, text, status=200):
            self.url, self.text, self.status_code = url, text, status

    def fake_fetch_html(domain, user_agent=None, timeout=None, **_kw):
        return ("https://www.glocknerhof.at/", _glocknerhof_startseite(), 200)

    def fake_get(url, **_kw):
        assert "glocknerhof.at" in url  # Domain-Riegel: nichts Fremdes abrufen
        if "wissenswertes-faq" in url:
            return _Resp(url, _faq_unterseite())
        return _Resp(url, "<html></html>", 404)

    monkeypatch.setattr(signal2_schema, "_fetch_html", fake_fetch_html)
    monkeypatch.setattr(signal2_schema.requests, "get", fake_get)

    res = check_schema("glocknerhof.at")
    assert res.has_faqpage is True
    assert res.faqpage_quelle == "/zimmer-preise/wissenswertes-faq/"
    assert "keine FAQPage" not in res.reason
    assert res.overall_status == "GELB"          # weiterhin: kein sameAs
    assert "kein sameAs" in res.reason

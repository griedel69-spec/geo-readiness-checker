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

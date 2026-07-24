"""
Signal 2: Strukturierte Daten (Schema.org JSON-LD)

Frage: Kann die KI die Fakten des Hauses als strukturierte Entität lesen?

Vollständige Bau-Vorgaben stehen in CLAUDE.md, Abschnitt "Signal 2".
Dieses Modul hält sich strikt an die dort definierten Lodging-Typen,
Kernfelder und Schwellen.

Ehrlichkeitsregel (CLAUDE.md): Vorhandenes, aber fehlerhaftes JSON wird
als "vorhanden, aber ungültig" ausgewiesen, nicht still auf GRÜN oder
ROT gezogen.

Nutzung als CLI:
    python src/signal2_schema.py hotel-example.at

Nutzung als Bibliothek:
    from signal2_schema import check_schema
    result = check_schema("hotel-example.at")
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup


# -----------------------------------------------------------------------------
# Vorgaben aus CLAUDE.md
# -----------------------------------------------------------------------------

# Unterkunfts-Typen — die "Lodging-Entität" muss einer davon sein.
LODGING_TYPES = {
    "Hotel",
    "Resort",
    "BedAndBreakfast",
    "Hostel",
    "LodgingBusiness",
    "Apartment",
    "VacationRental",
}

# Generische Typen, die alleine nicht zaehlen — hoechstens ROT.
GENERIC_TYPES = {
    "WebSite",
    "WebPage",
    "Organization",
    "LocalBusiness",   # zaehlt nicht als Lodging
    "BreadcrumbList",
    "Article",
    "BlogPosting",
}

# Kernfelder, die eine Lodging-Entität für GRÜN alle mitbringen muss.
# Reihenfolge = Report-Reihenfolge.
CORE_FIELDS = ("name", "address", "geo", "telephone", "url", "image")

# Empfohlen, aber (per CLAUDE.md GELB-Definition) nicht Blocker für GRÜN.
# Werden im Report als Zusatzinfo gelistet.
EMPFOHLEN_FIELDS = ("priceRange", "amenityFeature", "checkinTime", "checkoutTime")


# -----------------------------------------------------------------------------
# Konfiguration
# -----------------------------------------------------------------------------

DEFAULT_USER_AGENT = os.environ.get(
    "GEO_RADAR_USER_AGENT",
    "GEO-Radar/0.1 (+contact: gernotriedel@gmx.at)",
)
DEFAULT_TIMEOUT = int(os.environ.get("GEO_RADAR_HTTP_TIMEOUT", "15"))


# -----------------------------------------------------------------------------
# Datentypen
# -----------------------------------------------------------------------------

@dataclass
class FieldCheck:
    """Pro Kernfeld: da oder fehlt, plus Kurz-Beleg."""
    name: str
    present: bool
    evidence: str


@dataclass
class LodgingCheck:
    """Details zur gefundenen Lodging-Entität."""
    type_name: str                  # z. B. "Hotel"
    all_types: list[str]            # alle @type-Werte dieser Entität
    fields: list[FieldCheck]        # Kernfelder-Prüfung
    empfohlen: list[FieldCheck]     # empfohlene Zusatzfelder
    has_sameAs: bool
    sameAs_count: int
    sameAs_evidence: str


@dataclass
class SchemaResult:
    """Gesamt-Ergebnis der Schema.org-Prüfung."""
    domain: str
    fetched_url: Optional[str] = None
    fetched_status: Optional[int] = None
    fetch_error: Optional[str] = None
    n_blocks: int = 0
    n_parsed: int = 0
    n_invalid: int = 0
    parse_errors: list[str] = field(default_factory=list)
    all_types: list[str] = field(default_factory=list)
    lodging: Optional[LodgingCheck] = None
    has_faqpage: bool = False
    # Wo das FAQPage-Markup gefunden wurde, wenn NICHT auf der Startseite
    # (z. B. "/zimmer-preise/wissenswertes-faq/"). None = Startseite oder
    # gar nicht gefunden.
    faqpage_quelle: Optional[str] = None
    overall_status: str = "UNBEKANNT"  # GRÜN | GELB | ROT | UNBEKANNT
    reason: str = ""


# -----------------------------------------------------------------------------
# HTTP-Fetch der Startseite (Redirects folgen, HTTPS bevorzugt)
# -----------------------------------------------------------------------------

def _fetch_html(
    domain: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str, str, int] | tuple[None, None, Optional[int]]:
    """
    Holt die Startseite der Domain.

    Rückgabe bei 2xx:      (final_url, html, status)
    Rückgabe sonst:        (None, None, letzter_status_oder_None) -> UNBEKANNT
    """
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-AT,de;q=0.9,en;q=0.7",
    }
    last_status = None

    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/"
        try:
            r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            last_status = r.status_code
            if 200 <= r.status_code < 300:
                return r.url, r.text, r.status_code
            # 4xx/5xx: versuche das andere Schema; ansonsten -> UNBEKANNT
        except requests.RequestException:
            continue

    return None, None, last_status


# -----------------------------------------------------------------------------
# JSON-LD-Blöcke aus HTML ziehen und parsen
# -----------------------------------------------------------------------------

def _extract_ld_blocks(soup: BeautifulSoup) -> list[tuple[Optional[Any], Optional[str]]]:
    """
    Zieht alle <script type="application/ld+json">-Blöcke.

    Rückgabe: Liste von (parsed_json_oder_None, error_oder_None).
    Ein leerer Block wird übersprungen.
    """
    def _has_ld_type(v):
        return v is not None and "application/ld+json" in v.lower()

    blocks: list[tuple[Optional[Any], Optional[str]]] = []
    for script in soup.find_all("script", type=_has_ld_type):
        raw = script.string
        if raw is None:
            raw = script.get_text()
        raw = (raw or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            blocks.append((data, None))
        except json.JSONDecodeError as exc:
            blocks.append((None, f"{exc.__class__.__name__}: {exc.msg} (line {exc.lineno})"))
    return blocks


def _flatten_entities(data: Any, out: Optional[list[dict]] = None) -> list[dict]:
    """
    Sammelt rekursiv alle dicts mit @type-Feld.

    Deckt ab:
    - Top-level Objekt oder Array
    - @graph-Arrays
    - Verschachtelte Entitäten in Properties (z. B. WebPage.mainEntity = Hotel)

    PostalAddress und GeoCoordinates werden als eigene Entitäten mitgesammelt —
    das ist OK, weil unsere LODGING_TYPES-Filter sie ignoriert.
    """
    if out is None:
        out = []
    if isinstance(data, list):
        for item in data:
            _flatten_entities(item, out)
    elif isinstance(data, dict):
        if "@type" in data:
            out.append(data)
        for k, v in data.items():
            if k == "@type":
                continue
            if isinstance(v, (dict, list)):
                _flatten_entities(v, out)
    return out


def _normalize_type(t: Any) -> str:
    """
    Normalisiert Typ-Strings — strippt schema.org-Prefixes wie
    'http://schema.org/Hotel' oder 'schema:Hotel'.
    """
    s = str(t)
    if "/" in s:
        s = s.rsplit("/", 1)[-1]
    if ":" in s:
        s = s.rsplit(":", 1)[-1]
    return s.strip()


def _type_of(entity: dict) -> list[str]:
    """Gibt @type als Liste normalisierter Strings zurück."""
    t = entity.get("@type")
    if isinstance(t, list):
        return [_normalize_type(x) for x in t]
    if t is not None:
        return [_normalize_type(t)]
    return []


def _is_lodging(entity: dict) -> bool:
    return any(t in LODGING_TYPES for t in _type_of(entity))


# -----------------------------------------------------------------------------
# Kernfeld-Prüfungen (jeweils klein und einzeln testbar)
# -----------------------------------------------------------------------------

def _str_nonempty(v: Any) -> Optional[str]:
    """Wenn v ein nicht-leerer String ist, gib ihn zurück. Sonst None."""
    if isinstance(v, list) and v:
        v = v[0]
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _check_name(entity: dict) -> FieldCheck:
    v = _str_nonempty(entity.get("name"))
    if v:
        return FieldCheck("name", True, v[:60])
    return FieldCheck("name", False, "kein name-Feld")


def _check_address(entity: dict) -> FieldCheck:
    addr = entity.get("address")
    if isinstance(addr, list) and addr:
        addr = addr[0]
    if isinstance(addr, dict):
        types = _type_of(addr)
        is_postal = "PostalAddress" in types or not types
        street = _str_nonempty(addr.get("streetAddress")) or ""
        locality = _str_nonempty(addr.get("addressLocality")) or ""
        postal = _str_nonempty(addr.get("postalCode")) or ""
        if is_postal and (street or locality or postal):
            parts = [x for x in [street, postal + " " + locality if postal or locality else ""] if x.strip()]
            summary = ", ".join(p.strip() for p in parts if p.strip())
            return FieldCheck("address", True, f"PostalAddress: {summary}")
        return FieldCheck(
            "address", False,
            f"address dict ohne PostalAddress-Inhalt (types={types or 'unspecified'})"
        )
    if isinstance(addr, str) and addr.strip():
        return FieldCheck("address", False,
                          f"address als Fließtext (nicht als PostalAddress strukturiert): {addr[:60]}")
    return FieldCheck("address", False, "kein address-Feld")


def _check_geo(entity: dict) -> FieldCheck:
    geo = entity.get("geo")
    if isinstance(geo, list) and geo:
        geo = geo[0]
    if isinstance(geo, dict):
        lat = geo.get("latitude")
        lng = geo.get("longitude")
        if lat is not None and lng is not None:
            try:
                float(lat)
                float(lng)
                return FieldCheck("geo", True, f"lat={lat}, lng={lng}")
            except (ValueError, TypeError):
                return FieldCheck("geo", False, "geo mit lat/lng aber nicht numerisch")
    return FieldCheck("geo", False, "kein geo mit lat/lng")


def _check_telephone(entity: dict) -> FieldCheck:
    v = _str_nonempty(entity.get("telephone"))
    if v:
        return FieldCheck("telephone", True, v)
    return FieldCheck("telephone", False, "kein telephone-Feld")


def _check_url(entity: dict) -> FieldCheck:
    v = _str_nonempty(entity.get("url"))
    if v:
        return FieldCheck("url", True, v[:60])
    return FieldCheck("url", False, "kein url-Feld")


def _check_image(entity: dict) -> FieldCheck:
    img = entity.get("image")
    if isinstance(img, str) and img.strip():
        return FieldCheck("image", True, img[:60])
    if isinstance(img, list) and img:
        first = img[0]
        if isinstance(first, str):
            return FieldCheck("image", True, f"{len(img)} Bild(er), erstes: {first[:40]}")
        if isinstance(first, dict):
            u = _str_nonempty(first.get("url")) or _str_nonempty(first.get("contentUrl"))
            if u:
                return FieldCheck("image", True, f"{len(img)} ImageObject(s), erstes: {u[:40]}")
    if isinstance(img, dict):
        u = _str_nonempty(img.get("url")) or _str_nonempty(img.get("contentUrl"))
        if u:
            return FieldCheck("image", True, f"ImageObject: {u[:60]}")
    return FieldCheck("image", False, "kein image-Feld")


def _check_price_range(entity: dict) -> FieldCheck:
    v = _str_nonempty(entity.get("priceRange"))
    if v:
        return FieldCheck("priceRange", True, v)
    return FieldCheck("priceRange", False, "kein priceRange-Feld")


def _check_amenity(entity: dict) -> FieldCheck:
    a = entity.get("amenityFeature")
    if isinstance(a, list) and a:
        return FieldCheck("amenityFeature", True, f"{len(a)} Merkmal(e)")
    if isinstance(a, dict):
        return FieldCheck("amenityFeature", True, "1 Merkmal")
    return FieldCheck("amenityFeature", False, "kein amenityFeature")


def _check_time(entity: dict, key: str) -> FieldCheck:
    v = _str_nonempty(entity.get(key))
    if v:
        return FieldCheck(key, True, v)
    return FieldCheck(key, False, f"kein {key}-Feld")


def _check_sameAs(entity: dict) -> tuple[bool, int, str]:
    sa = entity.get("sameAs")
    if isinstance(sa, list):
        urls = [u for u in sa if isinstance(u, str) and u.strip()]
        if urls:
            preview = ", ".join(urls[:3])
            more = f"  (+{len(urls) - 3} weitere)" if len(urls) > 3 else ""
            return True, len(urls), f"{len(urls)} Link(s): {preview}{more}"
    if isinstance(sa, str) and sa.strip():
        return True, 1, f"1 Link: {sa}"
    return False, 0, "kein sameAs-Feld"


def _run_field_checks(entity: dict) -> tuple[list[FieldCheck], list[FieldCheck]]:
    """Führt alle Kernfeld- und Empfehlungsprüfungen aus."""
    core = [
        _check_name(entity),
        _check_address(entity),
        _check_geo(entity),
        _check_telephone(entity),
        _check_url(entity),
        _check_image(entity),
    ]
    empfohlen = [
        _check_price_range(entity),
        _check_amenity(entity),
        _check_time(entity, "checkinTime"),
        _check_time(entity, "checkoutTime"),
    ]
    return core, empfohlen


# -----------------------------------------------------------------------------
# Hauptfunktion: reine Auswertung (kein Netz)
# -----------------------------------------------------------------------------

def evaluate_html(
    html: str,
    http_status: int = 200,
    domain: str = "",
    fetched_url: Optional[str] = None,
    faqpage_extern: Optional[str] = None,
) -> SchemaResult:
    """
    Wertet HTML-Text aus. Wird sowohl von check_schema() nach dem Fetch als auch
    von Tests direkt aufgerufen.

    faqpage_extern: Pfad einer FAQ-Unterseite, auf der bereits gültiges
    FAQPage-Markup nachgewiesen wurde (Glocknerhof-Fix: FAQPage-Markup
    gehört laut Google-Richtlinie auf die FAQ-Seite selbst, nicht auf die
    Startseite — die frühere Nur-Startseiten-Prüfung hat korrekt
    ausgezeichnete Websites fälschlich mit 'keine FAQPage' bemängelt).
    """
    result = SchemaResult(domain=domain, fetched_url=fetched_url, fetched_status=http_status)

    # Nicht 2xx -> UNBEKANNT (Seite nicht abrufbar)
    if not (200 <= http_status < 300):
        result.overall_status = "UNBEKANNT"
        result.reason = f"Seite nicht abrufbar (HTTP {http_status})"
        return result

    soup = BeautifulSoup(html, "lxml")
    blocks = _extract_ld_blocks(soup)
    result.n_blocks = len(blocks)

    parsed_entities: list[dict] = []
    for data, err in blocks:
        if err is not None:
            result.n_invalid += 1
            result.parse_errors.append(err)
        else:
            result.n_parsed += 1
            parsed_entities.extend(_flatten_entities(data))

    # kein Markup -> ROT
    if result.n_blocks == 0:
        result.overall_status = "ROT"
        result.reason = "kein JSON-LD-Markup auf der Seite gefunden"
        return result

    # alle Blöcke unparsbar -> UNBEKANNT (Ehrlichkeitsregel)
    if result.n_parsed == 0:
        result.overall_status = "UNBEKANNT"
        result.reason = (
            f"alle {result.n_blocks} JSON-LD-Blöcke unparsbar — "
            "vorhanden, aber technisch defekt"
        )
        return result

    # Alle @type-Werte sammeln (dedup, Reihenfolge beibehalten)
    seen_types: list[str] = []
    for e in parsed_entities:
        for t in _type_of(e):
            if t not in seen_types:
                seen_types.append(t)
    result.all_types = seen_types

    # Lodging-Entität suchen
    lodging_entities = [e for e in parsed_entities if _is_lodging(e)]
    result.has_faqpage = any("FAQPage" in _type_of(e) for e in parsed_entities)
    if not result.has_faqpage and faqpage_extern:
        result.has_faqpage = True
        result.faqpage_quelle = faqpage_extern

    if not lodging_entities:
        result.overall_status = "ROT"
        # Wir zeigen die tatsächlich gefundenen Typen — Grundregel 2 (Belege).
        types_str = ", ".join(seen_types) if seen_types else "(keine)"
        result.reason = (
            f"keine Lodging-Entität (Hotel/Resort/BedAndBreakfast/Hostel/"
            f"LodgingBusiness/Apartment/VacationRental). Gefunden: {types_str}"
        )
        return result

    # "Beste" Lodging-Entität wählen (die mit den meisten Kernfeldern).
    def _score(e: dict) -> int:
        return sum(1 for f in CORE_FIELDS if e.get(f))
    lodging = max(lodging_entities, key=_score)
    lodging_types = _type_of(lodging)
    lodging_type_name = next(
        (t for t in lodging_types if t in LODGING_TYPES),
        lodging_types[0] if lodging_types else "?",
    )

    core_checks, empf_checks = _run_field_checks(lodging)
    has_sa, sa_count, sa_evidence = _check_sameAs(lodging)
    result.lodging = LodgingCheck(
        type_name=lodging_type_name,
        all_types=lodging_types,
        fields=core_checks,
        empfohlen=empf_checks,
        has_sameAs=has_sa,
        sameAs_count=sa_count,
        sameAs_evidence=sa_evidence,
    )

    # Beleg-Zusatz, wenn das FAQPage-Markup auf einer FAQ-Unterseite
    # nachgewiesen wurde (Belege statt Urteile: Fundstelle nennen).
    quelle_hinweis = (
        f" (FAQPage auf {result.faqpage_quelle})" if result.faqpage_quelle else ""
    )

    missing_core = [c.name for c in core_checks if not c.present]
    if not missing_core and result.has_faqpage and has_sa:
        result.overall_status = "GRÜN"
        result.reason = (
            f"vollständige Lodging-Entität ({lodging_type_name}) + FAQPage + sameAs"
            + quelle_hinweis
        )
    else:
        gaps: list[str] = []
        if missing_core:
            gaps.append("Kernfelder fehlen: " + ", ".join(missing_core))
        if not result.has_faqpage:
            gaps.append("keine FAQPage")
        if not has_sa:
            gaps.append("kein sameAs")
        result.overall_status = "GELB"
        result.reason = (
            f"Lodging-Entität ({lodging_type_name}) vorhanden, aber unvollständig — "
            + "; ".join(gaps)
            + quelle_hinweis
        )

    return result


# -----------------------------------------------------------------------------
# FAQ-Unterseiten-Prüfung (Glocknerhof-Fix)
# -----------------------------------------------------------------------------
# FAQPage-Markup gehört laut Google-Richtlinie auf die Seite, auf der die
# FAQ sichtbar ist — typischerweise eine Unterseite, NICHT die Startseite.
# Die frühere Nur-Startseiten-Prüfung hat deshalb korrekt ausgezeichnete
# Websites (Beweisfall glocknerhof.at: gültiges FAQPage mit 16 Fragen auf
# /zimmer-preise/wissenswertes-faq/) dauerhaft mit "keine FAQPage"
# bemängelt — und die Produktion hat daraufhin unnötig einen FAQ-Baustein
# erzeugt. Jetzt: findet die Startseite kein FAQPage, werden bis zu
# _MAX_FAQ_UNTERSEITEN FAQ-Kandidaten der GLEICHEN Domain nachgeprüft.

_FAQ_LINK_SCHLUESSEL = ("faq", "fragen", "wissenswert")
_FAQ_STANDARD_PFADE = ("/faq", "/faqs", "/haeufige-fragen", "/fragen")
_MAX_FAQ_UNTERSEITEN = 3


def _gleiche_domain(netloc: str, dom: str) -> bool:
    """Locker genug für www./Subdomain-Varianten, hart gegen Fremd-Domains
    (gleiche Regel wie der Domain-Riegel des Produktions-Crawlers)."""
    n = netloc.lower().split(":")[0]
    d = dom.lower().split(":")[0]
    for prefix in ("www.",):
        if n.startswith(prefix):
            n = n[len(prefix):]
        if d.startswith(prefix):
            d = d[len(prefix):]
    return n == d or n.endswith("." + d)


def finde_faq_kandidaten(html: str, basis_url: str, dom: str) -> list[str]:
    """
    Sammelt FAQ-Kandidaten-URLs aus dem Startseiten-HTML: Links, deren
    href ODER Ankertext ein FAQ-Schlüsselwort enthält, plus die
    Standard-Pfade. Nur gleiche Domain, dedupliziert, Reihenfolge:
    echte Links zuerst (die treffen fast immer), Standard-Pfade danach.
    """
    from urllib.parse import urljoin, urlparse

    kandidaten: list[str] = []
    gesehen: set[str] = set()

    def _nimm(url: str) -> None:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return
        if not _gleiche_domain(p.netloc, dom):
            return
        schluessel = url.rstrip("/")
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            kandidaten.append(url)

    try:
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(" ", strip=True)
            blob = (href + " " + text).lower()
            if any(k in blob for k in _FAQ_LINK_SCHLUESSEL):
                _nimm(urljoin(basis_url, href))
    except Exception:
        pass  # kaputtes HTML: dann eben nur die Standard-Pfade

    for pfad in _FAQ_STANDARD_PFADE:
        _nimm(urljoin(basis_url, pfad))

    return kandidaten[:_MAX_FAQ_UNTERSEITEN]


def hat_faqpage_markup(html: str) -> bool:
    """Prüft ein HTML NUR auf gültiges FAQPage-JSON-LD (deterministisch)."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return False
    for data, err in _extract_ld_blocks(soup):
        if err is not None:
            continue
        if any("FAQPage" in _type_of(e) for e in _flatten_entities(data)):
            return True
    return False


def _pruefe_faq_unterseiten(
    kandidaten: list[str], dom: str,
    user_agent: str, timeout: int,
) -> tuple[Optional[str], int]:
    """
    Ruft die Kandidaten-URLs ab und sucht FAQPage-Markup. Rückgabe:
    (Pfad_der_Fundstelle_oder_None, Anzahl_geprüfter_Seiten).
    Weiterleitungen auf fremde Domains werden verworfen (Domain-Riegel).
    """
    from urllib.parse import urlparse
    import time as _time

    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-AT,de;q=0.9,en;q=0.7",
    }
    geprueft = 0
    for i, url in enumerate(kandidaten):
        if i > 0:
            _time.sleep(0.3)  # höflich zwischen Requests
        try:
            r = requests.get(url, headers=headers, timeout=timeout,
                             allow_redirects=True)
        except requests.RequestException:
            continue
        if not (200 <= r.status_code < 300):
            continue
        if not _gleiche_domain(urlparse(r.url).netloc, dom):
            continue
        geprueft += 1
        if hat_faqpage_markup(r.text):
            return urlparse(r.url).path or "/", geprueft
    return None, geprueft


# -----------------------------------------------------------------------------
# Netzwerk-Wrapper
# -----------------------------------------------------------------------------

def check_schema(
    domain: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
) -> SchemaResult:
    """Prüft eine Domain auf Schema.org-JSON-LD. Interpretiert nichts — nur Fakten."""
    dom = domain.strip()
    if dom.startswith("https://"):
        dom = dom[8:]
    elif dom.startswith("http://"):
        dom = dom[7:]
    dom = dom.strip("/")

    final_url, html, status = _fetch_html(dom, user_agent=user_agent, timeout=timeout)

    if final_url is None:
        result = SchemaResult(domain=dom, fetched_status=status)
        result.fetch_error = (
            "Startseite nicht abrufbar (Timeout/DNS/Connection-Fehler"
            + (f", letzter Status {status}" if status else "")
            + ")"
        )
        result.overall_status = "UNBEKANNT"
        result.reason = "HTML konnte nicht geladen werden"
        return result

    result = evaluate_html(html or "", status or 200, dom, final_url)

    # Glocknerhof-Fix: Startseite ohne FAQPage heißt noch nicht "keine
    # FAQPage" — das Markup gehört auf die FAQ-Unterseite. Nachprüfen,
    # bevor der Mangel behauptet wird (nur wenn eine Lodging-Entität da
    # ist; ohne die entscheidet die FAQPage ohnehin nichts).
    if result.overall_status == "GELB" and not result.has_faqpage:
        kandidaten = finde_faq_kandidaten(html or "", final_url, dom)
        if kandidaten:
            quelle, geprueft = _pruefe_faq_unterseiten(
                kandidaten, dom, user_agent, timeout)
            if quelle:
                result = evaluate_html(html or "", status or 200, dom,
                                       final_url, faqpage_extern=quelle)
            elif geprueft:
                # Ehrlich präzisieren: nicht nur die Startseite wurde
                # geprüft. Der Wortlaut "keine FAQPage" bleibt erhalten —
                # die Produktions-Weiche (bausteine_aus_befund) hängt an
                # genau dieser Phrase.
                result.reason = result.reason.replace(
                    "keine FAQPage",
                    f"keine FAQPage (Startseite + {geprueft} "
                    f"FAQ-Unterseite(n) geprüft)",
                )

    return result


# -----------------------------------------------------------------------------
# Menschenlesbarer Ausdruck
# -----------------------------------------------------------------------------

def format_report(res: SchemaResult) -> str:
    lines: list[str] = []
    lines.append(f"Domain: {res.domain}")
    if res.fetched_url:
        lines.append(f"Startseite: {res.fetched_url}  (HTTP {res.fetched_status})")
    if res.fetch_error:
        lines.append(f"Fehler: {res.fetch_error}")
    lines.append(f"Ampel: {res.overall_status}  —  {res.reason}")
    lines.append("")
    lines.append(
        f"JSON-LD-Blöcke: {res.n_blocks} gesamt, "
        f"{res.n_parsed} parsbar, {res.n_invalid} ungültig"
    )
    for err in res.parse_errors[:3]:
        lines.append(f"  ! Parse-Fehler: {err}")
    if res.all_types:
        lines.append(f"@type-Werte gefunden: {', '.join(res.all_types)}")
    else:
        lines.append("@type-Werte gefunden: (keine)")
    lines.append("")

    if res.lodging:
        lines.append(
            f"Lodging-Entität: {res.lodging.type_name}  "
            f"(alle @types: {', '.join(res.lodging.all_types)})"
        )
        lines.append("Kernfelder (für GRÜN alle nötig):")
        for fc in res.lodging.fields:
            mark = "OK   " if fc.present else "FEHLT"
            lines.append(f"  [{mark}] {fc.name}: {fc.evidence}")
        sa_mark = "OK   " if res.lodging.has_sameAs else "FEHLT"
        lines.append(f"  [{sa_mark}] sameAs: {res.lodging.sameAs_evidence}")

        lines.append("")
        lines.append("Empfohlen (nicht Blocker):")
        for fc in res.lodging.empfohlen:
            mark = "OK  " if fc.present else "leer"
            lines.append(f"  [{mark}] {fc.name}: {fc.evidence}")
    else:
        lines.append("Lodging-Entität: KEINE gefunden")

    fp_mark = "OK   " if res.has_faqpage else "FEHLT"
    if res.faqpage_quelle:
        fp_text = f"vorhanden (auf {res.faqpage_quelle})"
    else:
        fp_text = "vorhanden" if res.has_faqpage else "nicht vorhanden"
    lines.append("")
    lines.append(f"[{fp_mark}] FAQPage: {fp_text}")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Nutzung: python src/signal2_schema.py <domain>")
        print("Beispiel: python src/signal2_schema.py hotel-example.at")
        return 2
    res = check_schema(argv[0])
    print(format_report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())

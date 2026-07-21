"""
Signal 3: Maschinenlesbarkeit (Server-Side Rendering) — BATCH-Variante.

Frage: Stehen Zimmer, Lage, Preise, Kontakt im ausgelieferten HTML oder erst
       nach JavaScript (und damit für KI-Crawler unsichtbar)?

Diese Datei liefert nur die kostenlose HTTP-Variante nach CLAUDE.md
Bau-Reihenfolge Punkt 4. Die Tiefenaudit-Variante mit Playwright kommt
später (Bau-Reihenfolge Punkt 6-7 nach Piloten-Kalibrierung).

Was wir OHNE Render tun können:
- sichtbaren Textumfang im rohen HTML messen (ohne <script>/<style>)
- SPA-Signaturen erkennen (Framework-Anker + fast leerer Body)
- prüfen, ob Adresse und Telefon im rohen HTML vorkommen

Hartes Kriterium (CLAUDE.md): Fehlt Adresse oder Telefon im rohen HTML,
ist es mindestens GELB, egal wie viele Zeichen der Body zaehlt.

Nutzung als CLI:
    python src/signal3_rendering.py hotel-example.at
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup, Comment


# -----------------------------------------------------------------------------
# Startwerte für die Batch-Variante (in CLAUDE.md steht: am Piloten kalibrieren).
# Alle als Konstanten oben, damit die Kalibrierung an einer Stelle stattfindet.
# -----------------------------------------------------------------------------

# Sichtbarer Textumfang im Body (nach Script/Style-Strip).
# Unter TEXT_MIN_SUBSTANZ = die Seite ist duenn und braucht wahrscheinlich Render.
TEXT_MIN_SUBSTANZ = 1000

# Deutlich unter Schwelle -> starkes Verdachtssignal für SPA-Shell.
TEXT_KRITISCH = 300

# Wenn Framework-Marker vorhanden UND weniger als so viele Zeichen sichtbar,
# gilt es als "SPA verdaechtig".
SPA_MARKER_TEXT_LIMIT = 1000

# HTTP
DEFAULT_USER_AGENT = os.environ.get(
    "GEO_RADAR_USER_AGENT",
    "GEO-Radar/0.1 (+contact: gernotriedel@gmx.at)",
)
DEFAULT_TIMEOUT = int(os.environ.get("GEO_RADAR_HTTP_TIMEOUT", "15"))


# -----------------------------------------------------------------------------
# Framework-Anker: kein Killerkriterium für sich allein, aber kombiniert mit
# duennem Body ein starkes Indiz für SPA-Shell.
# -----------------------------------------------------------------------------

FRAMEWORK_MARKERS: list[tuple[str, str]] = [
    (r'<div\s+[^>]*id=["\']root["\']', 'React/Vite #root-Anker'),
    (r'<div\s+[^>]*id=["\']app["\']', 'Vue/Nuxt #app-Anker'),
    (r'<div\s+[^>]*id=["\']__next["\']', 'Next.js __next-Anker'),
    (r'<div\s+[^>]*id=["\']__nuxt["\']', 'Nuxt __nuxt-Anker'),
    (r'\bdata-reactroot\b', 'React data-reactroot Attribut'),
    (r'\bng-version\s*=', 'Angular ng-version Attribut'),
    (r'\bng-app\s*=', 'AngularJS ng-app Attribut'),
    (r'\bdata-v-[a-f0-9]{6,}', 'Vue.js data-v- Attribute'),
]


# -----------------------------------------------------------------------------
# Adresse und Telefon — bewusst tolerante Regeln, damit deutsche und
# österreichische Formate sicher greifen.
# -----------------------------------------------------------------------------

# +43 5356 12345  oder  0043 5356 12345
PHONE_INTERNATIONAL = re.compile(
    r'(?:\+|00)\d{1,3}[\s\-\/\.\(\)]{0,3}\d{1,5}[\s\-\/\.\(\)]{0,3}\d{2,}[\s\-\/\.\(\)]{0,3}\d{2,}'
)

# 0512 12345 (Inlands-Vorwahl)
PHONE_DOMESTIC = re.compile(
    r'\b0\d{2,4}[\s\-\/\.\(\)]{1,3}\d{3,}[\s\-\/\.\(\)]{0,3}\d{0,}'
)

# "Bergstraße 12", "Hauptstrasse 5", "Muehlweg 3", "Kirchplatz 1", "Str. 7"
ADDRESS_STREET = re.compile(
    r'\b[A-ZÄÖÜa-zäöüß\-]+(?:straße|strasse|str\.|weg|gasse|platz|allee|ring|ufer)\s+\d{1,4}\b',
    re.IGNORECASE,
)

# "6370 Kitzbühel", "1010 Wien" — PLZ 4-5 stellig plus Ort mit Grossbuchstabe.
# Bewusst keine Ziffer davor, um Preise wie "6370 EUR" auszuschließen.
ADDRESS_PLZ_ORT = re.compile(
    r'(?:^|[^\d])(\d{4,5})\s+([A-ZÄÖÜ][A-Za-zäöüß\-]{2,30})\b'
)


# -----------------------------------------------------------------------------
# Datentypen
# -----------------------------------------------------------------------------

@dataclass
class RenderingResult:
    """Ergebnis der Rendering-Prüfung (Batch-Variante)."""
    domain: str
    fetched_url: Optional[str] = None
    fetched_status: Optional[int] = None
    fetch_error: Optional[str] = None

    # Sichtbarer Textumfang im rohen HTML (nach Script/Style/Comment-Strip)
    visible_text_length: int = 0

    # SPA-Verdachts-Info
    is_spa_suspect: bool = False
    spa_markers_found: list[str] = field(default_factory=list)

    # Kontaktinfos im rohen HTML
    has_address: bool = False
    address_evidence: str = ""
    has_phone: bool = False
    phone_evidence: str = ""

    overall_status: str = "UNBEKANNT"  # GRÜN | GELB | ROT | UNBEKANNT
    reason: str = ""


# -----------------------------------------------------------------------------
# HTTP-Fetch
# -----------------------------------------------------------------------------

def _fetch_html(
    domain: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str, str, int] | tuple[None, None, Optional[int]]:
    """Holt die Startseite. Rückgabe wie in Signal 2."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
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
        except requests.RequestException:
            continue
    return None, None, last_status


# -----------------------------------------------------------------------------
# Text-/Struktur-Analyse
# -----------------------------------------------------------------------------

def _visible_text(html: str) -> str:
    """
    Extrahiert den sichtbaren Text aus dem HTML.
    Entfernt <script>, <style>, <noscript>, <template> und Kommentare.
    <nav>, <header>, <footer> BLEIBEN — dort steht oft der Kontakt.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    return soup.get_text(separator=" ", strip=True)


def _detect_framework_markers(html: str) -> list[str]:
    """Findet alle Framework-Anker im HTML — case-insensitive."""
    found = []
    for pattern, label in FRAMEWORK_MARKERS:
        if re.search(pattern, html, re.IGNORECASE):
            found.append(label)
    return found


def _find_phone(html: str) -> tuple[bool, str]:
    """Sucht ein Telefon-Muster im rohen HTML."""
    m = PHONE_INTERNATIONAL.search(html)
    if m:
        return True, m.group(0).strip()
    m = PHONE_DOMESTIC.search(html)
    if m:
        return True, m.group(0).strip()
    return False, ""


def _find_address(html: str) -> tuple[bool, str]:
    """
    Sucht ein Adress-Muster im rohen HTML. Zwei Wege:
    1. Straßenname + Hausnummer (z. B. 'Bergstraße 12')
    2. PLZ + Ort (z. B. '6370 Kitzbühel')
    """
    m = ADDRESS_STREET.search(html)
    if m:
        return True, m.group(0).strip()
    m = ADDRESS_PLZ_ORT.search(html)
    if m:
        # Gruppen 1 und 2 sind PLZ und Ort
        return True, f"{m.group(1)} {m.group(2)}".strip()
    return False, ""


# -----------------------------------------------------------------------------
# Hauptfunktion: reine Auswertung (kein Netz)
# -----------------------------------------------------------------------------

def evaluate_html(
    html: str,
    http_status: int = 200,
    domain: str = "",
    fetched_url: Optional[str] = None,
) -> RenderingResult:
    """Wertet HTML-Text aus. Rein — kein Netz — leicht testbar."""
    result = RenderingResult(domain=domain, fetched_url=fetched_url, fetched_status=http_status)

    if not (200 <= http_status < 300):
        result.overall_status = "UNBEKANNT"
        result.reason = f"Seite nicht abrufbar (HTTP {http_status})"
        return result

    text = _visible_text(html)
    result.visible_text_length = len(text)

    markers = _detect_framework_markers(html)
    result.spa_markers_found = markers
    # SPA-Verdacht = Framework-Marker UND wenig sichtbarer Text.
    result.is_spa_suspect = bool(markers) and result.visible_text_length < SPA_MARKER_TEXT_LIMIT

    result.has_address, result.address_evidence = _find_address(html)
    result.has_phone, result.phone_evidence = _find_phone(html)

    # Ampel-Logik in Reihenfolge der Prioritaet:

    # 1) SPA-Shell ohne jegliche Kontaktinfos -> klarer Notfall = ROT
    if (
        result.is_spa_suspect
        and result.visible_text_length < TEXT_KRITISCH
        and not result.has_address
        and not result.has_phone
    ):
        parts = ["SPA-Shell erkannt: " + ", ".join(markers)]
        parts.append(f"nur {result.visible_text_length} sichtbare Zeichen")
        parts.append("weder Adresse noch Telefon im rohen HTML")
        result.overall_status = "ROT"
        result.reason = "; ".join(parts)
        return result

    # 2) Hartes Kriterium aus CLAUDE.md:
    #    Fehlt Adresse ODER Telefon im rohen HTML -> mindestens GELB.
    if not result.has_address or not result.has_phone:
        parts = []
        if not result.has_address:
            parts.append("Adresse fehlt im rohen HTML")
        if not result.has_phone:
            parts.append("Telefon fehlt im rohen HTML")
        parts.append(f"{result.visible_text_length} sichtbare Zeichen im Body")
        if markers:
            parts.append("Framework-Marker: " + ", ".join(markers))
        result.overall_status = "GELB"
        result.reason = "; ".join(parts)
        return result

    # 3) Framework-Marker plus dünner Body -> SPA-Verdacht,
    #    obwohl Kontakt gefunden -> Vollrender-Check empfohlen -> GELB
    if result.is_spa_suspect:
        result.overall_status = "GELB"
        result.reason = (
            f"SPA-Verdacht ({', '.join(markers)}), nur {result.visible_text_length} "
            "sichtbare Zeichen — Tiefenaudit mit Render-Vergleich empfohlen"
        )
        return result

    # 4) Sehr wenig sichtbarer Text, auch ohne Marker -> Zweifel -> GELB
    if result.visible_text_length < TEXT_KRITISCH:
        result.overall_status = "GELB"
        result.reason = (
            f"nur {result.visible_text_length} sichtbare Zeichen im Body — "
            "wesentliche Inhalte kommen möglicherweise erst nach JavaScript"
        )
        return result

    # 5) Duenner mittlerer Bereich -> GELB
    if result.visible_text_length < TEXT_MIN_SUBSTANZ:
        result.overall_status = "GELB"
        result.reason = (
            f"{result.visible_text_length} sichtbare Zeichen — dünner Body, "
            "wesentliche Teile (FAQ, Zimmer) möglicherweise erst nach Render"
        )
        return result

    # 6) Alles gut: substantieller Body, Kontakt vorhanden, kein SPA-Marker
    result.overall_status = "GRÜN"
    result.reason = (
        f"{result.visible_text_length} sichtbare Zeichen im Body, "
        "Adresse und Telefon im rohen HTML"
    )
    return result


# -----------------------------------------------------------------------------
# Netzwerk-Wrapper
# -----------------------------------------------------------------------------

def check_rendering(
    domain: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
) -> RenderingResult:
    """Prüft eine Domain auf Render-Auslieferung. Interpretiert nichts."""
    dom = domain.strip()
    if dom.startswith("https://"):
        dom = dom[8:]
    elif dom.startswith("http://"):
        dom = dom[7:]
    dom = dom.strip("/")

    final_url, html, status = _fetch_html(dom, user_agent=user_agent, timeout=timeout)

    if final_url is None:
        result = RenderingResult(domain=dom, fetched_status=status)
        result.fetch_error = (
            "Startseite nicht abrufbar (Timeout/DNS/Connection-Fehler"
            + (f", letzter Status {status}" if status else "")
            + ")"
        )
        result.overall_status = "UNBEKANNT"
        result.reason = "HTML konnte nicht geladen werden"
        return result

    return evaluate_html(html or "", status or 200, dom, final_url)


# -----------------------------------------------------------------------------
# Menschenlesbarer Ausdruck
# -----------------------------------------------------------------------------

def format_report(res: RenderingResult) -> str:
    lines: list[str] = []
    lines.append(f"Domain: {res.domain}")
    if res.fetched_url:
        lines.append(f"Startseite: {res.fetched_url}  (HTTP {res.fetched_status})")
    if res.fetch_error:
        lines.append(f"Fehler: {res.fetch_error}")
    lines.append(f"Ampel: {res.overall_status}  —  {res.reason}")
    lines.append("")
    lines.append(f"Sichtbarer Textumfang im Body: {res.visible_text_length} Zeichen")
    if res.spa_markers_found:
        lines.append("Framework-Marker gefunden: " + ", ".join(res.spa_markers_found))
        lines.append(f"SPA-Verdacht: {'JA' if res.is_spa_suspect else 'nein'}")
    else:
        lines.append("Framework-Marker gefunden: keine")
    addr_mark = "OK   " if res.has_address else "FEHLT"
    phone_mark = "OK   " if res.has_phone else "FEHLT"
    lines.append(f"[{addr_mark}] Adresse im rohen HTML: "
                 + (res.address_evidence if res.has_address else "nicht gefunden"))
    lines.append(f"[{phone_mark}] Telefon im rohen HTML: "
                 + (res.phone_evidence if res.has_phone else "nicht gefunden"))
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Nutzung: python src/signal3_rendering.py <domain>")
        print("Beispiel: python src/signal3_rendering.py hotel-example.at")
        return 2
    res = check_rendering(argv[0])
    print(format_report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())

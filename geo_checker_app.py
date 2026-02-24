import streamlit as st
import anthropic
import json
import csv
import io
import datetime
import re
import time
import requests
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from fpdf import FPDF

# ─── PAGE CONFIG ───
st.set_page_config(
    page_title="GEO-Readiness Checker | Gernot Riedel Tourism Consulting",
    page_icon="🏔",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── CSS ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.main-header { background: linear-gradient(135deg, #1a2332 0%, #2d4a3e 100%); padding: 36px 32px 28px; border-radius: 8px; margin-bottom: 28px; }
.main-header h1 { color: #ffffff; font-size: 32px; font-weight: 700; margin: 0 0 8px 0; }
.main-header h1 span { color: #c9a84c; }
.main-header p { color: rgba(255,255,255,0.7); font-size: 15px; margin: 0; line-height: 1.6; }
.brand-tag { display: inline-block; background: rgba(201,168,76,0.2); border: 1px solid rgba(201,168,76,0.4); color: #e8c97a; padding: 4px 12px; border-radius: 2px; font-size: 11px; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 16px; }
.score-box { background: linear-gradient(135deg, #1a2332, #2d4a3e); border-radius: 8px; padding: 24px; text-align: center; color: white; }
.score-number { font-size: 56px; font-weight: 800; line-height: 1; }
.score-excellent { color: #7ab89a; }
.score-good { color: #c9a84c; }
.score-poor { color: #e67e22; }
.score-critical { color: #c0392b; }
.win-sofort { background: #fde8e8; border-left: 4px solid #c0392b; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 8px; }
.win-kurz   { background: #fef3e2; border-left: 4px solid #e67e22; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 8px; }
.win-mittel { background: #eaf5f0; border-left: 4px solid #27ae60; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 8px; }
.cta-box { background: linear-gradient(135deg, #1a2332 0%, #2d4a3e 100%); border-radius: 8px; padding: 28px 32px; color: white; margin-top: 24px; }
.footer-bar { background: #1a2332; color: rgba(255,255,255,0.5); padding: 16px 24px; border-radius: 8px; text-align: center; font-size: 12px; margin-top: 40px; }
div[data-testid="stForm"] { background: white; padding: 24px; border-radius: 8px; border: 1px solid #e8e3da; }
.stButton > button { background: #3d7a5e !important; color: white !important; font-weight: 700 !important; font-size: 16px !important; padding: 14px 28px !important; border-radius: 4px !important; border: none !important; width: 100% !important; }
.stButton > button:hover { background: #2d4a3e !important; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───
st.markdown("""
<div class="main-header">
    <div class="brand-tag">🏔 Gernot Riedel Tourism Consulting</div>
    <h1>GEO-Readiness <span>Checker</span></h1>
    <p>Kostenlose Website-Analyse für Tourismusbetriebe im DACH-Raum.<br>
    Erfahren Sie in 60 Sekunden, wie gut Ihr Betrieb in der KI-gestützten Suche sichtbar ist.</p>
</div>
""", unsafe_allow_html=True)

# ─── SESSION STATE ───
if "leads" not in st.session_state:
    st.session_state.leads = []
if "result" not in st.session_state:
    st.session_state.result = None
if "anfrage_gesendet" not in st.session_state:
    st.session_state.anfrage_gesendet = False


# ══════════════════════════════════════════════════════════
# CRAWLER
# ══════════════════════════════════════════════════════════

def crawl_website(base_url):
    """Crawlt Hotel-Website: Sitemap → FAQ → Unterseiten (2 Ebenen)."""

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text_parts = []
            self.links = []
            self.skip_tags = {"script", "style", "head", "noscript", "iframe"}
            self.current_skip = 0
            self.headings = []
            self.in_heading = False
            self.current_tag = ""

        def handle_starttag(self, tag, attrs):
            if tag in self.skip_tags:
                self.current_skip += 1
            self.current_tag = tag
            if tag in ("h1", "h2", "h3"):
                self.in_heading = True
            if tag == "a":
                for attr, val in attrs:
                    if attr == "href" and val:
                        self.links.append(val)

        def handle_endtag(self, tag):
            if tag in self.skip_tags:
                self.current_skip = max(0, self.current_skip - 1)
            if tag in ("h1", "h2", "h3"):
                self.in_heading = False

        def handle_data(self, data):
            if self.current_skip == 0:
                text = data.strip()
                if text and len(text) > 2:
                    if self.in_heading:
                        self.headings.append(f"[{self.current_tag.upper()}] {text}")
                    self.text_parts.append(text)

        def get_text(self):
            return " ".join(self.text_parts)

    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    base_url = base_url.rstrip("/")
    base_domain = urlparse(base_url).netloc

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GEO-Checker/1.0)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "de-AT,de;q=0.9"
    }

    exclude_patterns = [
        "datenschutz", "cookie", "impressum", "agb", "privacy",
        "sitemap", "robots", ".xml", ".pdf", "login", "admin",
        "wp-admin", "wp-login", "feed", "rss", "javascript:"
    ]
    faq_patterns = ["faq", "haeufig", "faq.html", "faq.php"]
    content_patterns = [
        "zimmer", "rooms", "appartement", "wohnung", "suite",
        "ueber", "about", "uns", "lage", "anreise",
        "wellness", "spa", "angebot", "preise", "kontakt",
        "aktivitaet", "sommer", "winter", "service",
        "gut-zu-wissen", "buchungsinformation"
    ]

    def fetch_page(url):
        try:
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                html = resp.text
                parser = TextExtractor()
                parser.feed(html)
                text = parser.get_text()
                # JS-FAQ Accordion Extraktion
                faq_spans = re.findall(r'<span>([^<]{15,200}\?)</span>', html)
                if faq_spans:
                    text += "\n\nFAQ-FRAGEN AUF DIESER SEITE:\n" + "\n".join(f"- {q}" for q in faq_spans[:30])
                return text[:8000], parser.headings[:30], parser.links
        except Exception:
            pass
        return None, [], []

    def get_sitemap_urls(base):
        found = []
        for candidate in [base + "/sitemap.xml", base + "/sitemap_index.xml", base + "/sitemap.php"]:
            try:
                r = requests.get(candidate, headers=headers, timeout=8)
                if r.status_code == 200:
                    urls = re.findall(r'<loc>(https?://[^<]+)</loc>', r.text)
                    for u in urls:
                        if base_domain in u and u not in found:
                            found.append(u)
                    if found:
                        break
            except Exception:
                pass
        return found

    def is_valid_url(u, seen):
        u = u.rstrip("/")
        if u in seen:
            return False
        try:
            p = urlparse(u)
        except Exception:
            return False
        if base_domain not in p.netloc:
            return False
        path = p.path.lower()
        if any(ex in path for ex in exclude_patterns):
            return False
        return True

    def url_priority(path):
        for pat in content_patterns:
            if pat in path:
                return 4
        return 1

    pages = {}
    seen = set()

    # 1. Startseite
    text, headings, links = fetch_page(base_url)
    if text:
        pages["Startseite"] = {"text": text, "headings": headings}
    seen.add(base_url)

    # 2. Sitemap
    sitemap_urls = get_sitemap_urls(base_url)

    # 3. FAQ-Seiten bevorzugt crawlen
    de_faq, other_faq = [], []
    for u in sitemap_urls:
        path = urlparse(u).path.lower()
        if any(p in path for p in faq_patterns):
            if "/de/" in path:
                de_faq.append(u)
            elif "/en/" not in path and "/fr/" not in path:
                other_faq.append(u)
    for link in links:
        full = urljoin(base_url, link).rstrip("/")
        path = urlparse(full).path.lower()
        if base_domain in full and any(p in path for p in faq_patterns):
            if full not in de_faq and full not in other_faq:
                other_faq.append(full)

    for faq_url in (de_faq + other_faq)[:3]:
        seen.add(faq_url)
        t, h, _ = fetch_page(faq_url)
        if t:
            pages["FAQ-Seite"] = {"text": t, "headings": h}
            break

    # 4. URL-Pool aufbauen
    url_pool = sitemap_urls if sitemap_urls else [
        urljoin(base_url, l).rstrip("/") for l in links
        if urljoin(base_url, l).startswith("http") and base_domain in urljoin(base_url, l)
    ]

    priority_list = []
    for u in url_pool:
        u_clean = u.rstrip("/")
        if not is_valid_url(u_clean, seen):
            continue
        path = urlparse(u_clean).path.lower()
        priority_list.append((url_priority(path), u_clean, path))
        seen.add(u_clean)
    priority_list.sort(reverse=True)

    # 5. Ebene 1: bis zu 10 Seiten
    level2_links = []
    for _, sub_url, sub_path in priority_list[:10]:
        name = sub_path.strip("/").split("/")[-1][:40] or sub_path.strip("/")[:40]
        t, h, sub_links = fetch_page(sub_url)
        if t:
            pages[name] = {"text": t, "headings": h}
            if not sitemap_urls:
                level2_links.extend(sub_links)

    # 6. Ebene 2: bis zu 5 weitere Seiten (nur ohne Sitemap)
    if not sitemap_urls and len(pages) < 8:
        level2_list = []
        for link in level2_links:
            full = urljoin(base_url, link).rstrip("/")
            if full.startswith("http") and base_domain in full and is_valid_url(full, seen):
                path = urlparse(full).path.lower()
                level2_list.append((url_priority(path), full, path))
                seen.add(full)
        level2_list.sort(reverse=True)
        for _, sub_url, sub_path in level2_list[:5]:
            name = sub_path.strip("/").split("/")[-1][:40] or sub_path.strip("/")[:40]
            t, h, _ = fetch_page(sub_url)
            if t:
                pages[name] = {"text": t, "headings": h}

    # 7. Crawl-Status
    total_text = " ".join(d.get("text", "") for d in pages.values())
    main_ok = "Startseite" in pages and len(pages["Startseite"].get("text", "")) > 200
    total_chars = len(total_text)

    if not main_ok:
        stufe = 1
    elif len(pages) <= 1 or total_chars < 800:
        stufe = 2
    else:
        stufe = 3

    return pages, {
        "stufe": stufe,
        "blocked": stufe == 1,
        "partial": stufe == 2,
        "complete": stufe == 3,
        "pages_found": list(pages.keys()),
        "total_chars": total_chars,
    }


# ══════════════════════════════════════════════════════════
# NAP & FAQ EXTRAKTION
# ══════════════════════════════════════════════════════════

def extract_nap(pages):
    """Extrahiert NAP aus gecrawlten Seiten. Nur was tatsächlich im Text steht."""
    ordered = []
    for prio in ["kontakt", "contact", "impressum", "startseite"]:
        for name, data in pages.items():
            if prio in name.lower():
                ordered.append(data.get("text", ""))
    for data in pages.values():
        ordered.append(data.get("text", ""))
    full = " ".join(ordered)

    nap = {"telefon": None, "email": None, "adresse": None, "crawl_seiten": list(pages.keys())}

    tel = re.search(r'(\+43[\s\-./\d]{6,16}|\+49[\s\-./\d]{6,16}|\+41[\s\-./\d]{6,16}|0\d{3,5}[\s\-./\d]{4,12})', full)
    if tel:
        nap["telefon"] = tel.group().strip()

    mail = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}', full)
    if mail:
        nap["email"] = mail.group().strip()

    addr = re.search(
        r'[A-Za-z\u00c0-\u017e]+(?:stra\u00dfe|gasse|weg|platz|allee|ring|str\.|g\.)'
        r'\s*\d{1,4}[a-zA-Z]?,?\s*\d{4,5}\s+[A-Za-z\u00c0-\u017e][\w\u00c0-\u017e\-]*',
        full, re.IGNORECASE
    )
    if addr:
        nap["adresse"] = addr.group().strip()

    return nap


def extract_faq(pages):
    """Extrahiert FAQ-Fragen aus gecrawlten Seiten. Nur was tatsächlich im Text steht."""
    items = []
    source = None

    for name, data in pages.items():
        text = data.get("text", "")
        headings = data.get("headings", [])
        is_faq = "faq" in name.lower()

        for h in headings:
            clean = re.sub(r'\[H\d\]\s*|\[SPAN\]\s*', '', h).strip()
            if clean.endswith("?") and 15 <= len(clean) <= 200 and clean not in items:
                items.append(clean)
                if not source:
                    source = name

        if is_faq and text:
            for s in re.split(r'(?<=[.!])\s+', text):
                s = s.strip()
                if s.endswith("?") and 20 <= len(s) <= 200 and s not in items:
                    items.append(s)
                    if not source:
                        source = name

    seen, deduped = set(), []
    for q in items:
        if q not in seen:
            seen.add(q)
            deduped.append(q)

    return {
        "fragen": deduped[:20],
        "anzahl": len(deduped[:20]),
        "quelle": source,
        "faq_seite_gecrawlt": any("faq" in p.lower() for p in pages.keys()),
    }


# ══════════════════════════════════════════════════════════
# FORMAT FÜR PROMPT
# ══════════════════════════════════════════════════════════

def format_for_prompt(pages):
    if not pages:
        return "Keine Website-Inhalte konnten geladen werden."
    out = []
    for name, data in pages.items():
        out.append(f"\n=== SEITE: {name.upper()} ===")
        headings = data.get("headings", [])
        faq_h = [h for h in headings if h.startswith("[SPAN]") and "?" in h]
        normal_h = [h for h in headings if not h.startswith("[SPAN]")]
        if normal_h:
            out.append("UEBERSCHRIFTEN: " + " | ".join(normal_h[:10]))
        if faq_h:
            out.append(f"FAQ-SEKTION ({len(faq_h)} Fragen):")
            for fh in faq_h:
                out.append("  " + fh.replace("[SPAN] ", "- "))
        out.append("TEXT: " + data["text"][:2500])
    return "\n".join(out)


# ══════════════════════════════════════════════════════════
# API HELPER
# ══════════════════════════════════════════════════════════

def call_api(client, model, max_tokens, messages):
    """API-Call mit Retry und Haiku-Fallback bei OverloadedError."""
    fallback = "claude-haiku-4-5-20251001"
    for current_model in ([model, fallback] if model != fallback else [model]):
        for attempt in range(3):
            try:
                return client.messages.create(
                    model=current_model,
                    max_tokens=max_tokens,
                    messages=messages
                )
            except Exception as e:
                if "Overloaded" in type(e).__name__:
                    if attempt < 2:
                        wait = 15 * (attempt + 1)
                        st.warning(f"⏳ API ausgelastet ({current_model}) — warte {wait}s... (Versuch {attempt+2}/3)")
                        time.sleep(wait)
                    else:
                        if current_model != fallback:
                            st.warning(f"⚠️ {current_model} nicht erreichbar — wechsle auf Fallback-Modell...")
                        break
                else:
                    raise
    raise RuntimeError("API nach allen Versuchen nicht erreichbar. Bitte in 1-2 Minuten erneut versuchen.")


def parse_json(raw):
    """Robuste JSON-Extraktion aus API-Antwort."""
    text = raw.strip()

    # Versuch 1: direkt
    try:
        return json.loads(text)
    except Exception:
        pass

    # Versuch 2: ```json Block
    if "```" in text:
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                try:
                    return json.loads(part)
                except Exception:
                    pass

    # Versuch 3: { ... } extrahieren
    start, end = text.find("{"), text.rfind("}") + 1
    if start >= 0 and end > start:
        candidate = text[start:end]
        try:
            return json.loads(candidate)
        except Exception:
            pass
        # Versuch 4: trailing commas + single quotes bereinigen
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        candidate = re.sub(r"'([^']*)'(\s*:)", r'"\1"\2', candidate)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return {}


def clamp_score(raw):
    """Score auf 0–10 (int) normalisieren — alle Formate."""
    try:
        if isinstance(raw, str):
            raw = raw.split("/")[0].strip()
        return max(0, min(10, int(round(float(raw)))))
    except Exception:
        return 0


# ══════════════════════════════════════════════════════════
# HAUPTANALYSE
# ══════════════════════════════════════════════════════════

def run_analysis(hotel_name, location, url, business_type):
    try:
        api_key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        st.error("❌ API-Key nicht konfiguriert (ANTHROPIC_API_KEY in Streamlit Secrets fehlt).")
        return None

    # ── CRAWLING ──
    with st.spinner("🔍 Website wird gecrawlt..."):
        pages, crawl_status = crawl_website(url)
        website_content = format_for_prompt(pages)
        pages_found = crawl_status["pages_found"]

    # Geblockt
    if crawl_status["blocked"]:
        st.error("❌ **Analyse nicht möglich — Website blockiert automatische Zugriffe**")
        st.markdown(f"""
<div style="background:#1a1a2e;border:2px solid #e74c3c;border-radius:12px;padding:24px;margin:16px 0;">
    <h3 style="color:#e74c3c;margin-top:0;">🚫 Server-Blockierung erkannt</h3>
    <p style="color:#ecf0f1;">Die Website <strong>{url}</strong> blockiert automatische Zugriffe (Bot-Schutz aktiv).<br>
    Eine GEO-Readiness-Analyse ist ohne lesbare Website-Inhalte nicht möglich.</p>
    <hr style="border-color:#444;">
    <p style="color:#ecf0f1;font-size:14px;">
    Aktuelle Website-Inhalte (Angebote, FAQs, USPs) können von Crawlern nicht gelesen werden.<br>
    Suchmaschinen-Crawler erhalten möglicherweise keinen Zugriff auf aktuelle Seiteninhalte.<br>
    Dies ist ein technisches Problem unabhängig von der inhaltlichen Qualität der Website.
    </p>
    <h4 style="color:#27ae60;">💡 Empfohlener Kontakttext:</h4>
    <em style="color:#bdc3c7;font-size:13px;">
    "Guten Tag, bei einer technischen Überprüfung Ihrer Website haben wir festgestellt,
    dass der Server von {hotel_name} automatische Zugriffe blockiert.
    Das bedeutet: Aktuelle Inhalte Ihrer Website können von Suchmaschinen-Crawlern
    nicht zuverlässig gelesen werden.
    Gerne zeige ich Ihnen in einem kurzen Gespräch, was das konkret bedeutet."
    </em>
</div>
""", unsafe_allow_html=True)
        return None

    # Eingeschränkte Datenbasis
    if crawl_status["partial"]:
        st.warning(
            f"⚠️ **Eingeschränkte Datenbasis** — {len(pages_found)} Seite(n) geladen "
            f"({', '.join(pages_found)}). Faktoren die Unterseiten benötigen können eingeschränkt sein."
        )

    # ── ANALYSE-PROMPT ──
    has_faq = "FAQ-FRAGEN" in website_content or "FAQ-SEKTION" in website_content
    has_headings = "UEBERSCHRIFTEN:" in website_content
    has_nap = any(kw in website_content for kw in ["Tel", "+43", "+49", "+41", "Adresse", "Straße", "Gasse", "@"])

    datenverfuegbarkeit = f"""
DATENVERFUEGBARKEIT:
- Seiten gecrawlt: {', '.join(pages_found)}
- FAQ-Daten: {"JA" if has_faq else "NEIN"}
- Ueberschriften: {"JA" if has_headings else "NEIN"}
- NAP-Daten: {"JA" if has_nap else "NEIN"}

ABSOLUTE REGELN:
1. Score = 0 + Kommentar "Keine Daten verfuegbar" wenn Datenbasis fehlt
2. Nur bewerten was EXPLIZIT im gecrawlten Text steht — keine Annahmen
3. Quick Wins NUR fuer Faktoren mit Score > 0
4. NAP: nur vorhanden wenn Adresse UND Telefon im gecrawlten Text sichtbar
"""

    analyse_prompt = f"""Du bist GEO-Optimierungs-Experte fuer Tourismus-Websites im DACH-Raum.

Betrieb: {hotel_name} | Ort: {location} | Typ: {business_type}
Gecrawlte Seiten ({len(pages_found)}): {', '.join(pages_found)}
{datenverfuegbarkeit}

GECRAWLTE INHALTE:
{website_content[:15000]}

Bewerte 5 Faktoren (Score 0-10, ganze Zahl):
1. FAQ-Sektion: Strukturierte Fragen & Antworten vorhanden?
2. H1-Optimierung: Ortsbezug und USP in Hauptueberschriften?
3. Lokale Keywords: Region, Bundesland, Aktivitaeten, Saison?
4. NAP-Konsistenz: Name, Adresse, Telefon vollstaendig & einheitlich?
5. USP-Klarheit: Echte Alleinstellungsmerkmale kommuniziert?

USP-Kategorien:
- Lage-USP (direkter See, einzigartiger Ausblick) = USP fuer alle Kategorien
- Infrastruktur: Appartement mit Sauna = USP; 3-4 Sterne Hotel mit Sauna = Standard
- Thematisch: Kinderbetreuung, Fuehrungen, Sportprogramm = starker USP

Antworte NUR als valides JSON (keine Kommentare, kein Markdown):
{{
  "faktoren": [
    {{"name": "FAQ-Sektion", "score": 0, "kommentar": "<1 Satz>"}},
    {{"name": "H1-Optimierung", "score": 0, "kommentar": "<1 Satz>"}},
    {{"name": "Lokale Keywords", "score": 0, "kommentar": "<1 Satz>"}},
    {{"name": "NAP-Konsistenz", "score": 0, "kommentar": "<1 Satz>"}},
    {{"name": "USP-Klarheit", "score": 0, "kommentar": "<1 Satz>"}}
  ],
  "quickwins": [
    {{"prioritaet": "sofort", "massnahme": "<Massnahme>", "impact": "<Effekt>"}},
    {{"prioritaet": "sofort", "massnahme": "<Massnahme>", "impact": "<Effekt>"}},
    {{"prioritaet": "kurz", "massnahme": "<Massnahme>", "impact": "<Effekt>"}},
    {{"prioritaet": "kurz", "massnahme": "<Massnahme>", "impact": "<Effekt>"}},
    {{"prioritaet": "mittel", "massnahme": "<Massnahme>", "impact": "<Effekt>"}}
  ],
  "zusammenfassung": "<2-3 Saetze Gesamtbewertung>"
}}"""

    client = anthropic.Anthropic(api_key=api_key)

    # ── API CALL 1: Analyse ──
    with st.spinner("📊 Analysiere Website-Inhalte..."):
        try:
            msg1 = call_api(client, "claude-opus-4-5", 2000,
                            [{"role": "user", "content": analyse_prompt}])
        except RuntimeError as e:
            st.error(f"❌ {e}")
            return None

    result = parse_json(msg1.content[0].text)

    # ── SERVERSEITIGE VALIDIERUNG ──
    if not result or "faktoren" not in result:
        st.error("❌ Analyse lieferte kein verwertbares Ergebnis. Bitte erneut versuchen.")
        return None

    faktoren = result.get("faktoren", [])
    if len(faktoren) != 5:
        st.error(f"❌ Analyse unvollständig ({len(faktoren)}/5 Faktoren). Bitte erneut versuchen.")
        return None

    # Scores clampen — serverseitig, unabhängig von Claude-Output
    for f in faktoren:
        f["score"] = clamp_score(f.get("score", 0))

    # Gesamtscore immer selbst berechnen
    result["gesamtscore"] = sum(f["score"] for f in faktoren)

    # Quickwins validieren
    raw_qw = result.get("quickwins", [])
    result["quickwins"] = [
        w for w in raw_qw
        if isinstance(w, dict)
        and str(w.get("prioritaet", "")).strip() in ("sofort", "kurz", "mittel")
        and str(w.get("massnahme", "")).strip()
        and str(w.get("impact", "")).strip()
    ]

    # ── API CALL 2: Optimierungspaket ──
    paket_prompt = f"""Erstelle ein GEO-Optimierungspaket fuer diesen Tourismusbetrieb.

Betrieb: {hotel_name} | Ort: {location} | Typ: {business_type}

GECRAWLTE WEBSITE-INHALTE:
{website_content[:12000]}

WICHTIG: Nur Fakten aus gecrawlten Inhalten — keine Erfindungen.

Antworte NUR als valides JSON (kein Markdown):
{{
  "faq": [{{"frage": "<Frage>", "antwort": "<Antwort>"}}],
  "h1_neu": "<Optimierter H1-Titel max 70 Zeichen>",
  "h1_sub": "<Subheadline max 120 Zeichen>",
  "usp_box": [{{"emoji": "<>", "titel": "<>", "text": "<1 Satz>"}}],
  "keywords": ["<kw1>", "<kw2>"],
  "google_business": "<Google Business Text max 750 Zeichen>",
  "meta_start": "<Meta-Description Startseite max 155 Zeichen>",
  "meta_zimmer": "<Meta-Description Zimmer max 155 Zeichen>",
  "meta_preise": "<Meta-Description Preise max 155 Zeichen>",
  "ueber_uns": "<Ueber uns Text 250-300 Woerter>"
}}"""

    with st.spinner("📦 Erstelle Optimierungspaket..."):
        try:
            msg2 = call_api(client, "claude-haiku-4-5-20251001", 3000,
                            [{"role": "user", "content": paket_prompt}])
            paket = parse_json(msg2.content[0].text)
        except RuntimeError as e:
            st.warning(f"⚠️ Optimierungspaket nicht verfügbar: {e}")
            paket = {}
        except Exception:
            paket = {}

    if not paket:
        st.warning("⚠️ Optimierungspaket konnte nicht erstellt werden — Analyse-Report ist verfügbar.")

    # ── RESULT ZUSAMMENSTELLEN ──
    result["paket"] = paket
    result["hotelName"] = hotel_name
    result["location"] = location
    result["url"] = url
    result["type"] = business_type
    result["email"] = ""
    result["date"] = datetime.date.today().strftime("%d.%m.%Y")
    result["nap"] = extract_nap(pages)
    result["faq"] = extract_faq(pages)

    return result


# ══════════════════════════════════════════════════════════
# PDF GENERATOR
# ══════════════════════════════════════════════════════════

def sanitize(text):
    if not text:
        return ""
    replacements = {
        '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u2022': '*',
        '\u00e4': 'ae', '\u00f6': 'oe', '\u00fc': 'ue',
        '\u00c4': 'Ae', '\u00d6': 'Oe', '\u00dc': 'Ue',
        '\u00df': 'ss', '\u00e9': 'e', '\u00e8': 'e', '\u00e0': 'a',
        '\u2192': '->', '\u00b0': 'Grad', '\u20ac': 'EUR',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', errors='replace').decode('latin-1')


def generate_pdf(r):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_fill_color(26, 35, 50)
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 10)
    pdf.cell(0, 10, "GEO-Readiness Report", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(201, 168, 76)
    pdf.set_x(15)
    pdf.cell(0, 8, sanitize(r["hotelName"]), ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(180, 190, 200)
    pdf.set_x(15)
    pdf.cell(0, 6, sanitize(f"{r['location']} | {r['type']} | {r['date']}"), ln=True)

    # Score Box
    score = r["gesamtscore"]
    pdf.set_fill_color(61, 122, 94)
    pdf.rect(158, 8, 38, 28, 'F')
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(158, 12)
    pdf.cell(38, 12, str(score), align="C", ln=False)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(158, 26)
    pdf.cell(38, 6, "von 50 Punkten", align="C", ln=True)
    pdf.ln(18)

    # Zusammenfassung
    pdf.set_fill_color(240, 237, 232)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_x(15)
    pdf.multi_cell(180, 6, sanitize(r.get("zusammenfassung", "")), fill=True)
    pdf.ln(8)

    # Faktoren
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(26, 35, 50)
    pdf.set_x(15)
    pdf.cell(0, 8, "Faktor-Analyse", ln=True)
    pdf.ln(2)

    for f in r["faktoren"]:
        s = clamp_score(f.get("score", 0))
        rc, gc, bc = (39, 174, 96) if s >= 8 else ((230, 126, 34) if s >= 5 else (192, 57, 43))
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(26, 35, 50)
        pdf.set_x(15)
        pdf.cell(140, 6, sanitize(f["name"]))
        pdf.set_text_color(rc, gc, bc)
        pdf.cell(0, 6, f"{s}/10", ln=True)
        pdf.set_fill_color(220, 220, 220)
        pdf.rect(15, pdf.get_y(), 80, 3, 'F')
        pdf.set_fill_color(rc, gc, bc)
        pdf.rect(15, pdf.get_y(), (s / 10) * 80, 3, 'F')
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 110, 120)
        pdf.set_x(15)
        pdf.multi_cell(180, 5, sanitize(f.get("kommentar", "")))
        pdf.ln(3)

    # Quick Wins
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(26, 35, 50)
    pdf.set_x(15)
    pdf.cell(0, 8, "Quick Wins", ln=True)
    pdf.ln(2)

    prio_colors = {"sofort": (192, 57, 43), "kurz": (230, 126, 34), "mittel": (39, 174, 96)}
    prio_labels = {"sofort": "SOFORT", "kurz": "KURZFRISTIG", "mittel": "MITTELFRISTIG"}

    for w in r.get("quickwins", []):
        prio = str(w.get("prioritaet", "mittel")).strip()
        if prio not in prio_colors:
            prio = "mittel"
        rc, gc, bc = prio_colors[prio]
        pdf.set_fill_color(rc, gc, bc)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_x(15)
        pdf.cell(30, 6, prio_labels[prio], fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(26, 35, 50)
        pdf.set_x(48)
        pdf.multi_cell(157, 6, sanitize(str(w.get("massnahme", ""))))
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(61, 122, 94)
        pdf.set_x(48)
        pdf.cell(0, 5, sanitize("-> " + str(w.get("impact", ""))), ln=True)
        pdf.ln(2)

    # Footer
    pdf.ln(6)
    y = pdf.get_y()
    pdf.set_fill_color(26, 35, 50)
    pdf.rect(15, y, 180, 28, 'F')
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(201, 168, 76)
    pdf.set_xy(20, y + 5)
    pdf.cell(0, 7, "Detailberatung anfragen")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(200, 210, 220)
    pdf.set_xy(20, y + 13)
    pdf.cell(0, 5, "kontakt@gernot-riedel.com  |  +43 676 7237811  |  gernot-riedel.com")

    return bytes(pdf.output())


# ══════════════════════════════════════════════════════════
# UI — FORMULAR
# ══════════════════════════════════════════════════════════

st.markdown("### Website-Analyse starten")

with st.form("geo_form"):
    col1, col2 = st.columns(2)
    with col1:
        hotel_name = st.text_input("Name des Betriebs", placeholder="z.B. Hotel Alpenblick")
        business_type = st.selectbox("Betriebsart", [
            "Hotel (3-4 Sterne)", "Hotel (5 Sterne)", "Pension / Gasthof",
            "Ferienwohnung / Appartement", "Ferienhaus", "Tourismusverband / DMO"
        ])
    with col2:
        location = st.text_input("Ort / Region", placeholder="z.B. Zell am See, Salzburg")
        contact_email = st.text_input("Ihre E-Mail (für Report)", placeholder="name@hotel.at")
    website_url = st.text_input("Website-URL", placeholder="https://www.ihr-hotel.at")
    submitted = st.form_submit_button("🔍 Jetzt Website analysieren")

# ══════════════════════════════════════════════════════════
# ANALYSE AUSFÜHREN
# ══════════════════════════════════════════════════════════

if submitted:
    if not hotel_name or not website_url or not contact_email:
        st.error("Bitte Betriebsname, Website-URL und E-Mail angeben.")
    else:
        st.session_state.anfrage_gesendet = False
        result = run_analysis(hotel_name, location, website_url, business_type)
        if result:
            result["email"] = contact_email
            st.session_state.result = result
            st.session_state.leads.append({
                "Betrieb": hotel_name,
                "Ort": location,
                "E-Mail": contact_email,
                "Score": result["gesamtscore"],
                "Typ": business_type,
                "URL": website_url,
                "Datum": result["date"],
                "Zusammenfassung": result.get("zusammenfassung", "")
            })


# ══════════════════════════════════════════════════════════
# UI — ERGEBNISSE
# ══════════════════════════════════════════════════════════

if st.session_state.result:
    r = st.session_state.result
    score = r["gesamtscore"]

    st.markdown("---")
    st.markdown(f"## 📊 Analyse: {r['hotelName']}")
    st.caption(f"{r['location']} · {r['type']} · {r['date']}")

    if score >= 40:
        score_class, score_label = "score-excellent", "Ausgezeichnet"
    elif score >= 28:
        score_class, score_label = "score-good", "Gut"
    elif score >= 16:
        score_class, score_label = "score-poor", "Verbesserungsbedarf"
    else:
        score_class, score_label = "score-critical", "Kritisch"

    col_score, col_summary = st.columns([1, 2])
    with col_score:
        st.markdown(f"""
        <div class="score-box">
            <div class="score-number {score_class}">{score}</div>
            <div style="color:rgba(255,255,255,0.6);font-size:13px;margin-top:4px;">von 50 Punkten</div>
            <div style="color:#c9a84c;font-weight:700;margin-top:8px;">{score_label}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_summary:
        st.info(r.get("zusammenfassung", ""))

    # Faktoren
    st.markdown("### Faktor-Analyse")
    for f in r["faktoren"]:
        s = clamp_score(f.get("score", 0))
        bar_color = "#27ae60" if s >= 8 else "#e67e22" if s >= 5 else "#c0392b"
        col_f1, col_f2 = st.columns([4, 1])
        with col_f1:
            st.markdown(f"**{f['name']}**")
            st.progress(s / 10)
            st.caption(f.get("kommentar", ""))
        with col_f2:
            st.markdown(
                f"<div style='font-size:28px;font-weight:800;color:{bar_color};"
                f"text-align:center;padding-top:8px'>{s}"
                f"<span style='font-size:14px;color:#aaa'>/10</span></div>",
                unsafe_allow_html=True
            )
        st.markdown("---")

    # Quick Wins
    st.markdown("### ⚡ Quick Wins")
    quickwins = r.get("quickwins", [])
    if not quickwins:
        st.info("Keine Quick Wins verfügbar — zu wenig Datenbasis für konkrete Empfehlungen.")
    for w in quickwins:
        try:
            prio = str(w.get("prioritaet", "mittel")).lower().strip()
            if prio not in ("sofort", "kurz", "mittel"):
                prio = "mittel"
            massnahme = str(w.get("massnahme", "")).strip()
            impact = str(w.get("impact", "")).strip()
            if not massnahme:
                continue
            label = {"sofort": "🔴 SOFORT", "kurz": "🟠 KURZFRISTIG", "mittel": "🟢 MITTELFRISTIG"}[prio]
            st.markdown(f"""
        <div class="win-{prio}">
            <strong>{label}</strong> &nbsp; {massnahme}<br>
            <span style="color:#3d7a5e;font-size:13px;">→ {impact}</span>
        </div>
        """, unsafe_allow_html=True)
        except Exception:
            continue

    # NAP & FAQ
    st.markdown("### 🔍 NAP & FAQ Detailcheck")
    nap = r.get("nap", {})
    faq = r.get("faq", {})
    col_nap, col_faq = st.columns(2)

    with col_nap:
        st.markdown("#### 📍 NAP-Daten")
        seiten = nap.get("crawl_seiten", [])
        st.caption(f"Gecrawlte Seiten: {', '.join(seiten)}" if seiten else "Keine Seiten gecrawlt.")

        if nap.get("telefon"):
            st.success(f"✅ **Telefon:** {nap['telefon']}")
        else:
            st.error("❌ **Telefon:** Nicht im gecrawlten Text gefunden.")
            st.caption("Mögliche Ursachen: Bild/Grafik, JavaScript-gerendert, oder fehlend.")

        if nap.get("email"):
            st.success(f"✅ **E-Mail:** {nap['email']}")
        else:
            st.warning("⚠️ **E-Mail:** Nicht im gecrawlten Text gefunden.")

        if nap.get("adresse"):
            st.success(f"✅ **Adresse:** {nap['adresse']}")
        else:
            st.error("❌ **Adresse:** Nicht im gecrawlten Text gefunden.")
            st.caption("Mögliche Ursachen: Kontaktseite nicht gecrawlt, Karte/Bild, JavaScript.")

        if not nap.get("telefon") and not nap.get("adresse"):
            st.info("ℹ️ Ohne lesbare NAP-Daten sind KI-Suchsysteme auf externe Quellen angewiesen (Google Business, Booking.com) — mit Risiko veralteter Daten.")

    with col_faq:
        st.markdown("#### ❓ FAQ-Analyse")
        faq_gecrawlt = faq.get("faq_seite_gecrawlt", False)
        faq_anzahl = faq.get("anzahl", 0)
        faq_quelle = faq.get("quelle", "")

        st.caption(
            f"FAQ-Seite gecrawlt. Quelle: {faq_quelle or 'unbekannt'}"
            if faq_gecrawlt else "Keine dedizierte FAQ-Seite gefunden."
        )

        if faq_anzahl > 0:
            st.success(f"✅ **{faq_anzahl} FAQ-Fragen gefunden** (Quelle: {faq_quelle})")
            with st.expander("Gefundene Fragen anzeigen"):
                for i, frage in enumerate(faq.get("fragen", []), 1):
                    st.write(f"{i}. {frage}")
        else:
            st.error("❌ **Keine FAQ-Fragen gefunden.**")
            if faq_gecrawlt:
                st.caption("FAQ-Seite gecrawlt, aber keine Fragen erkannt — möglicherweise JavaScript-gerendert.")
            else:
                st.caption("Keine FAQ-Seite in Sitemap oder Links gefunden.")
            st.info("ℹ️ Fehlende FAQs reduzieren die Wahrscheinlichkeit, in KI-generierten Antworten zu erscheinen.")

    st.markdown("---")

    # PDF
    st.markdown("### 📄 Report herunterladen")
    pdf_bytes = generate_pdf(r)
    filename = f"GEO_Report_{r['hotelName'].replace(' ','_')}_{r['date'].replace('.','')}.pdf"
    st.download_button(
        label="📥 PDF-Report herunterladen",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True
    )

    # Paket Teaser
    paket = r.get("paket", {})
    if paket:
        st.markdown("---")
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a2332,#2d4a3e);padding:28px;border-radius:8px;">
            <h3 style="color:#c9a84c;margin:0 0 12px 0">📦 Ihr persönliches GEO-Optimierungspaket ist fertig</h3>
            <p style="color:rgba(255,255,255,0.9);margin:0 0 16px 0;font-size:15px;line-height:1.7">
            Basierend auf dieser Analyse wurde für Ihren Betrieb ein
            <strong style="color:white">vollständiges Optimierungspaket</strong> erstellt.</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700">LIEFERUNG 1</div>
                    <div style="color:white;font-size:14px">📋 10 FAQ-Fragen + Antworten</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700">LIEFERUNG 2</div>
                    <div style="color:white;font-size:14px">🏷️ H1-Titel + Subheadline neu</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700">LIEFERUNG 3</div>
                    <div style="color:white;font-size:14px">⭐ USP-Box mit 4 Alleinstellungsmerkmalen</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700">LIEFERUNG 4</div>
                    <div style="color:white;font-size:14px">🔍 20 lokale Keywords</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700">LIEFERUNG 5</div>
                    <div style="color:white;font-size:14px">📍 Google Business Profil-Text</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700">LIEFERUNG 6</div>
                    <div style="color:white;font-size:14px">🔗 3 Meta-Descriptions</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;border-left:3px solid #c9a84c;grid-column:span 2">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700">LIEFERUNG 7</div>
                    <div style="color:white;font-size:14px">📖 "Über uns" komplett neu (KI-optimiert)</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # CTA
    st.markdown("""
    <div class="cta-box">
        <h3 style="color:#c9a84c;margin:0 0 8px 0">🚀 GEO-Optimierungspaket Professional — € 149</h3>
        <p style="color:rgba(255,255,255,0.85);margin:0 0 6px 0;font-size:15px">
        Alle 7 Lieferungen als fertiges Dokument:</p>
        <p style="color:rgba(255,255,255,0.75);margin:0 0 16px 0;font-size:13px">
        ✅ 10 FAQ-Fragen &nbsp;|&nbsp; ✅ H1-Titel &nbsp;|&nbsp; ✅ USP-Box &nbsp;|&nbsp;
        ✅ 20 Keywords &nbsp;|&nbsp; ✅ Google Business &nbsp;|&nbsp;
        ✅ 3 Meta-Descriptions &nbsp;|&nbsp; ✅ Über uns neu
        </p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.anfrage_gesendet:
        if st.button("📩 Ja, ich möchte das GEO-Optimierungspaket für € 149",
                     use_container_width=True, type="primary"):
            with st.spinner("Ihre Anfrage wird verarbeitet..."):
                try:
                    webhook_url = st.secrets.get("ZAPIER_WEBHOOK_URL", "")
                    payload = {
                        "betrieb": r["hotelName"],
                        "ort": r["location"],
                        "email": r["email"],
                        "website": r["url"],
                        "typ": r["type"],
                        "score": r["gesamtscore"],
                        "datum": r["date"],
                        "zusammenfassung": r.get("zusammenfassung", ""),
                        "faktoren": json.dumps(r["faktoren"], ensure_ascii=False),
                        "quickwins": json.dumps(r["quickwins"], ensure_ascii=False),
                        "produkt": "GEO-Optimierungspaket",
                        "preis": "149 EUR"
                    }
                    if webhook_url:
                        requests.post(webhook_url, json=payload, timeout=10)
                    st.session_state.anfrage_gesendet = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Senden: {e}")
    else:
        st.success("✅ Ihre Anfrage ist eingegangen. Sie erhalten innerhalb von 24h Ihre Optimierungstexte.")
        st.info("📧 kontakt@gernot-riedel.com | 📞 +43 676 7237811")

    # Upsell
    st.markdown("""
    <div style="background:#f5f0e8;border:1px solid #e8e3da;border-left:4px solid #c9a84c;
                padding:20px 24px;border-radius:4px;margin-top:16px">
        <h4 style="margin:0 0 8px 0;color:#1a2332">📊 Noch mehr Potenzial: ReviewRadar 2.0</h4>
        <p style="margin:0 0 8px 0;color:#4a5568;font-size:14px">
        Bewertungsanalyse von Booking.com, Google, TripAdvisor & HolidayCheck —
        mit klarem Aktionsplan und ROI-Kalkulation.</p>
        <p style="margin:0;font-size:14px">
        <strong style="color:#c9a84c">ab € 149</strong> &nbsp;—&nbsp;
        <a href="https://gernot-riedel.com/hotelbewertungen-analyse-mehr-umsatz-direktbuchungen-reviewradar/"
        target="_blank" style="color:#3d7a5e;font-weight:600">Alle Pakete & Details →</a>
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── LEADS ADMIN ──
st.markdown("---")
with st.expander("📊 Gesammelte Leads anzeigen (Admin)", expanded=False):
    if st.session_state.leads:
        import pandas as pd
        df = pd.DataFrame(st.session_state.leads)
        st.dataframe(df, use_container_width=True)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 Leads als CSV exportieren",
            data=csv_buffer.getvalue().encode("utf-8-sig"),
            file_name=f"geo_leads_{datetime.date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("Noch keine Leads gesammelt.")

# ── FOOTER ──
st.markdown("""
<div class="footer-bar">
    <strong style="color:#c9a84c">Gernot Riedel Tourism Consulting</strong> &nbsp;|&nbsp;
    TÜV-zertifizierter KI-Trainer &nbsp;|&nbsp;
    kontakt@gernot-riedel.com &nbsp;|&nbsp;
    +43 676 7237811
</div>
""", unsafe_allow_html=True)

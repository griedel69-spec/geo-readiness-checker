import streamlit as st
import anthropic
import json
import csv
import io
import datetime
from fpdf import FPDF

# ─── PAGE CONFIG ───
st.set_page_config(
    page_title="GEO-Readiness Checker | Gernot Riedel Tourism Consulting",
    page_icon="🏔",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── CUSTOM CSS ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.main-header {
    background: linear-gradient(135deg, #1a2332 0%, #2d4a3e 100%);
    padding: 36px 32px 28px;
    border-radius: 8px;
    margin-bottom: 28px;
    position: relative;
}

.main-header h1 {
    color: #ffffff;
    font-size: 32px;
    font-weight: 700;
    margin: 0 0 8px 0;
    line-height: 1.2;
}

.main-header h1 span { color: #c9a84c; }

.main-header p {
    color: rgba(255,255,255,0.7);
    font-size: 15px;
    margin: 0;
    line-height: 1.6;
}

.brand-tag {
    display: inline-block;
    background: rgba(201,168,76,0.2);
    border: 1px solid rgba(201,168,76,0.4);
    color: #e8c97a;
    padding: 4px 12px;
    border-radius: 2px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 16px;
}

.score-box {
    background: linear-gradient(135deg, #1a2332, #2d4a3e);
    border-radius: 8px;
    padding: 24px;
    text-align: center;
    color: white;
}

.score-number {
    font-size: 56px;
    font-weight: 800;
    line-height: 1;
}

.score-excellent { color: #7ab89a; }
.score-good { color: #c9a84c; }
.score-poor { color: #e67e22; }
.score-critical { color: #c0392b; }

.factor-card {
    background: #f8f6f2;
    border-left: 4px solid #3d7a5e;
    padding: 16px 20px;
    border-radius: 0 6px 6px 0;
    margin-bottom: 12px;
}

.win-sofort { background: #fde8e8; border-left: 4px solid #c0392b; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 8px; }
.win-kurz   { background: #fef3e2; border-left: 4px solid #e67e22; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 8px; }
.win-mittel { background: #eaf5f0; border-left: 4px solid #27ae60; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 8px; }

.cta-box {
    background: linear-gradient(135deg, #1a2332 0%, #2d4a3e 100%);
    border-radius: 8px;
    padding: 28px 32px;
    color: white;
    margin-top: 24px;
}

.footer-bar {
    background: #1a2332;
    color: rgba(255,255,255,0.5);
    padding: 16px 24px;
    border-radius: 8px;
    text-align: center;
    font-size: 12px;
    margin-top: 40px;
}

div[data-testid="stForm"] {
    background: white;
    padding: 24px;
    border-radius: 8px;
    border: 1px solid #e8e3da;
}

.stButton > button {
    background: #3d7a5e !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    padding: 14px 28px !important;
    border-radius: 4px !important;
    border: none !important;
    width: 100% !important;
}

.stButton > button:hover {
    background: #2d4a3e !important;
}
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
if "show_leads" not in st.session_state:
    st.session_state.show_leads = False

# ─── GET API KEY ───
def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except:
        return None

# ─── MULTI-PAGE CRAWLER ───
def crawl_website(base_url):
    """Crawlt die wichtigsten Seiten einer Hotel-Website via Sitemap + direkte FAQ-Suche."""
    import requests
    import re
    from html.parser import HTMLParser
    from urllib.parse import urljoin, urlparse

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
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GEO-Checker/1.0)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "de-AT,de;q=0.9"
    }

    faq_patterns = ["faq", "haeufig", "faq.html", "faq.php"]
    content_patterns = [
        "zimmer", "rooms", "appartement", "wohnung", "suite",
        "ueber", "about", "uns", "lage", "anreise",
        "wellness", "spa", "angebot", "preise",
        "aktivitaet", "sommer", "winter", "service",
        "gut-zu-wissen", "buchungsinformation"
    ]

    pages_content = {}

    def fetch_page(url):
        try:
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                html = resp.text
                parser = TextExtractor()
                parser.feed(html)
                text = parser.get_text()

                faq_spans = re.findall(r'<span>([^<]{15,200}\?)</span>', html)
                if faq_spans:
                    text = text + "\n\nFAQ-FRAGEN AUF DIESER SEITE:\n" + "\n".join(f"- {q}" for q in faq_spans[:30])

                return text[:4000], parser.headings[:20], parser.links
        except Exception:
            pass
        return None, [], []

    def get_urls_from_sitemap(base):
        found_urls = []
        sitemap_candidates = [
            base + "/sitemap.xml",
            base + "/sitemap_index.xml",
            base + "/sitemap.php",
        ]
        for sitemap_url in sitemap_candidates:
            try:
                r = requests.get(sitemap_url, headers=headers, timeout=8)
                if r.status_code == 200:
                    urls = re.findall(r'<loc>(https?://[^<]+)</loc>', r.text)
                    for u in urls:
                        if base_domain in u and u not in found_urls:
                            found_urls.append(u)
                    if found_urls:
                        break
            except Exception:
                pass
        return found_urls

    text, headings, links = fetch_page(base_url)
    if text:
        pages_content["Startseite"] = {"text": text, "headings": headings}

    sitemap_urls = get_urls_from_sitemap(base_url)

    faq_crawled = False
    faq_candidates = []

    de_faq = []
    other_faq = []
    for u in sitemap_urls:
        path_lower = urlparse(u).path.lower()
        if any(p in path_lower for p in faq_patterns):
            if "/de/" in path_lower or path_lower.endswith("/de"):
                de_faq.append(u)
            elif "/en/" not in path_lower and "/fr/" not in path_lower:
                other_faq.append(u)
    faq_candidates = de_faq + other_faq

    for link in links:
        full_url = urljoin(base_url, link).rstrip("/")
        path_lower = urlparse(full_url).path.lower()
        if base_domain in full_url and any(p in path_lower for p in faq_patterns):
            if full_url not in faq_candidates:
                faq_candidates.append(full_url)

    for faq_url in faq_candidates[:2]:
        t, h, _ = fetch_page(faq_url)
        if t:
            pages_content["FAQ-Seite"] = {"text": t, "headings": h}
            faq_crawled = True
            break

    seen_urls = {base_url} | set(faq_candidates)
    priority_urls = []

    exclude_patterns = ["datenschutz", "cookie", "impressum", "agb", "privacy",
                       "sitemap", "robots", ".xml", ".pdf", "login", "admin"]
    url_pool = sitemap_urls if sitemap_urls else [urljoin(base_url, l) for l in links]

    for u in url_pool:
        u_clean = u.rstrip("/")
        if u_clean in seen_urls:
            continue
        parsed = urlparse(u_clean)
        if base_domain not in parsed.netloc:
            continue
        path_lower = parsed.path.lower()
        if any(ex in path_lower for ex in exclude_patterns):
            continue
        for pattern in content_patterns:
            if pattern in path_lower:
                priority_urls.append((4, u_clean, path_lower))
                seen_urls.add(u_clean)
                break

    priority_urls.sort(reverse=True)

    for _, sub_url, sub_path in priority_urls[:5]:
        page_name = sub_path.strip("/").split("/")[-1][:40]
        t, h, _ = fetch_page(sub_url)
        if t:
            pages_content[page_name] = {"text": t, "headings": h}

    return pages_content


def format_crawl_for_prompt(pages_content):
    if not pages_content:
        return "Keine Website-Inhalte konnten geladen werden."
    output = []
    for page_name, data in pages_content.items():
        output.append(f"\n=== SEITE: {page_name.upper()} ===")
        if data.get("headings"):
            headings = data["headings"]
            faq_fragen = [h for h in headings if h.startswith("[SPAN]") and "?" in h]
            normale_headings = [h for h in headings if not h.startswith("[SPAN]")]
            if normale_headings:
                output.append("UEBERSCHRIFTEN: " + " | ".join(normale_headings[:10]))
            if faq_fragen:
                output.append(f"FAQ-SEKTION VORHANDEN ({len(faq_fragen)} Fragen gefunden):")
                for fq in faq_fragen:
                    output.append("  " + fq.replace("[SPAN] ", "- "))
        output.append("TEXT: " + data["text"][:2500])
    return "\n".join(output)


# ─── ROBUSTE JSON-PARSE FUNKTION ───
def safe_json_parse(raw):
    """
    Robuste JSON-Extraktion aus Claude-Antworten.
    Behandelt: reines JSON, ```json Blöcke, ``` Blöcke, JSON mit führendem Text,
    unescapte Anführungszeichen in Strings, Trailing Commas, Sonderzeichen.
    """
    import re

    if not raw or not raw.strip():
        raise ValueError("Leere Antwort von Claude API")

    text = raw.strip()

    # Fall 1: Markdown-Codeblock mit ```json oder ```
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.lower().startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break

    # Fall 2: JSON-Objekt direkt extrahieren (erstes { bis letztes })
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    else:
        raise ValueError(f"Kein JSON-Objekt gefunden. Antwort beginnt mit: {raw[:300]}")

    # Fall 3: Trailing Commas bereinigen
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    # Fall 4: Direkt parsen versuchen
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall 5: Deutsche/typografische Anführungszeichen durch Standard ersetzen
    text = text.replace('\u201c', '\\"').replace('\u201d', '\\"')
    text = text.replace('\u2018', "\\'").replace('\u2019', "\\'")
    text = text.replace('\u2013', '-').replace('\u2014', '-')

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall 6: Zeilenumbrüche in JSON-Strings escapen
    # Findet unescapte Newlines innerhalb von String-Werten und ersetzt sie
    def fix_newlines_in_strings(s):
        result = []
        in_string = False
        escape_next = False
        for ch in s:
            if escape_next:
                result.append(ch)
                escape_next = False
            elif ch == '\\':
                result.append(ch)
                escape_next = True
            elif ch == '"':
                result.append(ch)
                in_string = not in_string
            elif in_string and ch == '\n':
                result.append('\\n')
            elif in_string and ch == '\r':
                result.append('\\r')
            elif in_string and ch == '\t':
                result.append('\\t')
            else:
                result.append(ch)
        return ''.join(result)

    text = fix_newlines_in_strings(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON-Parse-Fehler: {e}\nText (erste 500 Zeichen): {text[:500]}")


def run_analysis(hotel_name, location, url, business_type):
    api_key = get_api_key()
    if not api_key:
        st.error("❌ API-Key nicht konfiguriert. Bitte in Streamlit Secrets eintragen (ANTHROPIC_API_KEY).")
        return None

    with st.spinner("\U0001f50d Website wird gecrawlt... (Startseite + relevante Unterseiten)"):
        pages_content = crawl_website(url)
        website_content = format_crawl_for_prompt(pages_content)
        pages_found = list(pages_content.keys())

    crawl_info = f"Gecrawlte Seiten ({len(pages_found)}): {', '.join(pages_found)}"

    client = anthropic.Anthropic(api_key=api_key)

    # ── CALL 1: Analyse-Report ──
    analyse_prompt = f"""Du bist GEO-Optimierungs-Experte fuer Tourismus-Websites im DACH-Raum.

Betrieb: {hotel_name} | Ort: {location} | Typ: {business_type}
{crawl_info}

GECRAWLTE INHALTE:
{website_content[:8000]}

Bewerte diese 5 Faktoren (0-10) basierend auf den gecrawlten Inhalten:
1. FAQ-Sektion: Strukturierte Fragen & Antworten vorhanden?
2. H1-Optimierung: Ortsbezug und USP in Hauptueberschriften?
3. Lokale Keywords: Region, Bundesland, Aktivitaeten, Saison?
4. NAP-Konsistenz: Name, Adresse, Telefon vollstaendig & einheitlich?
5. USP-Klarheit: Klare Alleinstellungsmerkmale kommuniziert?

USP-Regel: Appartement mit Sauna/Panorama = echter USP. Hotel 3-4 Sterne mit Sauna = Standard.
WICHTIG: Sei fair - wenn FAQ auf Unterseite vorhanden, ist das ein gutes Zeichen (6-8 Punkte).
ACHTUNG JS-Websites: Wenn du "ZUSATZ-FAQ-INHALTE:" oder "FAQ:" Eintraege im Text siehst, sind das extrahierte Accordion-Fragen von Next.js/React-Seiten. Diese ZAEHLEN als vollwertige FAQ-Sektion (7-9 Punkte)!

Antworte AUSSCHLIESSLICH als reines JSON-Objekt. Kein Markdown, keine Erklaerungen, keine Codeblocks.
Beginne deine Antwort direkt mit {{ und beende sie mit }}

{{
  "gesamtscore": <0-50>,
  "faktoren": [
    {{"name": "FAQ-Sektion", "score": <0-10>, "kommentar": "<1 praegnanter Satz>"}},
    {{"name": "H1-Optimierung", "score": <0-10>, "kommentar": "<1 praegnanter Satz>"}},
    {{"name": "Lokale Keywords", "score": <0-10>, "kommentar": "<1 praegnanter Satz>"}},
    {{"name": "NAP-Konsistenz", "score": <0-10>, "kommentar": "<1 praegnanter Satz>"}},
    {{"name": "USP-Klarheit", "score": <0-10>, "kommentar": "<1 praegnanter Satz>"}}
  ],
  "quickwins": [
    {{"prioritaet": "sofort", "massnahme": "<konkrete Massnahme>", "impact": "<messbarer Effekt>"}},
    {{"prioritaet": "sofort", "massnahme": "<konkrete Massnahme>", "impact": "<messbarer Effekt>"}},
    {{"prioritaet": "kurz", "massnahme": "<konkrete Massnahme>", "impact": "<messbarer Effekt>"}},
    {{"prioritaet": "kurz", "massnahme": "<konkrete Massnahme>", "impact": "<messbarer Effekt>"}},
    {{"prioritaet": "mittel", "massnahme": "<konkrete Massnahme>", "impact": "<messbarer Effekt>"}}
  ],
  "zusammenfassung": "<2-3 Saetze ehrliche Gesamtbewertung>"
}}"""

    with st.spinner("📊 Analysiere Website-Inhalte..."):
        msg1 = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=1500,
            messages=[{"role": "user", "content": analyse_prompt}]
        )

    try:
        result = safe_json_parse(msg1.content[0].text)
    except ValueError as e:
        st.error(f"❌ Fehler bei Analyse-Auswertung: {e}")
        return None

    # ── CALL 2: Optimierungspaket ──
    paket_prompt = f"""Du erstellst das GEO-Optimierungspaket Professional fuer diesen Betrieb.

Betrieb: {hotel_name} | Ort: {location} | Typ: {business_type}

WEBSITE-INHALTE (gecrawlt):
{website_content[:6000]}

Erstelle auf Basis der tatsaechlichen Website-Inhalte:
- FAQ: 10 Fragen+Antworten, KI-optimiert, zum Betrieb passend
- H1_NEU: Optimierter Seitentitel (max 70 Zeichen, mit Ort+USP)
- H1_SUB: Subheadline (max 120 Zeichen)
- USP_BOX: 4 echte Alleinstellungsmerkmale (Emoji + Titel + 1 Satz)
- KEYWORDS: 20 lokale Keywords fuer die Region
- GOOGLE_BUSINESS: Google Business Text (max 750 Zeichen, keyword-reich)
- META_START: Meta-Description Startseite (max 155 Zeichen)
- META_ZIMMER: Meta-Description Zimmer/Appartements (max 155 Zeichen)
- META_PREISE: Meta-Description Preise/Angebote (max 155 Zeichen)
- UEBER_UNS: "Ueber uns" Text (250-300 Woerter, KI-lesbar, mit Lage+Geschichte+USPs)

WICHTIG: Nur Fakten aus gecrawlten Inhalten verwenden. Keine Erfindungen.

KRITISCH FUER VALIDES JSON - diese Regeln sind absolut:
- Verwende NIEMALS Anfuehrungszeichen (\", ', oder typografische) innerhalb von Textwerten
  Falsch: "antwort": "Die Panoramasauna - auch \"finnische Sauna\" genannt - ist..."
  Richtig: "antwort": "Die Panoramasauna mit finnischem Charakter ist..."
- Kein echter Zeilenumbruch innerhalb eines JSON-Stringwertes - schreibe alles in einer Zeile
- Keine Sonderzeichen die JSON brechen koennen

Antworte AUSSCHLIESSLICH als reines JSON-Objekt. Kein Markdown, keine Erklaerungen, keine Codeblocks.
Beginne deine Antwort direkt mit {{ und beende sie mit }}

{{
  "faq": [{{"frage": "<Frage>", "antwort": "<Antwort>"}}],
  "h1_neu": "<H1-Titel>",
  "h1_sub": "<Subheadline>",
  "usp_box": [{{"emoji": "<>", "titel": "<>", "text": "<1 Satz>"}}],
  "keywords": ["<kw1>", "<kw2>"],
  "google_business": "<Text>",
  "meta_start": "<Meta>",
  "meta_zimmer": "<Meta>",
  "meta_preise": "<Meta>",
  "ueber_uns": "<Text>"
}}"""

    with st.spinner("📦 Erstelle Optimierungspaket..."):
        msg2 = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=3000,
            messages=[{"role": "user", "content": paket_prompt}]
        )

    try:
        paket = safe_json_parse(msg2.content[0].text)
    except ValueError as e:
        st.error(f"❌ Fehler bei Paket-Erstellung: {e}")
        return None

    result["paket"] = paket
    result["hotelName"] = hotel_name
    result["location"] = location
    result["url"] = url
    result["type"] = business_type
    result["email"] = ""
    result["date"] = __import__("datetime").date.today().strftime("%d.%m.%Y")
    return result

# ─── PDF GENERATOR ───
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
    pdf.cell(0, 6, sanitize(f"{r['location']} | {r['type']} | Erstellt am {r['date']}"), ln=True)

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

    pdf.set_fill_color(240, 237, 232)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_x(15)
    pdf.multi_cell(180, 6, sanitize(r.get("zusammenfassung", "")), fill=True)
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(26, 35, 50)
    pdf.set_x(15)
    pdf.cell(0, 8, "Faktor-Analyse", ln=True)
    pdf.ln(2)

    for f in r["faktoren"]:
        score_f = f["score"]
        if score_f >= 8:
            r_c, g_c, b_c = 39, 174, 96
        elif score_f >= 5:
            r_c, g_c, b_c = 230, 126, 34
        else:
            r_c, g_c, b_c = 192, 57, 43

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(26, 35, 50)
        pdf.set_x(15)
        pdf.cell(140, 6, sanitize(f["name"]))
        pdf.set_text_color(r_c, g_c, b_c)
        pdf.cell(0, 6, f"{score_f}/10", ln=True)

        pdf.set_fill_color(220, 220, 220)
        pdf.rect(15, pdf.get_y(), 80, 3, 'F')
        pdf.set_fill_color(r_c, g_c, b_c)
        pdf.rect(15, pdf.get_y(), (score_f / 10) * 80, 3, 'F')
        pdf.ln(5)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 110, 120)
        pdf.set_x(15)
        pdf.multi_cell(180, 5, sanitize(f["kommentar"]))
        pdf.ln(3)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(26, 35, 50)
    pdf.set_x(15)
    pdf.cell(0, 8, "Quick Wins", ln=True)
    pdf.ln(2)

    prio_colors = {
        "sofort": (192, 57, 43),
        "kurz": (230, 126, 34),
        "mittel": (39, 174, 96)
    }
    prio_labels = {"sofort": "SOFORT", "kurz": "KURZFRISTIG", "mittel": "MITTELFRISTIG"}

    for w in r["quickwins"]:
        rc, gc, bc = prio_colors.get(w["prioritaet"], (100, 100, 100))
        pdf.set_fill_color(rc, gc, bc)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_x(15)
        pdf.cell(30, 6, prio_labels.get(w["prioritaet"], ""), fill=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(26, 35, 50)
        pdf.set_x(48)
        pdf.multi_cell(157, 6, sanitize(w["massnahme"]))
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(61, 122, 94)
        pdf.set_x(48)
        pdf.cell(0, 5, sanitize("-> " + w["impact"]), ln=True)
        pdf.ln(2)

    pdf.ln(6)
    pdf.set_fill_color(26, 35, 50)
    pdf.set_x(15)
    y_start = pdf.get_y()
    pdf.rect(15, y_start, 180, 28, 'F')
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(201, 168, 76)
    pdf.set_xy(20, y_start + 5)
    pdf.cell(0, 7, "Detailberatung anfragen")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(200, 210, 220)
    pdf.set_xy(20, y_start + 13)
    pdf.cell(0, 5, "kontakt@gernot-riedel.com  |  +43 676 7237811  |  gernot-riedel.com")

    return bytes(pdf.output())

# ─── MAIN FORM ───
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

# ─── ANALYSIS ───
if submitted:
    if not hotel_name or not website_url or not contact_email:
        st.error("Bitte Betriebsname, Website-URL und E-Mail angeben.")
    else:
        with st.spinner("🤖 KI wertet gecrawlte Inhalte aus... Das dauert ca. 30–60 Sekunden."):
            progress = st.progress(0)
            import time
            for i in range(0, 60, 10):
                time.sleep(0.3)
                progress.progress(i)

            result = run_analysis(hotel_name, location, website_url, business_type)

            progress.progress(100)
            time.sleep(0.2)
            progress.empty()

        if result:
            result["hotelName"] = hotel_name
            result["location"] = location
            result["type"] = business_type
            result["email"] = contact_email
            result["url"] = website_url
            result["date"] = datetime.date.today().strftime("%d.%m.%Y")
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

# ─── RESULTS ───
if st.session_state.result:
    r = st.session_state.result
    score = r["gesamtscore"]

    st.markdown("---")
    st.markdown(f"## 📊 Analyse: {r['hotelName']}")
    st.caption(f"{r['location']} · {r['type']} · {r['date']}")

    if score >= 40:
        score_class = "score-excellent"
        score_label = "Ausgezeichnet"
    elif score >= 28:
        score_class = "score-good"
        score_label = "Gut"
    elif score >= 16:
        score_class = "score-poor"
        score_label = "Verbesserungsbedarf"
    else:
        score_class = "score-critical"
        score_label = "Kritisch"

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

    st.markdown("### Faktor-Analyse")
    for f in r["faktoren"]:
        s = f["score"]
        bar_color = "#27ae60" if s >= 8 else "#e67e22" if s >= 5 else "#c0392b"
        col_f1, col_f2 = st.columns([4, 1])
        with col_f1:
            st.markdown(f"**{f['name']}**")
            st.progress(s / 10)
            st.caption(f["kommentar"])
        with col_f2:
            st.markdown(f"<div style='font-size:28px;font-weight:800;color:{bar_color};text-align:center;padding-top:8px'>{s}<span style='font-size:14px;color:#aaa'>/10</span></div>", unsafe_allow_html=True)
        st.markdown("---")

    st.markdown("### ⚡ Quick Wins")
    for w in r["quickwins"]:
        css_class = f"win-{w['prioritaet']}"
        label = {"sofort": "🔴 SOFORT", "kurz": "🟠 KURZFRISTIG", "mittel": "🟢 MITTELFRISTIG"}.get(w["prioritaet"], "")
        st.markdown(f"""
        <div class="{css_class}">
            <strong>{label}</strong> &nbsp; {w['massnahme']}<br>
            <span style="color:#3d7a5e;font-size:13px;">→ {w['impact']}</span>
        </div>
        """, unsafe_allow_html=True)

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

    paket = r.get("paket", {})
    if paket and not st.session_state.get("anfrage_gesendet", False):
        st.markdown("---")
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a2332,#2d4a3e);padding:28px 28px 24px;
                    border-radius:8px;margin-bottom:8px">
            <h3 style="color:#c9a84c;margin:0 0 12px 0">
                📦 Ihr persönliches GEO-Optimierungspaket — bereit zur Erstellung
            </h3>
            <p style="color:rgba(255,255,255,0.9);margin:0 0 16px 0;font-size:15px;line-height:1.7">
            Basierend auf dieser Analyse kann für Ihren Betrieb ein 
            <strong style="color:white">vollständiges Optimierungspaket</strong> erstellt werden —
            mit allen Texten die Sie, ein Mitarbeiter oder Ihre Webagentur 
            direkt in Ihre Website einbauen können.
            </p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px">
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;
                            border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700;letter-spacing:1px">LIEFERUNG 1</div>
                    <div style="color:white;font-size:14px;margin-top:2px">📋 10 FAQ-Fragen + Antworten</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;
                            border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700;letter-spacing:1px">LIEFERUNG 2</div>
                    <div style="color:white;font-size:14px;margin-top:2px">🏷️ H1-Titel + Subheadline neu</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;
                            border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700;letter-spacing:1px">LIEFERUNG 3</div>
                    <div style="color:white;font-size:14px;margin-top:2px">⭐ USP-Box mit 4 Alleinstellungsmerkmalen</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;
                            border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700;letter-spacing:1px">LIEFERUNG 4</div>
                    <div style="color:white;font-size:14px;margin-top:2px">🔍 20 lokale Keywords</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;
                            border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700;letter-spacing:1px">LIEFERUNG 5</div>
                    <div style="color:white;font-size:14px;margin-top:2px">📍 Google Business Profil-Text</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;
                            border-left:3px solid #c9a84c">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700;letter-spacing:1px">LIEFERUNG 6</div>
                    <div style="color:white;font-size:14px;margin-top:2px">🔗 3 Meta-Descriptions</div>
                </div>
                <div style="background:rgba(255,255,255,0.08);padding:10px 14px;border-radius:6px;
                            border-left:3px solid #c9a84c;grid-column:span 2">
                    <div style="color:#c9a84c;font-size:11px;font-weight:700;letter-spacing:1px">LIEFERUNG 7</div>
                    <div style="color:white;font-size:14px;margin-top:2px">📖 "Über uns" — komplett neu geschrieben (KI-optimiert)</div>
                </div>
            </div>
            <p style="color:rgba(255,255,255,0.6);margin:0;font-size:13px;font-style:italic">
            ✉️ Nach Ihrer Bestellung erhalten Sie alle 7 Lieferungen als fertig formatiertes Dokument per E-Mail —
            innerhalb von 24 Stunden.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="cta-box">
        <h3 style="color:#c9a84c;margin:0 0 8px 0">🚀 GEO-Optimierungspaket Professional — € 149</h3>
        <p style="color:rgba(255,255,255,0.85);margin:0 0 6px 0;font-size:15px">
        Alle 7 Lieferungen oben als fertiges Dokument — von Ihnen, einem Mitarbeiter oder Ihrer Webagentur umsetzbar:</p>
        <p style="color:rgba(255,255,255,0.75);margin:0 0 16px 0;font-size:13px">
        ✅ 10 FAQ-Fragen &nbsp;|&nbsp; ✅ H1-Titel + Subheadline &nbsp;|&nbsp; ✅ USP-Box &nbsp;|&nbsp;
        ✅ 20 Keywords &nbsp;|&nbsp; ✅ Google Business Text &nbsp;|&nbsp;
        ✅ 3 Meta-Descriptions &nbsp;|&nbsp; ✅ Über uns neu
        </p>
    </div>
    """, unsafe_allow_html=True)

    if "anfrage_gesendet" not in st.session_state:
        st.session_state.anfrage_gesendet = False

    if not st.session_state.anfrage_gesendet:
        if st.button("📩 Ja, ich möchte das GEO-Optimierungspaket für € 149", use_container_width=True, type="primary"):
            with st.spinner("Ihre Anfrage wird verarbeitet..."):
                try:
                    import requests as req
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
                        req.post(webhook_url, json=payload, timeout=10)
                    
                    st.session_state.anfrage_gesendet = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Fehler beim Senden: {e}")
    else:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a2332,#2d4a3e);padding:28px 28px 24px;
                    border-radius:8px;margin-bottom:8px;margin-top:16px">
            <h3 style="color:#c9a84c;margin:0 0 12px 0">
                ✅ Vielen Dank — Ihr GEO-Optimierungspaket wird jetzt erstellt!
            </h3>
            <p style="color:rgba(255,255,255,0.9);margin:0 0 16px 0;font-size:15px;line-height:1.7">
            Gernot Riedel wurde über Ihre Bestellung informiert und erstellt Ihr persönliches 
            Optimierungspaket mit <strong style="color:white">7 fertigen Texten</strong> speziell für Ihren Betrieb.
            </p>
            <div style="background:rgba(255,255,255,0.08);padding:16px 20px;border-radius:6px;
                        border-left:3px solid #c9a84c;margin-bottom:16px">
                <div style="color:#c9a84c;font-weight:700;margin-bottom:8px">📬 Was passiert als nächstes?</div>
                <div style="color:rgba(255,255,255,0.85);font-size:14px;line-height:1.8">
                    1. Sie erhalten innerhalb von <strong style="color:white">24 Stunden</strong> Ihr Paket per E-Mail<br>
                    2. Alle 7 Texte sind sofort verwendbar — für Sie, Ihr Team oder Ihre Webagentur<br>
                    3. Die Rechnung über € 149 erhalten Sie separat per E-Mail
                </div>
            </div>
            <p style="color:rgba(255,255,255,0.6);margin:0;font-size:13px">
            📧 Bei Fragen: kontakt@gernot-riedel.com &nbsp;|&nbsp; 📞 +43 676 7237811
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background:#f5f0e8;border:1px solid #e8e3da;border-left:4px solid #c9a84c;
                padding:20px 24px;border-radius:4px;margin-top:16px">
        <h4 style="margin:0 0 8px 0;color:#1a2332">📊 Noch mehr Potenzial: ReviewRadar 2.0</h4>
        <p style="margin:0 0 8px 0;color:#4a5568;font-size:14px">
        Verwandeln Sie Ihre Gästebewertungen in garantierten Mehrumsatz. ReviewRadar 2.0 analysiert 
        bis zu 800 Bewertungen von Booking.com, Google, TripAdvisor & HolidayCheck — und liefert 
        Ihnen einen klaren Aktionsplan mit ROI-Kalkulation. Einmalig, kein Abo, keine laufenden Kosten.</p>
        <p style="margin:0;font-size:14px">
        <strong style="color:#c9a84c">ab € 149</strong> &nbsp;—&nbsp; 
        3 Pakete: Quick Insight € 149 | Professional € 349 | Premium € 599 &nbsp;|&nbsp; 
        <a href="https://gernot-riedel.com/hotelbewertungen-analyse-mehr-umsatz-direktbuchungen-reviewradar/" 
        target="_blank" style="color:#3d7a5e;font-weight:600">Alle Pakete & Details →</a>
        </p>
    </div>
    """, unsafe_allow_html=True)

# ─── LEADS SECTION (Admin) ───
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

# ─── FOOTER ───
st.markdown("""
<div class="footer-bar">
    <strong style="color:#c9a84c">Gernot Riedel Tourism Consulting</strong> &nbsp;|&nbsp; 
    TÜV-zertifizierter KI-Trainer &nbsp;|&nbsp; 
    kontakt@gernot-riedel.com &nbsp;|&nbsp; 
    +43 676 7237811
</div>
""", unsafe_allow_html=True)

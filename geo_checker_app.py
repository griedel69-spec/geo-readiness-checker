"""
GEO-Readiness Checker 2.0
Gernot Riedel Tourism Consulting — gernot-riedel.com
Erstellt mit KI-Unterstützung | #GernotGoesAI #GernotGoesKI
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import anthropic
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfgen import canvas as pdfcanvas
import io

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GEO-Readiness Checker | Gernot Riedel",
    page_icon="🏔️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── DESIGN SYSTEM ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Source+Sans+3:wght@300;400;600&display=swap');

/* Reset & base */
.stApp { background: #f4f7f4; }
.main .block-container { max-width: 740px; padding: 2rem 1.5rem; }

/* Typography */
body, p, li, span, div { font-family: 'Source Sans 3', sans-serif; }
h1, h2, h3 { font-family: 'Playfair Display', serif; }

/* Header */
.geo-header {
    background: linear-gradient(135deg, #0d6248 0%, #0a4f39 100%);
    border-radius: 16px;
    padding: 2.5rem 2rem 2rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.geo-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 180px; height: 180px;
    background: rgba(244,162,97,0.15);
    border-radius: 50%;
}
.geo-header::after {
    content: '';
    position: absolute;
    bottom: -30px; left: -30px;
    width: 120px; height: 120px;
    background: rgba(255,255,255,0.05);
    border-radius: 50%;
}
.geo-title {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 800;
    color: white;
    margin: 0 0 0.4rem;
    line-height: 1.2;
}
.geo-subtitle {
    color: rgba(255,255,255,0.75);
    font-size: 1rem;
    font-weight: 300;
    margin: 0;
}
.geo-byline {
    color: #f4a261;
    font-size: 0.8rem;
    margin-top: 1rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* Form card */
.form-card {
    background: white;
    border-radius: 12px;
    padding: 1.8rem;
    box-shadow: 0 2px 20px rgba(0,0,0,0.06);
    margin-bottom: 1.5rem;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.badge-measured { background: #e8f5f0; color: #0d6248; border: 1px solid #0d6248; }
.badge-ai { background: #fff3cd; color: #856404; border: 1px solid #f4a261; }
.badge-warning { background: #ffe0e0; color: #cc3333; border: 1px solid #cc3333; }

/* Checklist items */
.check-item {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1rem 1.2rem;
    background: white;
    border-radius: 10px;
    margin: 0.5rem 0;
    box-shadow: 0 1px 8px rgba(0,0,0,0.05);
    border-left: 4px solid transparent;
}
.check-item.pass { border-left-color: #0d6248; }
.check-item.fail { border-left-color: #cc3333; }
.check-item.warn { border-left-color: #f4a261; }
.check-icon { font-size: 1.3rem; flex-shrink: 0; line-height: 1.4; }
.check-content { flex: 1; }
.check-title { font-weight: 600; color: #2b2b27; font-size: 0.95rem; }
.check-detail { color: #666; font-size: 0.85rem; margin-top: 0.2rem; line-height: 1.4; }
.check-badge { float: right; margin-top: 0.1rem; }

/* Score summary */
.score-summary {
    background: linear-gradient(135deg, #0d6248, #0a4f39);
    color: white;
    border-radius: 12px;
    padding: 1.8rem;
    text-align: center;
    margin: 1.5rem 0;
}
.score-big {
    font-family: 'Playfair Display', serif;
    font-size: 3.5rem;
    font-weight: 800;
    line-height: 1;
}
.score-label { font-size: 0.85rem; opacity: 0.8; margin-top: 0.3rem; letter-spacing: 0.05em; }
.score-verdict { font-size: 1.1rem; font-weight: 600; margin-top: 0.8rem; }
.score-note { font-size: 0.78rem; opacity: 0.65; margin-top: 0.5rem; }

/* AI analysis section */
.ai-section {
    background: #fffdf7;
    border: 1px solid #f4a261;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1rem 0;
}
.ai-section-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    color: #2b2b27;
    margin: 0 0 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.ai-disclaimer {
    background: #fff8f0;
    border-left: 3px solid #f4a261;
    padding: 0.6rem 0.8rem;
    border-radius: 0 6px 6px 0;
    font-size: 0.78rem;
    color: #856404;
    margin-bottom: 1rem;
}

/* Quick win cards */
.qw-card {
    background: white;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    border-left: 4px solid #f4a261;
    box-shadow: 0 1px 8px rgba(0,0,0,0.05);
}
.qw-prio-high { border-left-color: #cc3333; }
.qw-prio-mid { border-left-color: #f4a261; }
.qw-title { font-weight: 600; color: #2b2b27; font-size: 0.9rem; }
.qw-impact { color: #555; font-size: 0.82rem; margin-top: 0.2rem; }

/* Robots.txt highlight */
.robots-alert {
    background: #fff0f0;
    border: 2px solid #cc3333;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin: 0.8rem 0;
}
.robots-ok {
    background: #e8f5f0;
    border: 2px solid #0d6248;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin: 0.8rem 0;
}

/* Teaser grid */
.teaser-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.7rem;
    margin: 1rem 0;
}
.teaser-item {
    background: #f0f7f4;
    border: 1.5px solid #0d6248;
    border-radius: 8px;
    padding: 0.8rem 0.6rem;
    text-align: center;
}
.teaser-lock { font-size: 1.2rem; }
.teaser-name { font-size: 0.75rem; color: #0d6248; font-weight: 600; margin-top: 0.3rem; }

/* CTA button override */
.stButton > button[kind="primary"] {
    background: #0d6248 !important;
    border: none !important;
    font-family: 'Source Sans 3', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.8rem !important;
    border-radius: 8px !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"]:hover {
    background: #0a4f39 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(13,98,72,0.3) !important;
}

/* Info boxes */
.info-blocked {
    background: #fff3cd;
    border: 1px solid #f4a261;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.88rem;
}
.info-manual {
    background: #e8f5f0;
    border: 1px solid #0d6248;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin: 0.5rem 0;
    font-size: 0.88rem;
}

/* Footer */
.geo-footer {
    text-align: center;
    color: #999;
    font-size: 0.75rem;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

# ─── TECHNICAL CHECKS ENGINE ──────────────────────────────────────────────────

AI_BOTS = {
    'gptbot': 'ChatGPT (OpenAI)',
    'chatgpt-user': 'ChatGPT Browse',
    'anthropic-ai': 'Claude (Anthropic)',
    'claude-web': 'Claude Web',
    'google-extended': 'Google Gemini',
    'perplexitybot': 'Perplexity AI',
    'youbot': 'You.com',
    'ccbot': 'Common Crawl',
    'bingbot': 'Bing/Copilot',
}

def fetch_url(url: str, timeout: int = 12) -> tuple[requests.Response | None, float, str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'de-AT,de;q=0.9,en;q=0.5',
    }
    start = time.time()
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        elapsed = round(time.time() - start, 2)
        if resp.status_code in [403, 429, 503]:
            return None, elapsed, 'blocked'
        return resp, elapsed, 'ok'
    except Exception:
        elapsed = round(time.time() - start, 2)
        return None, elapsed, 'blocked'

def parse_robots(robots_text: str) -> dict:
    """Parse robots.txt and return per-bot status."""
    result = {'blocked': [], 'allowed': [], 'raw': robots_text}
    lines = robots_text.lower().split('\n')
    current_agents = []
    agent_rules = {}

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('user-agent:'):
            ua = line.split(':', 1)[1].strip()
            current_agents = [ua]
            for agent in current_agents:
                if agent not in agent_rules:
                    agent_rules[agent] = {'disallow': [], 'allow': []}
        elif line.startswith('disallow:') and current_agents:
            path = line.split(':', 1)[1].strip()
            for agent in current_agents:
                if agent not in agent_rules:
                    agent_rules[agent] = {'disallow': [], 'allow': []}
                agent_rules[agent]['disallow'].append(path)
        elif line.startswith('allow:') and current_agents:
            path = line.split(':', 1)[1].strip()
            for agent in current_agents:
                if agent not in agent_rules:
                    agent_rules[agent] = {'disallow': [], 'allow': []}
                agent_rules[agent]['allow'].append(path)

    for bot_key, bot_name in AI_BOTS.items():
        rules = agent_rules.get(bot_key, agent_rules.get('*', {'disallow': [], 'allow': []}))
        if bot_key in agent_rules:
            disallows = agent_rules[bot_key]['disallow']
            if '/' in disallows:
                result['blocked'].append(bot_name)
            else:
                result['allowed'].append(bot_name)
        else:
            # Falls under wildcard
            wildcard = agent_rules.get('*', {'disallow': []})
            if '/' in wildcard.get('disallow', []):
                result['blocked'].append(bot_name)
            else:
                result['allowed'].append(bot_name)

    return result

def run_technical_checks(url: str) -> dict:
    """Run all 10 verified technical checks. Returns structured results."""
    base_url = url.rstrip('/')
    checks = {}

    # CHECK 1: HTTPS
    checks['https'] = {
        'name': 'HTTPS / Sichere Verbindung',
        'pass': url.startswith('https://'),
        'detail': 'Website nutzt HTTPS — verschlüsselte Verbindung aktiv.' if url.startswith('https://') else 'Kein HTTPS! KI-Crawler bevorzugen sichere Seiten.',
        'badge': 'measured',
        'impact': 'Hoch' if not url.startswith('https://') else None
    }

    # Fetch main page
    resp, load_time, status = fetch_url(url)
    checks['_fetch_status'] = status
    checks['_load_time_raw'] = load_time

    # CHECK 2: Ladezeit
    checks['load_time'] = {
        'name': 'Ladezeit',
        'pass': load_time < 3.0 if status == 'ok' else None,
        'detail': f'{load_time}s — {"✓ Gut" if load_time < 3.0 else "⚠ Zu langsam (Ziel: unter 3s)"}' if status == 'ok' else 'Nicht messbar (Seite blockiert automatischen Zugriff)',
        'badge': 'measured',
        'impact': 'Mittel' if status == 'ok' and load_time >= 3.0 else None
    }

    if resp and status == 'ok':
        soup = BeautifulSoup(resp.text, 'html.parser')

        # CHECK 3: Meta Description
        meta = soup.find('meta', attrs={'name': 'description'})
        meta_content = meta.get('content', '').strip() if meta else ''
        meta_len = len(meta_content)
        meta_ok = bool(meta_content) and 50 <= meta_len <= 160
        checks['meta_desc'] = {
            'name': 'Meta-Description',
            'pass': meta_ok,
            'detail': f'"{meta_content[:100]}{"..." if meta_len > 100 else ""}" ({meta_len} Zeichen)' if meta_content else 'Fehlt! KI-Systeme nutzen Meta-Descriptions als Zusammenfassung.',
            'badge': 'measured',
            'impact': 'Hoch' if not meta_ok else None
        }

        # CHECK 4: Viewport / Mobilfähigkeit
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        checks['viewport'] = {
            'name': 'Mobilfähigkeit (Viewport)',
            'pass': bool(viewport),
            'detail': 'Viewport-Tag vorhanden — mobiloptimiert.' if viewport else 'Kein Viewport-Tag. Seite möglicherweise nicht mobiloptimiert.',
            'badge': 'measured',
            'impact': 'Mittel' if not viewport else None
        }

        # CHECK 5: Sprach-Attribut
        html_tag = soup.find('html')
        lang = html_tag.get('lang', '').strip() if html_tag else ''
        checks['lang'] = {
            'name': 'Sprach-Attribut (lang="")',
            'pass': bool(lang),
            'detail': f'Sprache "{lang}" definiert — KI versteht den Sprachkontext.' if lang else 'Kein lang-Attribut. KI-Systeme können Sprache nicht sicher zuordnen.',
            'badge': 'measured',
            'impact': 'Mittel' if not lang else None
        }

        # CHECK 6: Title-Tag
        title_tag = soup.find('title')
        title_text = title_tag.get_text(strip=True) if title_tag else ''
        title_len = len(title_text)
        title_ok = bool(title_text) and 20 <= title_len <= 70
        checks['title'] = {
            'name': 'Page Title',
            'pass': title_ok,
            'detail': f'"{title_text[:80]}" ({title_len} Zeichen) — {"✓ Optimale Länge" if 20 <= title_len <= 70 else "⚠ Zu lang (Ziel: 50–70 Zeichen)" if title_len > 70 else "⚠ Zu kurz"}' if title_text else 'Kein Title-Tag gefunden.',
            'badge': 'measured',
            'impact': None if title_ok else 'Hoch'
        }

        # CHECK 7: Canonical Tag
        canonical = soup.find('link', rel='canonical')
        checks['canonical'] = {
            'name': 'Canonical-Tag',
            'pass': bool(canonical),
            'detail': f'Canonical gesetzt: {canonical.get("href","")[:80]}' if canonical else 'Kein Canonical-Tag. Risiko für doppelte Inhalte.',
            'badge': 'measured',
            'impact': 'Mittel' if not canonical else None
        }

        # CHECK 8: Strukturierte Daten (Schema.org)
        schemas = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    t = data.get('@type', '')
                    if t:
                        schemas.append(t)
                elif isinstance(data, list):
                    schemas.extend([d.get('@type', '') for d in data if isinstance(d, dict) and d.get('@type')])
            except Exception:
                pass

        has_lodging = any(s in ['LodgingBusiness', 'Hotel', 'BedAndBreakfast', 'Resort', 'Hostel'] for s in schemas)
        has_faq = 'FAQPage' in schemas
        has_local = any(s in ['LocalBusiness', 'LodgingBusiness', 'Organization'] for s in schemas)
        schema_detail_parts = []
        if schemas:
            schema_detail_parts.append(f'Gefunden: {", ".join(set(schemas))}')
        if has_faq:
            schema_detail_parts.append('✓ FAQPage Schema — exzellent für KI-Sichtbarkeit')
        elif not has_faq:
            schema_detail_parts.append('⚠ Kein FAQPage Schema — größte schnelle Gewinnchance')
        if has_lodging:
            schema_detail_parts.append('✓ Hotel-Schema vorhanden')

        checks['schema'] = {
            'name': 'Strukturierte Daten (Schema.org)',
            'pass': has_local,
            'warn': has_local and not has_faq,
            'detail': ' | '.join(schema_detail_parts) if schema_detail_parts else 'Keine Schema.org-Daten gefunden. KI kann den Betriebstyp nicht automatisch erkennen.',
            'badge': 'measured',
            'impact': 'Hoch' if not has_local else ('Mittel' if not has_faq else None),
            'faq_missing': not has_faq
        }

    else:
        # JS-heavy or blocked — mark these as "not checkable"
        for key in ['meta_desc', 'viewport', 'lang', 'title', 'canonical', 'schema']:
            checks[key] = {
                'name': {'meta_desc': 'Meta-Description', 'viewport': 'Mobilfähigkeit', 'lang': 'Sprach-Attribut',
                         'title': 'Page Title', 'canonical': 'Canonical-Tag', 'schema': 'Strukturierte Daten'}[key],
                'pass': None,
                'detail': 'Website blockiert automatischen Zugriff — manuelle Prüfung empfohlen.',
                'badge': 'measured',
                'impact': None
            }

    # CHECK 9: robots.txt + KI-Bot-Check
    robots_resp, _, robots_status = fetch_url(base_url + '/robots.txt', timeout=5)
    if robots_resp and robots_resp.status_code == 200 and len(robots_resp.text) > 10:
        robots_data = parse_robots(robots_resp.text)
        blocked = robots_data['blocked']
        checks['robots'] = {
            'name': 'KI-Bot-Zugang (robots.txt)',
            'pass': len(blocked) == 0,
            'detail_blocked': blocked,
            'detail_raw': robots_resp.text,
            'badge': 'measured',
            'is_robots': True,
            'exists': True
        }
    else:
        checks['robots'] = {
            'name': 'KI-Bot-Zugang (robots.txt)',
            'pass': None,
            'detail': 'robots.txt nicht gefunden oder nicht erreichbar.',
            'badge': 'measured',
            'is_robots': True,
            'exists': False
        }

    # CHECK 10: Sitemap
    sitemap_resp, _, _ = fetch_url(base_url + '/sitemap.xml', timeout=5)
    sitemap_ok = sitemap_resp is not None and sitemap_resp.status_code == 200
    checks['sitemap'] = {
        'name': 'Sitemap.xml',
        'pass': sitemap_ok,
        'detail': 'sitemap.xml gefunden — KI-Crawler können alle Seiten finden.' if sitemap_ok else 'Keine sitemap.xml. KI-Crawler müssen Seiten selbst entdecken.',
        'badge': 'measured',
        'impact': 'Mittel' if not sitemap_ok else None
    }

    return checks

def score_from_checks(checks: dict) -> tuple[int, int]:
    """Calculate score: passed / total checkable."""
    total = 0
    passed = 0
    for key, check in checks.items():
        if key.startswith('_'):
            continue
        if check.get('pass') is None:
            continue
        total += 1
        if check.get('warn'):
            passed += 0.5
        elif check.get('pass'):
            passed += 1
    return int(passed), total

# ─── CLAUDE AI ANALYSIS ───────────────────────────────────────────────────────

def analyse_mit_claude(betrieb: str, ort: str, url: str, typ: str, website_text: str, checks: dict) -> dict:
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
    client = anthropic.Anthropic(api_key=api_key)

    # Summarize technical checks for context
    check_summary = []
    for key, check in checks.items():
        if key.startswith('_') or key == 'robots':
            continue
        status = "✓" if check.get('pass') else ("~" if check.get('pass') is None else "✗")
        check_summary.append(f"{status} {check['name']}: {check.get('detail','')[:80]}")

    prompt = f"""Du bist ein GEO-Optimierungsexperte für Tourismus im DACH-Raum.

BETRIEB: {betrieb}
ORT: {ort}
TYP: {typ}
URL: {url}

TECHNISCHE CHECKS (bereits verifiziert):
{chr(10).join(check_summary)}

WEBSITE-TEXT (vom Betreiber bereitgestellt oder automatisch geladen):
{website_text[:4000] if website_text else "Kein Text verfügbar — nur technische Analyse möglich."}

DEINE AUFGABE:
Erstelle eine INHALTLICHE GEO-Analyse als Ergänzung zu den technischen Checks.
Bewerte NUR was du aus dem Website-Text DIREKT ableiten kannst.
Bei fehlenden Informationen: schreibe "[nicht beurteilbar — Text fehlt]"

WICHTIG:
- Keine Schlussfolgerungen aus regionalen Daten auf den Betrieb
- Keine erfundenen Fakten
- Zahlen nur wenn explizit im Text
- Alles mit [bitte prüfen] markieren was unsicher ist

Antworte NUR mit diesem JSON (kein Text davor/danach):

{{
  "zusammenfassung": "2-3 Sätze zur inhaltlichen KI-Readiness auf Basis des Textes",
  "text_bewertung": {{
    "usp_klarheit": {{"score": 0-10, "kommentar": "Was sind die USPs laut Text? Sind sie klar formuliert?"}},
    "lokale_signale": {{"score": 0-10, "kommentar": "Ort, Region, Aktivitäten, Lage — wie präzise?"}},
    "zielgruppen_klarheit": {{"score": 0-10, "kommentar": "Wer wird angesprochen? Für wen ist der Betrieb?"}},
    "faq_potential": {{"score": 0-10, "kommentar": "Welche Fragen würden Gäste stellen die nicht beantwortet werden?"}}
  }},
  "quickwins": [
    {{"prioritaet": "HOCH", "massnahme": "...", "impact": "..."}},
    {{"prioritaet": "HOCH", "massnahme": "...", "impact": "..."}},
    {{"prioritaet": "MITTEL", "massnahme": "...", "impact": "..."}},
    {{"prioritaet": "MITTEL", "massnahme": "...", "impact": "..."}},
    {{"prioritaet": "MITTEL", "massnahme": "...", "impact": "..."}}
  ],
  "paket": {{
    "faq": [
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}},
      {{"frage": "...", "antwort": "..."}}
    ],
    "h1_neu": "Neuer H1-Vorschlag (max 70 Zeichen, keyword-reich)",
    "h1_sub": "Subheadline (max 120 Zeichen)",
    "usp_box": [
      {{"emoji": "🏔️", "titel": "USP 1", "text": "Ein Satz"}},
      {{"emoji": "🛁", "titel": "USP 2", "text": "Ein Satz"}},
      {{"emoji": "🍽️", "titel": "USP 3", "text": "Ein Satz"}},
      {{"emoji": "📍", "titel": "USP 4", "text": "Ein Satz"}}
    ],
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5",
                 "keyword6", "keyword7", "keyword8", "keyword9", "keyword10",
                 "keyword11", "keyword12", "keyword13", "keyword14", "keyword15",
                 "keyword16", "keyword17", "keyword18", "keyword19", "keyword20"],
    "google_business": "Google Business Profil-Text (max 750 Zeichen)",
    "meta_start": "Meta-Description Startseite (max 155 Zeichen)",
    "meta_zimmer": "Meta-Description Zimmer/Suiten (max 155 Zeichen)",
    "meta_preise": "Meta-Description Preise/Buchung (max 155 Zeichen)",
    "ueber_uns": "Neuer Über-uns-Text (250-300 Wörter, KI-lesbar, mit Geschichte/Lage/USPs)"
  }}
}}"""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


# ─── PDF EXPORT ───────────────────────────────────────────────────────────────

def generate_pdf(betrieb, ort, url, typ, checks, ai_result, score_passed, score_total, email):
    """Branded PDF report using reportlab — full Unicode/UTF-8 support."""

    # Colors
    C_GREEN = HexColor('#0d6248')
    C_ORANGE = HexColor('#f4a261')
    C_LIGHT_GREEN = HexColor('#e8f5f0')
    C_NEAR_BLACK = HexColor('#2b2b27')
    C_GREY = HexColor('#888888')
    C_LIGHT_GREY = HexColor('#f8f9fa')
    C_RED = HexColor('#cc3333')
    C_WARN = HexColor('#856404')
    C_WARN_BG = HexColor('#fffdf7')

    buf = io.BytesIO()

    class BrandedCanvas(pdfcanvas.Canvas):
        def __init__(self, filename, **kwargs):
            pdfcanvas.Canvas.__init__(self, filename, **kwargs)
            self._saved_page_states = []
        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()
        def save(self):
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_chrome()
                pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)
        def _draw_chrome(self):
            # Header
            self.setFillColor(C_GREEN)
            self.rect(0, A4[1]-28*mm, A4[0], 28*mm, fill=1, stroke=0)
            self.setFillColor(white)
            self.setFont("Helvetica-Bold", 16)
            self.drawString(15*mm, A4[1]-14*mm, "GEO-Readiness Checker")
            self.setFont("Helvetica", 9)
            betrieb_safe = betrieb[:40]
            self.drawString(15*mm, A4[1]-21*mm, f"Analyse: {betrieb_safe} | {ort[:30]} | {datetime.now().strftime('%d.%m.%Y')}")
            self.setFillColor(C_ORANGE)
            self.setFont("Helvetica", 8)
            self.drawRightString(A4[0]-15*mm, A4[1]-14*mm, "gernot-riedel.com")
            self.drawRightString(A4[0]-15*mm, A4[1]-21*mm, "kontakt@gernot-riedel.com")
            # Footer
            self.setFillColor(C_GREEN)
            self.rect(0, 0, A4[0], 13*mm, fill=1, stroke=0)
            self.setFillColor(white)
            self.setFont("Helvetica", 7)
            self.drawString(15*mm, 8*mm, "Gernot Riedel Tourism Consulting  |  gernot-riedel.com  |  +43 676 7237811  |  #GernotGoesAI #GernotGoesKI")
            self.drawRightString(A4[0]-15*mm, 8*mm, "Technische Checks = verifizierte Messwerte")
            self.setFillColor(C_ORANGE)
            self.setFont("Helvetica-Oblique", 7)
            self.drawString(15*mm, 3.5*mm, "KI-Einschaetzungen sind Ergaenzungen, keine Messwerte.")

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=33*mm, bottomMargin=19*mm,
        canvasmaker=BrandedCanvas
    )

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    story = []

    def section_header(title, color=None):
        bg = color or C_GREEN
        tbl = Table([[Paragraph(f"<b>{title}</b>",
            S('sh', fontName='Helvetica-Bold', fontSize=11, textColor=white, leading=14))]],
            colWidths=[180*mm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(KeepTogether([tbl, Spacer(1, 2*mm)]))

    def info_box(text, bg_color, border_color):
        tbl = Table([[Paragraph(text, S('ib', fontName='Helvetica', fontSize=9,
                     textColor=C_NEAR_BLACK, leading=13))]],
                    colWidths=[180*mm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_color),
            ('BOX', (0,0), (-1,-1), 1, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 3*mm))

    # ── Score Box ──
    score_pct = score_passed / max(score_total, 1)
    if score_pct >= 0.8:
        verdict, v_color = "Gut aufgestellt", C_GREEN
    elif score_pct >= 0.55:
        verdict, v_color = "Verbesserungspotenzial", C_ORANGE
    else:
        verdict, v_color = "Handlungsbedarf", C_RED

    score_tbl = Table([[
        Paragraph(f"<b>{score_passed}/{score_total}</b>",
                  S('sc', fontName='Helvetica-Bold', fontSize=26, textColor=C_GREEN, leading=30)),
        [Paragraph(f"<b>Technische Checks bestanden</b>",
                   S('sv', fontName='Helvetica-Bold', fontSize=12, textColor=C_NEAR_BLACK, leading=15)),
         Spacer(1, 2*mm),
         Paragraph(f"<b>{verdict}</b>",
                   S('sv2', fontName='Helvetica-Bold', fontSize=10, textColor=v_color, leading=12)),
         Spacer(1, 2*mm),
         Paragraph("Verifizierte Messwerte — reproduzierbar und nachvollziehbar",
                   S('sv3', fontName='Helvetica-Oblique', fontSize=8, textColor=C_GREY, leading=10))]
    ]], colWidths=[30*mm, 150*mm])
    score_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_GREEN),
        ('BOX', (0,0), (-1,-1), 1, C_GREEN),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(score_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Robots.txt highlight ──
    robots = checks.get('robots', {})
    if robots.get('exists'):
        blocked = robots.get('detail_blocked', [])
        if blocked:
            bot_str = ', '.join(blocked)
            info_box(f"<b>KI-Bots blockiert — Sofortiger Handlungsbedarf!</b><br/>"
                     f"Folgende KI-Systeme koennen diese Website NICHT lesen: {bot_str}",
                     HexColor('#fff0f0'), C_RED)
        else:
            info_box("<b>Alle KI-Bots haben Zugang</b><br/>"
                     "robots.txt laesst ChatGPT, Claude, Perplexity &amp; Co. zu.",
                     C_LIGHT_GREEN, C_GREEN)

    # ── Technische Checkliste ──
    section_header("Technische Checkliste")
    check_order = ['https', 'load_time', 'title', 'meta_desc', 'viewport',
                   'lang', 'canonical', 'schema', 'robots', 'sitemap']
    rows = []
    for key in check_order:
        chk = checks.get(key, {})
        if not chk:
            continue
        if chk.get('is_robots'):
            blocked_list = chk.get('detail_blocked', [])
            p = chk.get('pass')
            icon = "OK" if p else ("??" if not chk.get('exists') else "!!")
            detail = "Alle KI-Bots erlaubt" if p else (f"Blockiert: {', '.join(blocked_list)}" if blocked_list else "Fehlt")
            bg = C_LIGHT_GREEN if p else HexColor('#fff0f0')
        else:
            p = chk.get('pass')
            warn = chk.get('warn', False)
            icon = "OK" if (p and not warn) else ("~" if warn or p is None else "!!")
            detail = chk.get('detail', '')[:100]
            bg = C_LIGHT_GREEN if (p and not warn) else (HexColor('#fff8f0') if warn or p is None else HexColor('#fff0f0'))

        icon_color = '#0d6248' if icon == 'OK' else ('#f4a261' if icon == '~' else '#cc3333')
        rows.append([
            Paragraph(f"<b><font color='{icon_color}'>{icon}</font></b>",
                      S('ic', fontName='Helvetica-Bold', fontSize=9, leading=13)),
            Paragraph(f"<b>{chk.get('name', key)}</b><br/>"
                      f"<font size='7.5' color='#888888'>{detail}</font>",
                      S('cn', fontName='Helvetica', fontSize=8.5, textColor=C_NEAR_BLACK, leading=12)),
            Paragraph("<font size='7' color='#0d6248'>● Gemessen</font>",
                      S('bd', fontName='Helvetica', fontSize=7, leading=10)),
            bg
        ])

    for row in rows:
        bg_color = row.pop()
        tbl = Table([row], colWidths=[12*mm, 140*mm, 28*mm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_color),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LINEBELOW', (0,0), (-1,-1), 0.3, HexColor('#dddddd')),
        ]))
        story.append(tbl)

    story.append(Spacer(1, 5*mm))

    # ── KI-Analyse ──
    if ai_result:
        section_header("Inhaltliche KI-Analyse", color=HexColor('#856404'))
        info_box("KI-Einschaetzung — Diese Bewertungen basieren auf der Analyse des Website-Textes. "
                 "Sie ergaenzen die technischen Checks, sind aber keine Messwerte.",
                 C_WARN_BG, C_ORANGE)

        text_bew = ai_result.get('text_bewertung', {})
        labels_order = [('usp_klarheit', 'USP-Klarheit'), ('lokale_signale', 'Lokale Signale'),
                        ('zielgruppen_klarheit', 'Zielgruppen-Klarheit'), ('faq_potential', 'FAQ-Potenzial')]
        for k, label in labels_order:
            item = text_bew.get(k, {})
            sc = item.get('score', 0)
            kommentar = item.get('kommentar', '')[:120]
            bar_f = "+" * sc + "-" * (10 - sc)
            icon = "OK" if sc >= 7 else ("~" if sc >= 4 else "!!")
            icon_c = '#0d6248' if sc >= 7 else ('#f4a261' if sc >= 4 else '#cc3333')
            bg = C_LIGHT_GREEN if sc >= 7 else (HexColor('#fff8f0') if sc >= 4 else HexColor('#fff0f0'))
            row = [
                Paragraph(f"<b><font color='{icon_c}'>{icon}</font></b>",
                          S('ki', fontName='Helvetica-Bold', fontSize=9, leading=13)),
                Paragraph(f"<b>{label}</b> — {sc}/10  <font face='Courier' size='7'>[{bar_f}]</font><br/>"
                          f"<font size='7.5' color='#888888'>{kommentar}</font>",
                          S('kb', fontName='Helvetica', fontSize=8.5, textColor=C_NEAR_BLACK, leading=12)),
                Paragraph("<font size='7' color='#856404'>● KI-Einschaetzung</font>",
                          S('kib', fontName='Helvetica', fontSize=7, leading=10)),
            ]
            tbl = Table([row], colWidths=[12*mm, 140*mm, 28*mm])
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bg),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,-1), 0.3, HexColor('#dddddd')),
            ]))
            story.append(tbl)

        zus = ai_result.get('zusammenfassung', '')
        if zus:
            story.append(Spacer(1, 3*mm))
            info_box(f"<b>Fazit:</b> {zus}", C_LIGHT_GREY, HexColor('#cccccc'))

        story.append(Spacer(1, 3*mm))
        section_header("Quick Wins — sofort umsetzbar")
        for qw in ai_result.get('quickwins', []):
            prio = qw.get('prioritaet', 'MITTEL')
            massnahme = qw.get('massnahme', '')
            impact = qw.get('impact', '')
            prio_c = '#cc3333' if prio == 'HOCH' else '#f4a261'
            border_c = C_RED if prio == 'HOCH' else C_ORANGE
            qw_row = [
                Paragraph(f"<b><font color='{prio_c}'>{prio}</font></b>",
                          S('qp', fontName='Helvetica-Bold', fontSize=8, textColor=HexColor(prio_c), leading=12)),
                Paragraph(f"<b>{massnahme}</b><br/>"
                          f"<font size='7.5' color='#666666'>Wirkung: {impact}</font>",
                          S('qm', fontName='Helvetica', fontSize=8.5, textColor=C_NEAR_BLACK, leading=12)),
            ]
            qw_tbl = Table([qw_row], colWidths=[22*mm, 158*mm])
            qw_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), white),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,-1), 0.3, HexColor('#eeeeee')),
                ('LINEBEFORE', (0,0), (0,-1), 3, border_c),
            ]))
            story.append(qw_tbl)

        story.append(Spacer(1, 5*mm))

    # ── Upsell box ──
    up_tbl = Table([[Paragraph(
        "<b>GEO-Optimierungspaket Professional — EUR 149</b><br/>"
        "<font size='8.5'>7 fertige Optimierungstexte: 10 FAQ-Antworten | H1+Subheadline | 4 USP-Kacheln | "
        "20 lokale Keywords | Google Business Profil-Text | 3 Meta-Descriptions | Ueber-uns-Text neu<br/>"
        "Lieferung in 24 Stunden per E-Mail  |  kontakt@gernot-riedel.com  |  +43 676 7237811</font>",
        S('up', fontName='Helvetica', fontSize=9, textColor=C_GREEN, leading=14)
    )]], colWidths=[180*mm])
    up_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_GREEN),
        ('BOX', (0,0), (-1,-1), 2, C_GREEN),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(up_tbl)

    doc.build(story)
    return buf.getvalue()

# ─── ZAPIER WEBHOOK ───────────────────────────────────────────────────────────

def sende_webhook(betrieb, ort, email, url, typ, score_passed, score_total, zusammenfassung, checks):
    webhook_url = st.secrets.get("ZAPIER_WEBHOOK_URL", os.environ.get("ZAPIER_WEBHOOK_URL", ""))
    if not webhook_url:
        return
    robots = checks.get('robots', {})
    blocked_bots = robots.get('detail_blocked', []) if robots.get('is_robots') else []
    payload = {
        "betrieb": betrieb, "ort": ort, "email": email, "website": url, "typ": typ,
        "score": f"{score_passed}/{score_total}",
        "datum": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "zusammenfassung": zusammenfassung,
        "ki_bots_blockiert": blocked_bots,
        "produkt": "GEO-Optimierungspaket Professional",
        "preis": "149"
    }
    try:
        requests.post(webhook_url, json=payload, timeout=8)
    except Exception:
        pass

# ─── SESSION STATE INIT ───────────────────────────────────────────────────────
for key, default in [
    ('analyse_running', False),
    ('analyse_done', False),
    ('checks', {}),
    ('ai_result', None),
    ('form_betrieb', ''),
    ('form_ort', ''),
    ('form_url', ''),
    ('form_typ', 'Hotel (3–5 Sterne)'),
    ('form_email', ''),
    ('form_text', ''),
    ('fetch_status', ''),
    ('score_passed', 0),
    ('score_total', 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── UI ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="geo-header">
    <div class="geo-title">🏔️ GEO-Readiness Checker</div>
    <div class="geo-subtitle">Wie gut findet ChatGPT & Co. Ihren Betrieb?</div>
    <div class="geo-byline">Gernot Riedel Tourism Consulting · gernot-riedel.com</div>
</div>
""", unsafe_allow_html=True)

# ─── FORMULAR (kein st.form — verhindert alle Submit-Bugs) ────────────────────
st.markdown('<div class="form-card">', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    betrieb = st.text_input("🏨 Betriebsname", placeholder="Hotel Kaiserlodge",
                             value=st.session_state.form_betrieb, key="input_betrieb")
    ort = st.text_input("📍 Ort / Region", placeholder="Scheffau am Wilden Kaiser, Tirol",
                         value=st.session_state.form_ort, key="input_ort")
with col2:
    url_raw = st.text_input("🌐 Website-URL", placeholder="https://www.kaiserlodge.at",
                             value=st.session_state.form_url, key="input_url")
    typ = st.selectbox("🏷️ Betriebstyp", [
        "Hotel (3–5 Sterne)", "Pension / B&B", "Ferienwohnung / Chalet",
        "Resort / Wellness-Hotel", "Seilbahn / Bergbahn", "TVB / DMO", "Restaurant", "Sonstiges"
    ], key="input_typ")

email = st.text_input("📧 Ihre E-Mail-Adresse * (Pflichtfeld — für die Zusendung Ihrer Analyse)",
                       placeholder="ihre@email.at  ← Pflichtfeld",
                       value=st.session_state.form_email, key="input_email")

with st.expander("✏️ Website-Text manuell eingeben — bei Bot-Schutz oder JS-Seiten"):
    st.markdown("""
    <div class="info-blocked">
    <strong>Wann nötig?</strong> Viele Hotel-Websites blockieren automatischen Zugriff (Cloudflare, JS-Rendering).
    Die technischen Checks (HTTPS, robots.txt, Schema etc.) funktionieren trotzdem.
    Für die inhaltliche KI-Analyse: Startseite + Über uns + Zimmer-Text hier einfügen.
    </div>
    """, unsafe_allow_html=True)
    manueller_text = st.text_area(
        "Text einfügen:",
        placeholder="Willkommen im Hotel...\nUnsere Zimmer...\nLage und Anreise...",
        height=160,
        value=st.session_state.form_text,
        key="input_text"
    )

st.markdown('</div>', unsafe_allow_html=True)

# ─── SUBMIT BUTTON ────────────────────────────────────────────────────────────
if st.button("🔍 GEO-Analyse starten", type="primary", use_container_width=True):
    b = st.session_state.input_betrieb.strip()
    o = st.session_state.input_ort.strip()
    u = st.session_state.input_url.strip()

    e = st.session_state.input_email.strip()
    if not b or not o or not u or not e:
        if not b or not o or not u:
            st.error("Bitte Betriebsname, Ort und URL ausfüllen.")
        if not e:
            st.error("📧 Bitte E-Mail-Adresse eingeben — Ihre kostenlose Analyse wird dorthin gesendet.")
    else:
        # Werte in session_state speichern
        st.session_state.form_betrieb = b
        st.session_state.form_ort = o
        st.session_state.form_url = u
        st.session_state.form_typ = st.session_state.input_typ
        st.session_state.form_email = st.session_state.input_email.strip()
        st.session_state.form_text = st.session_state.input_text.strip()
        st.session_state.analyse_done = False
        st.session_state.analyse_running = True
        st.rerun()

# ─── ANALYSE (läuft nach rerun) ───────────────────────────────────────────────
if st.session_state.analyse_running:
    betrieb = st.session_state.form_betrieb
    ort = st.session_state.form_ort
    url = st.session_state.form_url
    typ = st.session_state.form_typ
    email = st.session_state.form_email
    manueller_text = st.session_state.form_text

    if not url.startswith('http'):
        url = 'https://' + url
        st.session_state.form_url = url

    # PHASE 1: Technische Checks
    with st.spinner("🔬 Technische Checks laufen..."):
        checks = run_technical_checks(url)

    fetch_status = checks.get('_fetch_status', 'blocked')

    if fetch_status == 'blocked' and not manueller_text.strip():
        st.markdown("""
        <div class="info-blocked">
        🚫 <strong>Website blockiert automatischen Zugriff</strong> (Bot-Schutz oder JavaScript-Rendering aktiv).<br><br>
        Die technischen Checks (HTTPS, robots.txt, Sitemap) wurden trotzdem durchgeführt.<br>
        Für die <strong>inhaltliche KI-Analyse</strong>: Bitte Website-Text oben im Feld einfügen und nochmals starten.
        </div>
        """, unsafe_allow_html=True)
    elif fetch_status == 'ok':
        st.markdown('<div class="info-manual">✅ Website erfolgreich analysiert</div>', unsafe_allow_html=True)

    # PHASE 2: Score
    score_passed, score_total = score_from_checks(checks)
    pct = round((score_passed / score_total * 100)) if score_total > 0 else 0

    if pct >= 80:
        verdict = "Gut aufgestellt"
        verdict_emoji = "✅"
    elif pct >= 55:
        verdict = "Verbesserungspotenzial"
        verdict_emoji = "⚠️"
    else:
        verdict = "Handlungsbedarf"
        verdict_emoji = "🔴"

    st.markdown(f"""
    <div class="score-summary">
        <div class="score-big">{score_passed}/{score_total}</div>
        <div class="score-label">TECHNISCHE CHECKS BESTANDEN</div>
        <div class="score-verdict">{verdict_emoji} {verdict}</div>
        <div class="score-note">🔬 Verifizierte Messwerte — keine KI-Schätzung</div>
    </div>
    """, unsafe_allow_html=True)

    # PHASE 3: Robots.txt Highlight (das Star-Feature)
    robots = checks.get('robots', {})
    if robots.get('exists'):
        blocked = robots.get('detail_blocked', [])
        if blocked:
            bot_list = ', '.join(blocked)
            st.markdown(f"""
            <div class="robots-alert">
            🚫 <strong>KI-Bots blockiert!</strong><br>
            Folgende KI-Systeme können diese Website laut robots.txt NICHT lesen:<br>
            <strong>{bot_list}</strong><br><br>
            <small>Das bedeutet: Diese KI-Systeme nennen den Betrieb bei Anfragen möglicherweise nicht.
            Sofortiger Handlungsbedarf — Lösung: robots.txt anpassen.</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="robots-ok">
            ✅ <strong>Alle KI-Bots haben Zugang</strong><br>
            robots.txt lässt ChatGPT, Claude, Perplexity & Co. zu — gute Ausgangslage für KI-Sichtbarkeit.
            </div>
            """, unsafe_allow_html=True)
    elif not robots.get('exists'):
        st.markdown("""
        <div class="info-blocked">
        ⚠️ <strong>robots.txt nicht gefunden</strong> — KI-Bots folgen dann Standard-Einstellungen.
        Eine explizite robots.txt wird empfohlen.
        </div>
        """, unsafe_allow_html=True)

    # PHASE 4: Checkliste
    st.subheader("📋 Technische Checkliste")
    st.caption("🔬 Alle Punkte sind verifizierte Messwerte — reproduzierbar und nachvollziehbar.")

    check_display_order = ['https', 'load_time', 'title', 'meta_desc', 'viewport',
                           'lang', 'canonical', 'schema', 'robots', 'sitemap']

    for key in check_display_order:
        check = checks.get(key, {})
        if not check:
            continue

        # Special handling for robots
        if check.get('is_robots'):
            if not check.get('exists'):
                icon = "⚠️"
                css_class = "warn"
                detail = "robots.txt nicht gefunden."
            elif check.get('pass'):
                icon = "✅"
                css_class = "pass"
                detail = "Alle KI-Bots erlaubt."
            else:
                icon = "❌"
                css_class = "fail"
                blocked_names = check.get('detail_blocked', [])
                detail = f"Blockiert: {', '.join(blocked_names)}" if blocked_names else "Einschränkungen gefunden."

            badge_html = '<span class="badge badge-measured">🔬 Gemessen</span>'
            st.markdown(f"""
            <div class="check-item {css_class}">
                <div class="check-icon">{icon}</div>
                <div class="check-content">
                    <div class="check-title">{check['name']} <span class="check-badge">{badge_html}</span></div>
                    <div class="check-detail">{detail}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            continue

        p = check.get('pass')
        warn = check.get('warn', False)

        if p is None:
            icon = "❓"
            css_class = "warn"
        elif warn:
            icon = "⚠️"
            css_class = "warn"
        elif p:
            icon = "✅"
            css_class = "pass"
        else:
            icon = "❌"
            css_class = "fail"

        badge_type = check.get('badge', 'measured')
        badge_labels = {'measured': '🔬 Gemessen', 'ai': '🤖 KI-Einschätzung'}
        badge_css = {'measured': 'badge-measured', 'ai': 'badge-ai'}
        badge_html = f'<span class="badge {badge_css.get(badge_type, "badge-measured")}">{badge_labels.get(badge_type, "")}</span>'

        detail = check.get('detail', '')

        st.markdown(f"""
        <div class="check-item {css_class}">
            <div class="check-icon">{icon}</div>
            <div class="check-content">
                <div class="check-title">{check['name']} <span class="check-badge">{badge_html}</span></div>
                <div class="check-detail">{detail}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # PHASE 5: KI-Analyse (wenn Text vorhanden)
    website_text = manueller_text.strip() if manueller_text.strip() else \
                   (checks.get('_raw_text', '') if fetch_status == 'ok' else '')

    ai_result = None
    if website_text or fetch_status == 'ok':
        st.divider()
        with st.spinner("🤖 Inhaltliche KI-Analyse läuft..."):
            try:
                ai_result = analyse_mit_claude(betrieb, ort, url, typ,
                                               website_text or f"Betrieb: {betrieb}, Ort: {ort}, Typ: {typ}",
                                               checks)
                st.session_state.ai_result = ai_result
            except Exception as e:
                st.warning(f"KI-Analyse konnte nicht abgeschlossen werden: {str(e)}")
    
    # Analyse abgeschlossen
    st.session_state.analyse_running = False
    st.session_state.analyse_done = True

    if ai_result:
        st.markdown('<div class="ai-section">', unsafe_allow_html=True)
        st.markdown('<div class="ai-section-title">🤖 Inhaltliche KI-Analyse</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="ai-disclaimer">
        🤖 <strong>KI-Einschätzung</strong> — Diese Bewertungen basieren auf Claude's Analyse des Website-Textes.
        Sie ergänzen die technischen Checks, sind aber keine Messwerte.
        </div>
        """, unsafe_allow_html=True)

        # Text-Bewertungen
        text_bew = ai_result.get('text_bewertung', {})
        labels = {
            'usp_klarheit': 'USP-Klarheit',
            'lokale_signale': 'Lokale Signale',
            'zielgruppen_klarheit': 'Zielgruppen-Klarheit',
            'faq_potential': 'FAQ-Potenzial'
        }
        for key, label in labels.items():
            item = text_bew.get(key, {})
            score = item.get('score', 0)
            kommentar = item.get('kommentar', '')
            bar_filled = "█" * score
            bar_empty = "░" * (10 - score)
            st.markdown(f"""
            <div class="check-item {'pass' if score >= 7 else 'warn' if score >= 4 else 'fail'}">
                <div class="check-icon">{'✅' if score >= 7 else '⚠️' if score >= 4 else '❌'}</div>
                <div class="check-content">
                    <div class="check-title">{label} — {score}/10 &nbsp;
                        <code style="font-size:0.75rem">{bar_filled}{bar_empty}</code>
                        <span class="check-badge"><span class="badge badge-ai">🤖 KI-Einschätzung</span></span>
                    </div>
                    <div class="check-detail">{kommentar}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Zusammenfassung
        st.markdown(f"""
        <div style="background:#f8f9fa;border-radius:8px;padding:1rem;margin:1rem 0;font-size:0.9rem;color:#444;">
        💬 {ai_result.get('zusammenfassung', '')}
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Quick Wins
        st.subheader("⚡ Quick Wins — sofort umsetzbar")
        for qw in ai_result.get('quickwins', []):
            prio = qw.get('prioritaet', 'MITTEL')
            css = 'qw-prio-high' if prio == 'HOCH' else 'qw-prio-mid'
            prio_color = '#cc3333' if prio == 'HOCH' else '#f4a261'
            st.markdown(f"""
            <div class="qw-card {css}">
                <div class="qw-title">
                    <span style="background:{prio_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;">{prio}</span>
                    &nbsp; {qw.get('massnahme', '')}
                </div>
                <div class="qw-impact">💡 {qw.get('impact', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    # PHASE 6: Lead-Webhook + PDF Download + Upsell
    st.divider()

    # Lead automatisch senden (Analyse ist kostenlos, E-Mail wurde gesammelt)
    zusammenfassung = ai_result.get('zusammenfassung', '') if ai_result else ''
    sende_webhook(betrieb, ort, email, url, typ, score_passed, score_total, zusammenfassung, checks)

    # PDF generieren
    pdf_bytes = generate_pdf(betrieb, ort, url, typ, checks, ai_result, score_passed, score_total)

    # PDF Download-Button
    st.markdown("""
    <div class="robots-ok" style="text-align:center;">
    ✅ <strong>Ihre kostenlose GEO-Analyse ist fertig!</strong><br>
    <small>Laden Sie Ihre Analyse als PDF herunter — direkt ausdruckbar und teilbar.</small>
    </div>
    """, unsafe_allow_html=True)

    st.download_button(
        label="📄  Analyse als PDF herunterladen (kostenlos)",
        data=pdf_bytes,
        file_name=f"GEO-Analyse_{betrieb.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.markdown("")

    # Upsell: €149 Paket
    st.subheader("📦 Möchten Sie mehr? GEO-Optimierungspaket Professional — €149")
    st.markdown("*Die Analyse zeigt das Problem — das Paket liefert die fertigen Lösungstexte:*")

    teaser = [
        ("❓", "10 FAQ-Antworten"), ("📝", "H1 + Subheadline"),
        ("⭐", "4 USP-Kacheln"), ("🔑", "20 Keywords"),
        ("📍", "Google Business"), ("🔍", "3 Meta-Descriptions"),
        ("🏨", "Über-uns-Text")
    ]
    cols = st.columns(3)
    for i, (emoji, name) in enumerate(teaser):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="teaser-item">
                <div class="teaser-lock">{emoji} 🔒</div>
                <div class="teaser-name">{name}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("")

    if st.button("🛒  Jetzt für €149 bestellen — Lieferung in 24 Stunden", use_container_width=True):
        st.success("""
        ✅ **Vielen Dank — Ihre Bestellung ist eingegangen!**

        Sie erhalten das vollständige GEO-Optimierungspaket mit allen 7 fertigen Texten
        innerhalb von 24 Stunden per E-Mail.

        Bei Fragen: kontakt@gernot-riedel.com | +43 676 7237811
        """)

    # Footer
    st.markdown(f"""
    <div class="geo-footer">
        Analyse durchgeführt am {datetime.now().strftime('%d.%m.%Y um %H:%M')} Uhr<br>
        🤖 Erstellt mit KI-Unterstützung |
        <a href="https://gernot-riedel.com" target="_blank">gernot-riedel.com</a> |
        #GernotGoesAI #GernotGoesKI<br>
        <small>Technische Checks = verifizierte Messwerte · KI-Einschätzungen sind keine Messwerte und können variieren.</small>
    </div>
    """, unsafe_allow_html=True)

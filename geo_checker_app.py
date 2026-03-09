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

# ─── UI ───────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="geo-header">
    <div class="geo-title">🏔️ GEO-Readiness Checker</div>
    <div class="geo-subtitle">Wie gut findet ChatGPT & Co. Ihren Betrieb?</div>
    <div class="geo-byline">Gernot Riedel Tourism Consulting · gernot-riedel.com</div>
</div>
""", unsafe_allow_html=True)

# ─── SESSION STATE INIT ───────────────────────────────────────────────────────
if 'manueller_text' not in st.session_state:
    st.session_state.manueller_text = ''

# ─── FORMULAR ─────────────────────────────────────────────────────────────────
with st.form("analyse_form"):
    st.markdown('<div class="form-card">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        betrieb = st.text_input("🏨 Betriebsname", placeholder="Hotel Kaiserlodge",
                                 key="betrieb_input")
        ort = st.text_input("📍 Ort / Region", placeholder="Scheffau am Wilden Kaiser, Tirol",
                             key="ort_input")
    with col2:
        url = st.text_input("🌐 Website-URL", placeholder="https://www.kaiserlodge.at",
                             key="url_input")
        typ = st.selectbox("🏷️ Betriebstyp", [
            "Hotel (3–5 Sterne)", "Pension / B&B", "Ferienwohnung / Chalet",
            "Resort / Wellness-Hotel", "Seilbahn / Bergbahn", "TVB / DMO", "Restaurant", "Sonstiges"
        ], key="typ_input")

    email = st.text_input("📧 E-Mail für das vollständige Paket (optional)",
                           placeholder="ihr@email.at", key="email_input")
    st.markdown('</div>', unsafe_allow_html=True)
    submitted = st.form_submit_button("🔍 GEO-Analyse starten", type="primary", use_container_width=True)

# Manueller Text AUSSERHALB des Forms (verhindert Streamlit-Bug mit expander+form)
st.markdown("""
<div class="info-blocked" style="margin-bottom:0.5rem;">
✏️ <strong>Website-Text manuell eingeben</strong> — bei Bot-Schutz oder JavaScript-Seiten<br>
<small>Viele Hotel-Websites blockieren automatischen Zugriff. Die technischen Checks funktionieren trotzdem.
Für die inhaltliche KI-Analyse: wichtigste Texte (Startseite, Über uns, Zimmer) hier einfügen.</small>
</div>
""", unsafe_allow_html=True)
manueller_text = st.text_area(
    "Startseite + Über uns + Zimmer (copy-paste aus dem Browser):",
    placeholder="Willkommen im Hotel Kaiserlodge...\nUnsere Zimmer und Suiten...\nLage und Anreise...",
    height=150,
    key="manueller_text",
    label_visibility="collapsed"
)

# ─── ANALYSE ──────────────────────────────────────────────────────────────────
if submitted:
    # Werte aus session_state lesen — zuverlässiger als direkte Variablen nach Submit
    betrieb = st.session_state.get('betrieb_input', betrieb).strip()
    ort = st.session_state.get('ort_input', ort).strip()
    url = st.session_state.get('url_input', url).strip()
    typ = st.session_state.get('typ_input', typ)
    email = st.session_state.get('email_input', email).strip()
    manueller_text = st.session_state.get('manueller_text', '').strip()

    if not betrieb or not ort or not url:
        st.error("Bitte Betriebsname, Ort und URL ausfüllen.")
        st.stop()

    if not url.startswith('http'):
        url = 'https://' + url

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
            except Exception as e:
                st.warning(f"KI-Analyse konnte nicht abgeschlossen werden: {str(e)}")

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

    # PHASE 6: Paket-Teaser
    st.divider()
    st.subheader("📦 GEO-Optimierungspaket Professional — €149")
    st.markdown("*7 fertig formulierte Texte und Optimierungen — sofort auf der Website einsetzbar:*")

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

    if email.strip():
        if st.button("🛒  Jetzt für €149 bestellen — Lieferung in 24 Stunden", type="primary", use_container_width=True):
            zusammenfassung = ai_result.get('zusammenfassung', '') if ai_result else ''
            sende_webhook(betrieb, ort, email, url, typ, score_passed, score_total, zusammenfassung, checks)
            st.success("""
            ✅ **Vielen Dank — Ihre Bestellung ist eingegangen!**

            Sie erhalten das vollständige GEO-Optimierungspaket mit allen 7 Lieferungen innerhalb von 24 Stunden per E-Mail.
            Bei Fragen: kontakt@gernot-riedel.com | +43 676 7237811
            """)
    else:
        st.info("📧 E-Mail oben eintragen, um das vollständige Paket zu bestellen.")

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

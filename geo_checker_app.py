import streamlit as st
import anthropic
import json
import csv
import io
import datetime
import re
import time
import urllib.request
from urllib.parse import urlparse

import gspread
from google.oauth2.service_account import Credentials

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
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #1a2332 0%, #2d4a3e 100%);
    padding: 36px 32px 28px; border-radius: 8px; margin-bottom: 28px;
}
.main-header h1 { color:#fff; font-size:30px; font-weight:700; margin:0 0 8px; line-height:1.2; }
.main-header h1 span { color:#c9a84c; }
.main-header p { color:rgba(255,255,255,0.72); font-size:15px; margin:0; line-height:1.6; }
.brand-tag {
    display:inline-block; background:rgba(201,168,76,0.2);
    border:1px solid rgba(201,168,76,0.4); color:#e8c97a;
    padding:4px 12px; border-radius:2px; font-size:11px;
    font-weight:600; letter-spacing:2px; text-transform:uppercase; margin-bottom:16px;
}

.score-card {
    background:linear-gradient(135deg,#0d6248 0%,#1a7a5a 100%);
    border-radius:8px; padding:28px 32px; text-align:center; margin:20px 0; color:white;
}
.score-number { font-size:64px; font-weight:700; line-height:1; }
.score-label { font-size:14px; opacity:0.8; margin-top:4px; letter-spacing:1px; text-transform:uppercase; }
.score-interpretation { font-size:17px; font-weight:600; margin-top:12px; }

.faktor-card {
    background:#f8f7f4; border-left:4px solid #0d6248;
    border-radius:4px; padding:14px 18px; margin:10px 0;
}
.faktor-name { font-weight:600; font-size:14px; color:#1a2332; }
.faktor-score { font-size:22px; font-weight:700; color:#0d6248; }
.faktor-kommentar { font-size:13px; color:#555; margin-top:4px; }

.quickwin-card {
    background:white; border:1px solid #e8e4dc;
    border-radius:6px; padding:14px 18px; margin:8px 0;
}
.qw-prio-hoch    { border-left:4px solid #c0392b; }
.qw-prio-mittel  { border-left:4px solid #e67e22; }
.qw-prio-niedrig { border-left:4px solid #27ae60; }
.qw-massnahme { font-weight:600; font-size:14px; color:#1a2332; }
.qw-impact    { font-size:13px; color:#666; margin-top:3px; }

.cta-box {
    background:linear-gradient(135deg,#1a2332 0%,#2d4a3e 100%);
    border-radius:8px; padding:28px 32px; text-align:center; margin:24px 0; color:white;
}
.cta-box h3 { color:#c9a84c; font-size:22px; margin:0 0 10px; }
.cta-box p  { opacity:0.85; font-size:15px; margin:0 0 18px; }

.robots-blocked {
    background:#fff3f3; border-left:4px solid #c0392b;
    padding:10px 14px; border-radius:4px; margin:4px 0; font-size:13px;
}
.robots-allowed {
    background:#f0fff4; border-left:4px solid #27ae60;
    padding:10px 14px; border-radius:4px; margin:4px 0; font-size:13px;
}

.badge-gemessen { background:#e8f5e9; color:#2e7d32; border-radius:3px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-ki       { background:#e3f2fd; color:#1565c0; border-radius:3px; padding:2px 8px; font-size:11px; font-weight:600; }

.footer-bar {
    background:#1a2332; color:rgba(255,255,255,0.6);
    text-align:center; padding:16px; border-radius:6px;
    font-size:12px; margin-top:40px;
}
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ───
for key, default in [
    ("analyse_done", False), ("result", None), ("lead_data", None),
    ("admin_logged_in", False), ("leads", [])
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════
# GOOGLE SHEETS
# ══════════════════════════════════════════════════════

SHEET_ID  = "1bNBtr9w__zlPL_5XETHhewu3TZAc7qAR1wm8sRO5WVI"
SHEET_TAB = "Leads"   # Tabellenblatt-Name — ggf. anpassen

def get_sheet():
    """Verbindet mit Google Sheets via Service Account aus Streamlit Secrets."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_TAB)


def write_lead_to_sheet(data: dict) -> bool:
    """Schreibt einen Lead als neue Zeile ins Google Sheet."""
    try:
        sheet = get_sheet()
        # Header anlegen falls Sheet leer
        if sheet.row_count < 1 or sheet.cell(1, 1).value != "Datum":
            sheet.insert_row(
                ["Datum", "Betrieb", "Ort", "E-Mail", "Website", "Typ", "Score", "Zusammenfassung"],
                index=1
            )
        sheet.append_row([
            datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            data.get("betrieb", ""),
            data.get("ort", ""),
            data.get("email", ""),
            data.get("website", ""),
            data.get("typ", ""),
            data.get("score", 0),
            data.get("zusammenfassung", ""),
        ])
        return True
    except Exception as e:
        st.warning(f"Google Sheets Eintrag fehlgeschlagen: {e}")
        return False


# ══════════════════════════════════════════════════════
# HILFSFUNKTIONEN
# ══════════════════════════════════════════════════════

def fetch_website_text(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 GEO-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>",  " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()[:8000]
    except Exception as e:
        return f"[Website konnte nicht geladen werden: {e}]"


def check_technical_facts(url: str) -> dict:
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    facts  = {"https": parsed.scheme == "https"}

    # robots.txt
    robots_text = ""
    try:
        req = urllib.request.Request(f"{base}/robots.txt", headers={"User-Agent": "GEO-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            robots_text = resp.read().decode("utf-8", errors="ignore")
        facts["robots_exists"] = True
    except Exception:
        facts["robots_exists"] = False

    # KI-Bot Crawlability
    AI_BOTS = {
        "GPTBot":          "OpenAI / ChatGPT",
        "ClaudeBot":       "Anthropic / Claude",
        "PerplexityBot":   "Perplexity",
        "Google-Extended": "Google AI (Gemini)",
        "Bytespider":      "TikTok / ByteDance",
    }
    blocked_bots, allowed_bots = [], []
    if robots_text:
        lines, current_ua, disallows = robots_text.lower().split("\n"), None, {}
        for line in lines:
            line = line.strip()
            if line.startswith("user-agent:"):
                current_ua = line.replace("user-agent:", "").strip()
                disallows.setdefault(current_ua, [])
            elif line.startswith("disallow:") and current_ua:
                disallows[current_ua].append(line.replace("disallow:", "").strip())
        for bot, label in AI_BOTS.items():
            bl = bot.lower()
            blocked = (bl in disallows and ("/" in disallows[bl] or "" in disallows[bl])) or \
                      ("*" in disallows and "/" in disallows["*"])
            (blocked_bots if blocked else allowed_bots).append({"bot": bot, "label": label})
    else:
        allowed_bots = [{"bot": b, "label": l} for b, l in AI_BOTS.items()]

    facts["blocked_bots"] = blocked_bots
    facts["allowed_bots"] = allowed_bots

    # sitemap.xml
    try:
        req = urllib.request.Request(f"{base}/sitemap.xml", headers={"User-Agent": "GEO-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            facts["sitemap_exists"] = resp.status == 200
    except Exception:
        facts["sitemap_exists"] = False

    # Ladezeit + HTML
    raw_html = ""
    try:
        t0 = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 GEO-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_html = resp.read().decode("utf-8", errors="ignore")
        facts["load_time"] = round(time.time() - t0, 2)
        facts["load_ok"]   = facts["load_time"] < 3.0
    except Exception:
        facts["load_time"] = None
        facts["load_ok"]   = False

    # Meta-Description
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', raw_html, re.I) or \
        re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']', raw_html, re.I)
    facts["meta_description"] = m.group(1).strip() if m else ""
    facts["meta_desc_ok"]     = bool(facts["meta_description"])

    facts["viewport"] = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', raw_html, re.I))

    lm = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', raw_html, re.I)
    facts["lang"]    = lm.group(1) if lm else ""
    facts["lang_ok"] = bool(facts["lang"])

    tm = re.search(r'<title[^>]*>(.*?)</title>', raw_html, re.I | re.DOTALL)
    facts["page_title"] = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else ""
    facts["title_ok"]   = bool(facts["page_title"])

    cm = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', raw_html, re.I)
    facts["canonical"]    = cm.group(1) if cm else ""
    facts["canonical_ok"] = bool(facts["canonical"])

    facts["schema_org"] = "schema.org" in raw_html.lower()
    return facts


def compute_technical_score(facts: dict) -> dict:
    checks = [
        {"name": "HTTPS-Verschlüsselung",      "ok": facts.get("https", False),
         "detail": "Aktiv ✅" if facts.get("https") else "Nicht aktiv ❌"},
        {"name": "Ladezeit unter 3 Sekunden",  "ok": facts.get("load_ok", False),
         "detail": (f"{facts['load_time']}s ✅" if facts.get("load_ok")
                    else (f"{facts['load_time']}s ❌" if facts.get("load_time") else "Nicht messbar ❌"))},
        {"name": "Meta-Description vorhanden", "ok": facts.get("meta_desc_ok", False),
         "detail": "Vorhanden ✅" if facts.get("meta_desc_ok") else "Fehlt ❌"},
        {"name": "Mobile Viewport-Tag",        "ok": facts.get("viewport", False),
         "detail": "Vorhanden ✅" if facts.get("viewport") else "Fehlt ❌"},
        {"name": "Sprach-Attribut (lang=)",    "ok": facts.get("lang_ok", False),
         "detail": f'lang="{facts["lang"]}" ✅' if facts.get("lang_ok") else "Fehlt ❌"},
        {"name": "Page Title vorhanden",       "ok": facts.get("title_ok", False),
         "detail": f'"{facts["page_title"][:50]}…" ✅' if facts.get("title_ok") else "Fehlt ❌"},
        {"name": "Canonical Tag gesetzt",      "ok": facts.get("canonical_ok", False),
         "detail": "Vorhanden ✅" if facts.get("canonical_ok") else "Fehlt ❌"},
        {"name": "Schema.org Markup",          "ok": facts.get("schema_org", False),
         "detail": "Gefunden ✅" if facts.get("schema_org") else "Nicht gefunden ❌"},
        {"name": "robots.txt — KI-Bots erlaubt", "ok": len(facts.get("blocked_bots", [])) == 0,
         "detail": "Alle KI-Bots erlaubt ✅" if len(facts.get("blocked_bots", [])) == 0
                   else f"{len(facts['blocked_bots'])} Bot(s) blockiert ❌"},
        {"name": "sitemap.xml vorhanden",      "ok": facts.get("sitemap_exists", False),
         "detail": "Gefunden ✅" if facts.get("sitemap_exists") else "Nicht gefunden ❌"},
    ]
    return {"checks": checks, "score": sum(2 for c in checks if c["ok"]), "max": 20}


def analyse_mit_claude(website_text: str, tech_score: int,
                       betrieb: str, ort: str, typ: str,
                       manual_text: str = "") -> dict | None:
    client   = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    combined = website_text + (f"\n\n[Zusatztext Betreiber]:\n{manual_text}" if manual_text.strip() else "")

    prompt = f"""Du bist GEO-Analyse-Experte für Tourismus-Websites im DACH-Raum.

BETRIEB: {betrieb} | ORT: {ort} | TYP: {typ}
TECHNISCHER SCORE (bereits gemessen): {tech_score}/20

WEBSITE-INHALT:
{combined}

Vergib Punkte für 3 inhaltliche Faktoren (je 0–10):
1. INHALTSQUALITÄT: Texte klar, strukturiert, KI-lesbar? FAQ vorhanden?
2. LOKALE RELEVANZ: Region, Lage, Aktivitäten, Saison erwähnt?
3. UNIQUE SELLING POINTS: Klare Alleinstellungsmerkmale kommuniziert?

KERNREGEL: NUR explizit auf der Website stehende Infos verwenden.
Regionale Daten NICHT dem Betrieb direkt zuschreiben.
Bei Unsicherheit: "bitte prüfen" statt Interpretation.

ANTWORTE NUR MIT GÜLTIGEM JSON:

{{
  "gesamtscore": {tech_score},
  "faktoren": [
    {{"name": "Technische Basis", "score": {tech_score}, "max": 20, "kommentar": "Gemessene technische Faktoren", "badge": "🔬 Gemessen"}},
    {{"name": "Inhaltsqualität",       "score": 0, "max": 10, "kommentar": "<1 Satz>", "badge": "🤖 KI-Einschätzung"}},
    {{"name": "Lokale Relevanz",        "score": 0, "max": 10, "kommentar": "<1 Satz>", "badge": "🤖 KI-Einschätzung"}},
    {{"name": "Unique Selling Points",  "score": 0, "max": 10, "kommentar": "<1 Satz>", "badge": "🤖 KI-Einschätzung"}}
  ],
  "quickwins": [
    {{"prioritaet": "Hoch",    "massnahme": "<Maßnahme>", "impact": "<Wirkung>"}},
    {{"prioritaet": "Hoch",    "massnahme": "<Maßnahme>", "impact": "<Wirkung>"}},
    {{"prioritaet": "Mittel",  "massnahme": "<Maßnahme>", "impact": "<Wirkung>"}},
    {{"prioritaet": "Mittel",  "massnahme": "<Maßnahme>", "impact": "<Wirkung>"}},
    {{"prioritaet": "Niedrig", "massnahme": "<Maßnahme>", "impact": "<Wirkung>"}}
  ],
  "zusammenfassung": "<2-3 Sätze, nur auf Basis gecrawlter Inhalte>"
}}"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = resp.content[0].text
    try:
        if "```" in raw:
            for p in raw.split("```"):
                p = p.strip()
                if p.startswith("json"): raw = p[4:].strip(); break
                elif p.startswith("{"): raw = p; break
        raw  = raw[raw.find("{"):raw.rfind("}")+1]
        data = json.loads(raw)
        # Gesamtscore korrekt berechnen
        ki_scores = sum(f["score"] for f in data["faktoren"] if f["badge"] == "🤖 KI-Einschätzung")
        data["gesamtscore"] = tech_score + ki_scores
        return data
    except Exception as e:
        st.error(f"JSON-Parsing Fehler: {e}")
        return None


def score_farbe(s):
    return "#27ae60" if s >= 35 else ("#e67e22" if s >= 20 else "#c0392b")

def score_interpretation(s):
    if s >= 40: return "🟢 Sehr gute KI-Sichtbarkeit — weiter optimieren"
    if s >= 30: return "🟡 Solide Basis — strukturierte Optimierung bringt messbar mehr"
    if s >= 20: return "🟠 Verbesserungspotenzial — KI-Sichtbarkeit ausbaubar"
    return "🔴 Kritisch — dieser Betrieb ist für KI-Suche nahezu unsichtbar"


# ══════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
  <div class="brand-tag">TÜV-zertifizierter KI-Trainer · DACH Tourismus</div>
  <h1>🏔 GEO-Readiness <span>Checker</span></h1>
  <p>Wie sichtbar ist Ihr Betrieb in ChatGPT, Perplexity und Google AI?<br>
  Kostenlose Analyse in 60 Sekunden — mit konkreten Maßnahmen.</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# FORMULAR
# ══════════════════════════════════════════════════════

if not st.session_state["analyse_done"]:
    st.subheader("Ihren Betrieb analysieren")

    col1, col2 = st.columns(2)
    with col1:
        betrieb = st.text_input("Name des Betriebs *", placeholder="z.B. Hotel Alpenstern")
        ort     = st.text_input("Ort / Destination *",  placeholder="z.B. St. Anton am Arlberg")
    with col2:
        website = st.text_input("Website-URL *", placeholder="https://www.hotel-alpenstern.at")
        typ     = st.selectbox("Betriebstyp *", [
            "Hotel (3–4 Sterne)", "Hotel (5 Sterne / Luxus)",
            "Pension / Gasthof", "Ferienwohnung / Appartement",
            "Ferienhaus / Chalet", "Boutique Hotel",
            "Wellnesshotel", "Tourismusverband / DMO", "Sonstiges"
        ])

    email = st.text_input(
        "Ihre E-Mail-Adresse * (für Rückfragen und weiterführende Tipps)",
        placeholder="max@muster.at"
    )

    with st.expander("⚙️ Website zeigt Fehler oder leere Ergebnisse?"):
        st.caption("Falls Ihre Website durch Cloudflare oder JavaScript geschützt ist, kopieren Sie den wichtigsten Text Ihrer Startseite hier hinein:")
        manual_text = st.text_area("Startseiten-Text (optional)", height=100,
                                   placeholder="Willkommen im Hotel Alpenstern…")

    st.caption("* Pflichtfelder — Ihre Daten werden vertraulich behandelt und nicht an Dritte weitergegeben.")

    if st.button("🔍 Kostenlose GEO-Analyse starten", type="primary", use_container_width=True):
        fehler = []
        if not betrieb.strip(): fehler.append("Bitte Betriebsnamen eingeben.")
        if not ort.strip():     fehler.append("Bitte Ort eingeben.")
        if not website.strip(): fehler.append("Bitte Website-URL eingeben.")
        if not email.strip() or "@" not in email: fehler.append("Bitte gültige E-Mail eingeben.")

        if fehler:
            for f in fehler: st.error(f)
        else:
            if not website.startswith("http"): website = "https://" + website

            with st.spinner("🔍 Analyse läuft… (ca. 30–60 Sekunden)"):
                prog = st.progress(0, text="Technische Faktoren messen…")
                facts       = check_technical_facts(website)
                tech_result = compute_technical_score(facts)
                prog.progress(30, text="Website-Inhalt laden…")

                website_text = fetch_website_text(website)
                prog.progress(55, text="KI-Analyse durchführen…")

                result = analyse_mit_claude(
                    website_text, tech_result["score"],
                    betrieb, ort, typ,
                    manual_text if "manual_text" in dir() else ""
                )
                prog.progress(85, text="Lead speichern…")

                if result:
                    result["tech_checks"]  = tech_result["checks"]
                    result["blocked_bots"] = facts.get("blocked_bots", [])
                    result["allowed_bots"] = facts.get("allowed_bots", [])

                    lead = {
                        "betrieb":         betrieb,
                        "ort":             ort,
                        "email":           email,
                        "website":         website,
                        "typ":             typ,
                        "score":           result.get("gesamtscore", 0),
                        "zusammenfassung": result.get("zusammenfassung", ""),
                    }
                    # Google Sheets — im Hintergrund, kein Abbruch bei Fehler
                    write_lead_to_sheet(lead)

                    # Lokal für Admin
                    st.session_state["leads"].append({
                        **lead,
                        "datum": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                    })

                    st.session_state["result"]       = result
                    st.session_state["lead_data"]    = lead
                    st.session_state["analyse_done"] = True
                    prog.progress(100, text="Fertig!")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("Analyse konnte nicht abgeschlossen werden. Bitte erneut versuchen.")


# ══════════════════════════════════════════════════════
# ERGEBNIS
# ══════════════════════════════════════════════════════

if st.session_state["analyse_done"] and st.session_state["result"]:
    result    = st.session_state["result"]
    lead_data = st.session_state["lead_data"]
    score     = result.get("gesamtscore", 0)

    # Score-Karte
    st.markdown(f"""
    <div class="score-card">
      <div class="score-number" style="color:{score_farbe(score)}">{score}</div>
      <div class="score-label">von 50 möglichen Punkten</div>
      <div class="score-interpretation">{score_interpretation(score)}</div>
    </div>
    """, unsafe_allow_html=True)

    st.info(f"📋 {result.get('zusammenfassung', '')}")

    # Faktoren
    st.subheader("📊 Faktoren im Detail")
    for f in result.get("faktoren", []):
        badge = (f'<span class="badge-gemessen">{f["badge"]}</span>'
                 if "Gemessen" in f.get("badge","")
                 else f'<span class="badge-ki">{f["badge"]}</span>')
        st.markdown(f"""
        <div class="faktor-card">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
              <div class="faktor-name">{f["name"]} &nbsp; {badge}</div>
              <div class="faktor-kommentar">{f["kommentar"]}</div>
            </div>
            <div class="faktor-score">{f["score"]}<span style="font-size:14px;color:#999">/{f.get("max",10)}</span></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Technische Einzelmessungen
    with st.expander("🔬 Technische Einzelmessungen (10 Checkpunkte)"):
        for c in result.get("tech_checks", []):
            st.markdown(f"{'✅' if c['ok'] else '❌'} **{c['name']}** — {c['detail']}")
        st.markdown("---")
        st.markdown("**🤖 KI-Bot Crawlability:**")
        for b in result.get("blocked_bots", []):
            st.markdown(f'<div class="robots-blocked">❌ <strong>{b["bot"]}</strong> ({b["label"]}) — blockiert</div>', unsafe_allow_html=True)
        for a in result.get("allowed_bots", []):
            st.markdown(f'<div class="robots-allowed">✅ <strong>{a["bot"]}</strong> ({a["label"]}) — darf crawlen</div>', unsafe_allow_html=True)

    # Quick Wins
    st.subheader("⚡ Ihre Top-5 Quick Wins")
    prio_css = {"Hoch": "qw-prio-hoch", "Mittel": "qw-prio-mittel", "Niedrig": "qw-prio-niedrig"}
    for qw in result.get("quickwins", []):
        st.markdown(f"""
        <div class="quickwin-card {prio_css.get(qw.get('prioritaet',''), '')}">
          <div class="qw-massnahme">{qw.get('prioritaet','')}: {qw.get('massnahme','')}</div>
          <div class="qw-impact">💡 {qw.get('impact','')}</div>
        </div>
        """, unsafe_allow_html=True)

    # CTA — Hinweis auf Beratung
    st.markdown(f"""
    <div class="cta-box">
      <h3>Möchten Sie mehr aus Ihrem Score herausholen?</h3>
      <p>
        Als TÜV-zertifizierter KI-Trainer mit 30+ Jahren Tourismus-Erfahrung im DACH-Raum
        helfe ich Ihnen, Ihren Betrieb in ChatGPT, Perplexity und Google AI sichtbar zu machen —
        mit fertigen Texten, konkreten Maßnahmen und ohne technisches Vorwissen.
      </p>
      <p style="font-size:13px; opacity:0.7;">
        GEO-Optimierungspaket · ReviewRadar · Workshops & Beratung
      </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.link_button(
            "🌐 gernot-riedel.com",
            "https://gernot-riedel.com",
            use_container_width=True
        )
    with col2:
        st.link_button(
            "📧 Kontakt aufnehmen",
            "mailto:kontakt@gernot-riedel.com?subject=GEO-Beratung%20Anfrage",
            use_container_width=True
        )

    st.divider()
    if st.button("🔄 Neue Analyse starten"):
        st.session_state["analyse_done"] = False
        st.session_state["result"]       = None
        st.session_state["lead_data"]    = None
        st.rerun()


# ══════════════════════════════════════════════════════
# ADMIN (passwortgeschützt)
# ══════════════════════════════════════════════════════

st.divider()
with st.expander("🔒 Admin-Bereich"):
    if not st.session_state["admin_logged_in"]:
        pw = st.text_input("Passwort", type="password", key="admin_pw")
        if st.button("Anmelden", key="admin_login"):
            if pw == st.secrets.get("ADMIN_PASSWORD", ""):
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("Falsches Passwort.")
    else:
        st.success("✅ Admin-Zugang aktiv")
        leads = st.session_state.get("leads", [])
        if leads:
            st.write(f"**{len(leads)} Lead(s) in dieser Session:**")
            for i, l in enumerate(leads, 1):
                st.write(f"{i}. **{l['betrieb']}** ({l['ort']}) — Score {l['score']}/50 — {l['email']} — {l.get('datum','')}")
            out = io.StringIO()
            w   = csv.DictWriter(out, fieldnames=["datum","betrieb","ort","email","website","typ","score","zusammenfassung"])
            w.writeheader(); w.writerows(leads)
            st.download_button("📥 CSV exportieren",
                               data=out.getvalue().encode("utf-8-sig"),
                               file_name=f"geo_leads_{datetime.date.today()}.csv",
                               mime="text/csv")
        else:
            st.info("Noch keine Leads in dieser Session.")

        st.markdown("---")
        st.markdown(f"🔗 [Alle Leads im Google Sheet öffnen](https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)")

        if st.button("🔓 Abmelden", key="admin_logout"):
            st.session_state["admin_logged_in"] = False
            st.rerun()


# ── FOOTER ──
st.markdown("""
<div class="footer-bar">
  <strong style="color:#c9a84c">Gernot Riedel Tourism Consulting</strong> &nbsp;|&nbsp;
  TÜV-zertifizierter KI-Trainer &nbsp;|&nbsp;
  kontakt@gernot-riedel.com &nbsp;|&nbsp;
  +43 676 7237811 &nbsp;|&nbsp;
  gernot-riedel.com
</div>
""", unsafe_allow_html=True)

import streamlit as st
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

.check-ok {
    background:#f0fff4; border-left:4px solid #27ae60;
    border-radius:4px; padding:12px 16px; margin:6px 0; font-size:14px;
}
.check-fail {
    background:#fff3f3; border-left:4px solid #c0392b;
    border-radius:4px; padding:12px 16px; margin:6px 0; font-size:14px;
}
.check-name { font-weight:600; color:#1a2332; }
.check-detail { color:#555; font-size:13px; margin-top:3px; }

.quickwin-card {
    background:white; border:1px solid #e8e4dc;
    border-radius:6px; padding:14px 18px; margin:8px 0;
}
.qw-hoch   { border-left:4px solid #c0392b; }
.qw-mittel { border-left:4px solid #e67e22; }
.qw-niedrig { border-left:4px solid #27ae60; }
.qw-titel { font-weight:600; font-size:14px; color:#1a2332; }
.qw-impact { font-size:13px; color:#666; margin-top:3px; }

.robots-blocked {
    background:#fff3f3; border-left:4px solid #c0392b;
    padding:10px 14px; border-radius:4px; margin:4px 0; font-size:13px;
}
.robots-allowed {
    background:#f0fff4; border-left:4px solid #27ae60;
    padding:10px 14px; border-radius:4px; margin:4px 0; font-size:13px;
}

.cta-box {
    background:linear-gradient(135deg,#1a2332 0%,#2d4a3e 100%);
    border-radius:8px; padding:28px 32px; text-align:center; margin:24px 0; color:white;
}
.cta-box h3 { color:#c9a84c; font-size:22px; margin:0 0 10px; }
.cta-box p  { opacity:0.85; font-size:15px; margin:0 0 18px; }

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
SHEET_TAB = "Leads"

def get_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_TAB)

def write_lead_to_sheet(data: dict) -> bool:
    try:
        sheet = get_sheet()
        if sheet.row_count < 1 or sheet.cell(1, 1).value != "Datum":
            sheet.insert_row(
                ["Datum", "Betrieb", "Ort", "E-Mail", "Website", "Typ", "Score", "Score %"],
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
            f"{round(data.get('score', 0) / 20 * 100)}%",
        ])
        return True
    except Exception as e:
        st.warning(f"Google Sheets: {e}")
        return False


# ══════════════════════════════════════════════════════
# TECHNISCHE MESSUNG
# ══════════════════════════════════════════════════════

def check_website(url: str) -> dict:
    """Misst alle 10 technischen GEO-Faktoren direkt und verifizierbar."""
    parsed = urlparse(url)
    base   = f"{parsed.scheme}://{parsed.netloc}"
    facts  = {"https": parsed.scheme == "https"}

    # robots.txt
    robots_text = ""
    try:
        req = urllib.request.Request(
            f"{base}/robots.txt", headers={"User-Agent": "GEO-Checker/1.0"}
        )
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
        req = urllib.request.Request(
            f"{base}/sitemap.xml", headers={"User-Agent": "GEO-Checker/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            facts["sitemap_exists"] = resp.status == 200
    except Exception:
        facts["sitemap_exists"] = False

    # Ladezeit + HTML
    raw_html = ""
    try:
        t0 = time.time()
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 GEO-Checker/1.0"}
        )
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
    facts["meta_desc"] = m.group(1).strip() if m else ""
    facts["meta_desc_ok"] = bool(facts["meta_desc"])

    # Viewport
    facts["viewport"] = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', raw_html, re.I))

    # lang=
    lm = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', raw_html, re.I)
    facts["lang"]    = lm.group(1) if lm else ""
    facts["lang_ok"] = bool(facts["lang"])

    # Page Title
    tm = re.search(r'<title[^>]*>(.*?)</title>', raw_html, re.I | re.DOTALL)
    facts["page_title"] = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else ""
    facts["title_ok"]   = bool(facts["page_title"])

    # Canonical
    cm = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', raw_html, re.I)
    facts["canonical"]    = cm.group(1) if cm else ""
    facts["canonical_ok"] = bool(facts["canonical"])

    # Schema.org
    facts["schema_org"] = "schema.org" in raw_html.lower()

    return facts


def build_checks(facts: dict) -> list:
    """Erstellt die 10 Checkpunkte mit Ergebnis und Quick-Win-Hinweis."""
    bots_ok = len(facts.get("blocked_bots", [])) == 0
    return [
        {
            "name":     "HTTPS-Verschlüsselung",
            "ok":       facts.get("https", False),
            "detail":   "Aktiv" if facts.get("https") else "Nicht aktiv",
            "quickwin": "HTTPS aktivieren — Pflicht für jede moderne Website und Vertrauenssignal für KI-Systeme.",
            "impact":   "Sicherheit & Vertrauen"
        },
        {
            "name":     "Ladezeit unter 3 Sekunden",
            "ok":       facts.get("load_ok", False),
            "detail":   (f"{facts['load_time']}s" if facts.get("load_time") else "Nicht messbar"),
            "quickwin": f"Ladezeit optimieren (aktuell {facts.get('load_time','?')}s) — KI-Crawler bevorzugen schnell ladende Seiten.",
            "impact":   "Crawlbarkeit & User Experience"
        },
        {
            "name":     "Meta-Description vorhanden",
            "ok":       facts.get("meta_desc_ok", False),
            "detail":   f'"{facts["meta_desc"][:60]}…"' if facts.get("meta_desc_ok") else "Fehlt",
            "quickwin": "Meta-Description ergänzen — kurze, keyword-reiche Beschreibung (max. 155 Zeichen) für jede Seite.",
            "impact":   "KI-Zitierbarkeit & Klickrate"
        },
        {
            "name":     "Mobile Viewport-Tag",
            "ok":       facts.get("viewport", False),
            "detail":   "Vorhanden" if facts.get("viewport") else "Fehlt",
            "quickwin": 'Viewport-Tag im HTML-Head ergänzen: <meta name="viewport" content="width=device-width, initial-scale=1">',
            "impact":   "Mobile Sichtbarkeit"
        },
        {
            "name":     "Sprach-Attribut (lang=)",
            "ok":       facts.get("lang_ok", False),
            "detail":   f'lang="{facts["lang"]}"' if facts.get("lang_ok") else "Fehlt",
            "quickwin": 'Sprache im HTML-Tag definieren: <html lang="de"> — wichtig für sprachspezifische KI-Antworten.',
            "impact":   "Sprachliche Einordnung"
        },
        {
            "name":     "Page Title vorhanden",
            "ok":       facts.get("title_ok", False),
            "detail":   f'"{facts["page_title"][:50]}…"' if facts.get("title_ok") else "Fehlt",
            "quickwin": "Page Title ergänzen — keyword-reich, max. 60 Zeichen, einzigartig pro Seite.",
            "impact":   "KI-Zitierbarkeit & Auffindbarkeit"
        },
        {
            "name":     "Canonical Tag gesetzt",
            "ok":       facts.get("canonical_ok", False),
            "detail":   "Vorhanden" if facts.get("canonical_ok") else "Fehlt",
            "quickwin": "Canonical Tag ergänzen — verhindert Duplicate Content und signalisiert die bevorzugte URL.",
            "impact":   "Technische SEO & KI-Indexierung"
        },
        {
            "name":     "Schema.org Markup",
            "ok":       facts.get("schema_org", False),
            "detail":   "Gefunden" if facts.get("schema_org") else "Nicht gefunden",
            "quickwin": "Schema.org Markup implementieren (z.B. Hotel, LodgingBusiness) — strukturierte Daten sind der wichtigste Faktor für KI-Zitierbarkeit.",
            "impact":   "KI-Zitierbarkeit — höchste Priorität"
        },
        {
            "name":     "robots.txt — KI-Bots erlaubt",
            "ok":       bots_ok,
            "detail":   "Alle KI-Bots erlaubt" if bots_ok else f"{len(facts.get('blocked_bots',[]))} Bot(s) blockiert",
            "quickwin": "robots.txt anpassen — GPTBot, ClaudeBot, PerplexityBot und Google-Extended dürfen crawlen.",
            "impact":   "KI-Sichtbarkeit direkt"
        },
        {
            "name":     "sitemap.xml vorhanden",
            "ok":       facts.get("sitemap_exists", False),
            "detail":   "Gefunden" if facts.get("sitemap_exists") else "Nicht gefunden",
            "quickwin": "sitemap.xml erstellen und in robots.txt verlinken — hilft KI-Crawlern alle Seiten zu finden.",
            "impact":   "Vollständige Indexierung"
        },
    ]


def score_farbe(s: int) -> str:
    if s >= 14: return "#27ae60"
    if s >= 8:  return "#e67e22"
    return "#c0392b"

def score_interpretation(s: int) -> str:
    if s >= 16: return "🟢 Sehr gute technische GEO-Basis — Inhalte optimieren"
    if s >= 12: return "🟡 Solide Basis — einige technische Lücken schließen"
    if s >= 6:  return "🟠 Technische Schwächen — KI-Sichtbarkeit stark eingeschränkt"
    return "🔴 Kritisch — grundlegende technische Voraussetzungen fehlen"


# ══════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
  <div class="brand-tag">TÜV-zertifizierter KI-Trainer · DACH Tourismus</div>
  <h1>🏔 GEO-Readiness <span>Checker</span></h1>
  <p>Wie sichtbar ist Ihr Betrieb in ChatGPT, Perplexity und Google AI?<br>
  Kostenlose technische Analyse in 30 Sekunden — 10 verifizierte Checkpunkte.</p>
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
        "Ihre E-Mail-Adresse * (für weiterführende Tipps)",
        placeholder="max@muster.at"
    )

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
            if not website.startswith("http"):
                website = "https://" + website

            with st.spinner("🔍 Website wird analysiert… (ca. 15–30 Sekunden)"):
                prog  = st.progress(0, text="Verbindung aufbauen…")
                facts = check_website(website)
                prog.progress(70, text="Ergebnisse auswerten…")
                checks = build_checks(facts)
                score  = sum(2 for c in checks if c["ok"])
                prog.progress(90, text="Lead speichern…")

                lead = {
                    "betrieb": betrieb, "ort": ort, "email": email,
                    "website": website, "typ": typ, "score": score,
                }
                write_lead_to_sheet(lead)
                st.session_state["leads"].append({
                    **lead,
                    "datum": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
                })

                st.session_state["result"] = {
                    "checks":       checks,
                    "score":        score,
                    "blocked_bots": facts.get("blocked_bots", []),
                    "allowed_bots": facts.get("allowed_bots", []),
                }
                st.session_state["lead_data"]    = lead
                st.session_state["analyse_done"] = True
                prog.progress(100, text="Fertig!")
                time.sleep(0.3)
                st.rerun()


# ══════════════════════════════════════════════════════
# ERGEBNIS
# ══════════════════════════════════════════════════════

if st.session_state["analyse_done"] and st.session_state["result"]:
    result    = st.session_state["result"]
    lead_data = st.session_state["lead_data"]
    score     = result["score"]
    checks    = result["checks"]

    # Score-Karte
    pct = round(score / 20 * 100)
    st.markdown(f"""
    <div class="score-card">
      <div class="score-number" style="color:{score_farbe(score)}">{score}</div>
      <div class="score-label">von 20 Punkten · {pct}% erreicht</div>
      <div class="score-interpretation">{score_interpretation(score)}</div>
    </div>
    """, unsafe_allow_html=True)

    # Checkpunkte
    st.subheader("🔬 10 Gemessene Checkpunkte")
    passed = sum(1 for c in checks if c["ok"])
    st.caption(f"{passed} von 10 Checkpunkten bestanden")

    for c in checks:
        css  = "check-ok" if c["ok"] else "check-fail"
        icon = "✅" if c["ok"] else "❌"
        st.markdown(f"""
        <div class="{css}">
          <div class="check-name">{icon} {c['name']}</div>
          <div class="check-detail">{c['detail']}</div>
        </div>
        """, unsafe_allow_html=True)

    # KI-Bot Detail
    with st.expander("🤖 KI-Bot Crawlability im Detail"):
        for b in result.get("blocked_bots", []):
            st.markdown(f'<div class="robots-blocked">❌ <strong>{b["bot"]}</strong> ({b["label"]}) — blockiert in robots.txt</div>', unsafe_allow_html=True)
        for a in result.get("allowed_bots", []):
            st.markdown(f'<div class="robots-allowed">✅ <strong>{a["bot"]}</strong> ({a["label"]}) — darf crawlen</div>', unsafe_allow_html=True)

    # Quick Wins — nur für fehlgeschlagene Checks
    failed = [c for c in checks if not c["ok"]]
    if failed:
        st.subheader("⚡ Ihre Quick Wins")
        prio_map = {0: ("Hoch", "qw-hoch"), 1: ("Hoch", "qw-hoch"),
                    2: ("Mittel", "qw-mittel"), 3: ("Mittel", "qw-mittel")}
        for i, c in enumerate(failed):
            prio, css = prio_map.get(i, ("Niedrig", "qw-niedrig"))
            st.markdown(f"""
            <div class="quickwin-card {css}">
              <div class="qw-titel">{prio}: {c['name']}</div>
              <div class="qw-impact">💡 {c['quickwin']}</div>
              <div class="qw-impact" style="color:#999;margin-top:4px">Wirkung: {c['impact']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("🎉 Alle technischen Checkpunkte bestanden!")

    # CTA
    st.markdown("""
    <div class="cta-box">
      <h3>Möchten Sie mehr aus Ihrem Score herausholen?</h3>
      <p>
        Als TÜV-zertifizierter KI-Trainer mit 30+ Jahren Tourismus-Erfahrung im DACH-Raum
        helfe ich Ihnen, Ihren Betrieb in ChatGPT, Perplexity und Google AI sichtbar zu machen —
        mit fertigen Texten, konkreten Maßnahmen und ohne technisches Vorwissen.
      </p>
      <p style="font-size:13px;opacity:0.7;">GEO-Optimierungspaket · ReviewRadar · Workshops & Beratung</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🌐 gernot-riedel.com", "https://gernot-riedel.com", use_container_width=True)
    with col2:
        st.link_button("📧 Kontakt aufnehmen",
                       "mailto:kontakt@gernot-riedel.com?subject=GEO-Beratung%20Anfrage",
                       use_container_width=True)

    st.divider()
    if st.button("🔄 Neue Analyse starten"):
        st.session_state["analyse_done"] = False
        st.session_state["result"]       = None
        st.session_state["lead_data"]    = None
        st.rerun()


# ══════════════════════════════════════════════════════
# ADMIN
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
                st.write(f"{i}. **{l['betrieb']}** ({l['ort']}) — {l['score']}/20 Pkt — {l['email']} — {l.get('datum','')}")
            out = io.StringIO()
            w   = csv.DictWriter(out, fieldnames=["datum","betrieb","ort","email","website","typ","score"])
            w.writeheader()
            w.writerows(leads)
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

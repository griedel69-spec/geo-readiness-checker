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

# ─── ANALYSE FUNCTION ───
def run_analysis(hotel_name, location, url, business_type):
    api_key = get_api_key()
    if not api_key:
        st.error("❌ API-Key nicht konfiguriert. Bitte in Streamlit Secrets eintragen (ANTHROPIC_API_KEY).")
        return None

    prompt = f"""Du bist ein Experte für GEO-Optimierung (Generative Engine Optimization) für Tourismus-Websites im DACH-Raum.

Analysiere folgende Website für KI-Suchmaschinen-Sichtbarkeit:
- Betrieb: {hotel_name}
- Ort: {location}
- Website: {url}
- Typ: {business_type}

Bewerte EXAKT diese 5 Faktoren auf einer Skala von 0–10:
1. FAQ-Sektion (Strukturierte Fragen & Antworten für KI-Suche)
2. H1/Headline-Optimierung (Ortsbezug, Haupt-USP, Keywords)
3. Lokale Keywords (Region, Bundesland, Aktivitäten, Saison)
4. NAP-Konsistenz (Name, Adresse, Telefon - Vollständigkeit & Konsistenz)
5. USP-Klarheit (Was macht diesen Betrieb einzigartig?)

Antworte NUR als valides JSON ohne Markdown:
{{
  "gesamtscore": <Zahl 0-50>,
  "faktoren": [
    {{"name": "FAQ-Sektion", "score": <0-10>, "kommentar": "<1 Satz>"}},
    {{"name": "H1-Optimierung", "score": <0-10>, "kommentar": "<1 Satz>"}},
    {{"name": "Lokale Keywords", "score": <0-10>, "kommentar": "<1 Satz>"}},
    {{"name": "NAP-Konsistenz", "score": <0-10>, "kommentar": "<1 Satz>"}},
    {{"name": "USP-Klarheit", "score": <0-10>, "kommentar": "<1 Satz>"}}
  ],
  "quickwins": [
    {{"prioritaet": "sofort", "massnahme": "<Maßnahme>", "impact": "<Effekt>"}},
    {{"prioritaet": "sofort", "massnahme": "<Maßnahme>", "impact": "<Effekt>"}},
    {{"prioritaet": "kurz", "massnahme": "<Maßnahme>", "impact": "<Effekt>"}},
    {{"prioritaet": "kurz", "massnahme": "<Maßnahme>", "impact": "<Effekt>"}},
    {{"prioritaet": "mittel", "massnahme": "<Maßnahme>", "impact": "<Effekt>"}}
  ],
  "zusammenfassung": "<2-3 Sätze Gesamtbewertung>"
}}"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    text = message.content[0].text.strip()
    return json.loads(text)

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
    pdf.cell(0, 6, sanitize(f"{r['location']} | {r['type']} | Erstellt am {r['date']}"), ln=True)

    # Score
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

        # Bar
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

    # Quick Wins
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

    # Footer CTA
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
        with st.spinner("KI analysiert Ihre Website... Das dauert ca. 30–60 Sekunden."):
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

            # Save lead
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

    # Score
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

    # Factors
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

    # Quick Wins
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

    # PDF Download
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

    # CTA — Detailberatung
    st.markdown("""
    <div class="cta-box">
        <h3 style="color:#c9a84c;margin:0 0 8px 0">🚀 Jetzt GEO-Optimierungspaket anfordern</h3>
        <p style="color:rgba(255,255,255,0.85);margin:0 0 6px 0;font-size:16px">
        <strong style="color:white">Nur € 149</strong> — Sie erhalten fertige, sofort einsetzbare Optimierungstexte:</p>
        <p style="color:rgba(255,255,255,0.75);margin:0 0 16px 0;font-size:14px">
        ✅ 10 FAQ-Fragen mit Antworten &nbsp;|&nbsp; ✅ Optimierte H1-Texte &nbsp;|&nbsp; 
        ✅ USP-Box für Startseite &nbsp;|&nbsp; ✅ 20 lokale Keywords<br>
        Umsetzung durch Sie, Ihren Mitarbeiter oder Ihre Webagentur.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Beratungsanfrage Button
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
        st.success("✅ Perfekt! Ihre Anfrage ist bei Gernot Riedel eingegangen. Sie erhalten innerhalb von 24 Stunden Ihre fertigen Optimierungstexte per E-Mail.")
        st.info("📧 Bei Fragen: kontakt@gernot-riedel.com | 📞 +43 676 7237811")

    # ReviewRadar Upsell
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

        # CSV Export
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

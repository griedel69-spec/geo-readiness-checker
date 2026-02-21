import streamlit as st
import requests
import json
import re
import time
from urllib.parse import quote_plus
import anthropic

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NAP-Konsistenz-Checker | Gernot Riedel Tourism Consulting",
    page_icon="🔍",
    layout="centered"
)

# ─── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .demo-banner {
    background: #e67e22; color: white; text-align: center;
    padding: 10px; border-radius: 6px; font-weight: 600;
    margin-bottom: 20px; font-size: 14px;
  }
  .score-box {
    border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 20px;
  }
  .score-good   { background: linear-gradient(135deg,#27ae60,#2ecc71); color:white; }
  .score-medium { background: linear-gradient(135deg,#e67e22,#f39c12); color:white; }
  .score-bad    { background: linear-gradient(135deg,#c0392b,#e74c3c); color:white; }
  .score-number { font-size: 3rem; font-weight: 800; }
  .issue-critical { background:#fff0ef; border-left:4px solid #e74c3c; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .issue-warning  { background:#fff8ec; border-left:4px solid #f39c12; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .issue-ok       { background:#f0fff5; border-left:4px solid #27ae60; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .footer-box { text-align:center; color:#888; font-size:13px; border-top:1px solid #e0e7ef; padding-top:20px; margin-top:30px; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ────────────────────────────────────────────────────────────────────
st.markdown('<div class="demo-banner">🎯 NAP-Konsistenz-Checker | Gernot Riedel Tourism Consulting</div>', unsafe_allow_html=True)
st.title("Ist Ihr Hotel überall konsistent auffindbar?")
st.markdown("Prüfen Sie automatisch, ob **Name, Adresse und Telefonnummer** auf den wichtigsten Plattformen übereinstimmen.")

# ─── HELPERS ───────────────────────────────────────────────────────────────────
def normalize(s):
    if not s:
        return ""
    s = s.lower()
    for a, b in [("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")]:
        s = s.replace(a, b)
    return re.sub(r"[-_.,\s/]+", " ", s).strip()

def clean_phone(p):
    return re.sub(r"[\s\-\/\(\)\+]", "", p or "")

# ─── GOOGLE PLACES LIVE LOOKUP ─────────────────────────────────────────────────
def get_google_places_data(hotel_name, city, api_key):
    query = f"{hotel_name} {city}"
    try:
        find_url = (
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
            f"?input={quote_plus(query)}&inputtype=textquery"
            "&fields=place_id,name"
            f"&key={api_key}"
        )
        r = requests.get(find_url, timeout=8)
        candidates = r.json().get("candidates", [])
        if not candidates:
            return {"platform": "Google Business", "note": "Kein Eintrag auf Google gefunden."}
        place_id = candidates[0]["place_id"]
        detail_url = (
            "https://maps.googleapis.com/maps/api/place/details/json"
            f"?place_id={place_id}"
            "&fields=name,formatted_address,formatted_phone_number,address_components"
            f"&key={api_key}"
        )
        r2 = requests.get(detail_url, timeout=8)
        result = r2.json().get("result", {})
        street = ""
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            if "street_number" in types:
                street = comp["long_name"] + " " + street
            if "route" in types:
                street = street + comp["long_name"]
        return {
            "platform": "Google Business",
            "name": result.get("name", ""),
            "address": street.strip() or result.get("formatted_address", ""),
            "phone": result.get("formatted_phone_number", ""),
            "source": "Google Places API (live)"
        }
    except Exception as e:
        return {"platform": "Google Business", "error": str(e)}

# ─── DEMO DATA GENERATOR ──────────────────────────────────────────────────────
def generate_demo_data(hotel_name, city, selected_platforms):
    """Realistische Demo-Inkonsistenzen für Workshop-Einsatz."""
    name_variants = [
        hotel_name,
        hotel_name.replace("Hotel ", "").replace(" Hotel", ""),
        hotel_name + " " + city.split()[-1],
        hotel_name.replace("-", " "),
        hotel_name,
        hotel_name,
    ]
    phone_base = "+43 5356 12345"
    phone_variants = [
        phone_base,
        phone_base.replace("+43 ", "0"),
        phone_base.replace(" ", ""),
        "+43-5356-12345",
        "",
        phone_base,
    ]
    addr_base = "Hauptstraße 12"
    addr_variants = [
        addr_base,
        addr_base.replace("straße", "str."),
        addr_base.replace("12", "12a"),
        "Dorfstraße 5",
        addr_base,
        addr_base,
    ]
    all_platforms = ["Google Business", "Booking.com", "TripAdvisor", "HolidayCheck", "Expedia", "Eigene Website"]
    result = []
    for i, platform in enumerate(all_platforms):
        if platform in selected_platforms:
            result.append({
                "platform": platform,
                "name": name_variants[i % len(name_variants)],
                "address": addr_variants[i % len(addr_variants)],
                "phone": phone_variants[i % len(phone_variants)],
                "source": f"{platform} (Demo)"
            })
    return result

# ─── CLAUDE AI ANALYSIS ────────────────────────────────────────────────────────
def analyze_with_claude(ref, platform_data, client):
    platforms_text = "\n".join([
        f"- {p['platform']}: Name='{p.get('name','')}', Adresse='{p.get('address','')}', Telefon='{p.get('phone','')}'"
        + (f" [HINWEIS: {p.get('note','')}]" if p.get("note") else "")
        + (f" [FEHLER: {p.get('error','')}]" if p.get("error") else "")
        for p in platform_data
    ])

    prompt = f"""Du bist ein NAP-Konsistenz-Experte für Hotels im DACH-Raum.

REFERENZ (offizielle Stammdaten):
- Name: {ref['name']}
- Straße: {ref['street']}
- Ort: {ref['city']}
- Telefon: {ref['phone']}

GEFUNDENE PLATTFORM-DATEN:
{platforms_text}

Analysiere die NAP-Konsistenz. Toleriere:
- Groß/Kleinschreibung, führende/nachfolgende Leerzeichen
- Telefon-Varianten (+43 5356 12345 = 05356/12345 = +435356 12345)
- Adress-Abkürzungen (Str. = Straße)

Markiere als KRITISCH: unterschiedlicher Name, falsche/fehlende Telefonnummer, andere Adresse
Markiere als WARNUNG: leere Felder, nicht prüfbar
Markiere als OK: konsistente Daten

Antworte NUR als JSON:
{{
  "score": 0-100,
  "bewertung": "Sehr gut|Gut|Verbesserungsbedarf|Kritisch",
  "zusammenfassung": "2 prägnante Sätze auf Deutsch",
  "plattformen": [
    {{
      "name": "Plattformname",
      "status": "ok|warning|critical",
      "issues": ["konkretes Issue auf Deutsch"],
      "gefundene_daten": {{"name": "...", "adresse": "...", "telefon": "..."}}
    }}
  ],
  "sofortmassnahmen": ["konkrete Maßnahme 1", "Maßnahme 2", "Maßnahme 3"]
}}"""

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
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
    except Exception as e:
        return {"error": str(e)}

# ─── MAIN FORM ─────────────────────────────────────────────────────────────────
with st.form("nap_form"):
    st.subheader("📋 Schritt 1: Ihre offiziellen Stammdaten")
    col1, col2 = st.columns(2)
    with col1:
        hotel_name = st.text_input("Offizieller Hotelname *", placeholder="Hotel Alpenblick Kitzbühel")
        street = st.text_input("Straße & Hausnummer *", placeholder="Hauptstraße 12")
    with col2:
        city = st.text_input("PLZ & Ort *", placeholder="6370 Kitzbühel")
        phone = st.text_input("Telefonnummer *", placeholder="+43 5356 12345")

    st.subheader("🌐 Schritt 2: Plattformen auswählen")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        check_google  = st.checkbox("🔵 Google Business", value=True)
        check_booking = st.checkbox("🟡 Booking.com", value=True)
    with col_p2:
        check_ta = st.checkbox("🟢 TripAdvisor", value=True)
        check_hc = st.checkbox("🔴 HolidayCheck")
    with col_p3:
        check_exp = st.checkbox("🔵 Expedia")
        check_web = st.checkbox("🌐 Eigene Website")

    mode = st.radio(
        "Analyse-Modus",
        ["🎭 Demo-Modus (für Workshops & Tests)", "🔴 Live-Analyse (Google Places API)"],
        help="Demo zeigt realistische Beispiel-Inkonsistenzen ohne echte API-Abfrage."
    )

    submitted = st.form_submit_button("🔍 NAP-Konsistenz jetzt prüfen", use_container_width=True)

# ─── RUN ANALYSIS ──────────────────────────────────────────────────────────────
if submitted:
    if not hotel_name or not street or not phone:
        st.error("Bitte Hotelname, Straße und Telefonnummer ausfüllen.")
        st.stop()

    selected = []
    if check_google:  selected.append("Google Business")
    if check_booking: selected.append("Booking.com")
    if check_ta:      selected.append("TripAdvisor")
    if check_hc:      selected.append("HolidayCheck")
    if check_exp:     selected.append("Expedia")
    if check_web:     selected.append("Eigene Website")

    if not selected:
        st.warning("Bitte mindestens eine Plattform auswählen.")
        st.stop()

    ref = {"name": hotel_name, "street": street, "city": city, "phone": phone}
    is_demo = "Demo" in mode

    with st.spinner("🔍 Analysiere Plattformen..."):
        if is_demo:
            platform_data = generate_demo_data(hotel_name, city, selected)
        else:
            platform_data = []
            google_key = st.secrets.get("GOOGLE_PLACES_API_KEY", "")
            if check_google:
                if google_key:
                    platform_data.append(get_google_places_data(hotel_name, city, google_key))
                else:
                    platform_data.append({"platform": "Google Business", "note": "Kein Google Places API-Key in Secrets hinterlegt."})
            for plat in [p for p in selected if p != "Google Business"]:
                platform_data.append({
                    "platform": plat,
                    "note": f"Automatisches Scraping ohne API nicht möglich — manuelle Prüfung empfohlen."
                })

        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            analysis = analyze_with_claude(ref, platform_data, client)
        except Exception as e:
            st.error(f"Fehler bei der KI-Analyse: {e}")
            st.stop()

    if "error" in analysis:
        st.error(f"Analyse-Fehler: {analysis['error']}")
        st.stop()

    # ── SCORE ─────────────────────────────────────────────────────────────────
    score = analysis.get("score", 0)
    score_class = "score-good" if score >= 80 else "score-medium" if score >= 50 else "score-bad"
    st.markdown(f"""
    <div class="score-box {score_class}">
      <div class="score-number">{score}%</div>
      <div style="font-size:1.3rem;font-weight:700;margin:8px 0">{analysis.get('bewertung','')}</div>
      <div style="font-size:0.95rem;opacity:0.9">{analysis.get('zusammenfassung','')}</div>
    </div>
    """, unsafe_allow_html=True)

    if is_demo:
        st.info("ℹ️ **Demo-Modus aktiv:** Zeigt realistische Beispiel-Inkonsistenzen für Workshop-Zwecke.")

    # ── PLATTFORM DETAILS ─────────────────────────────────────────────────────
    st.subheader("📋 Detailanalyse nach Plattform")
    for p in analysis.get("plattformen", []):
        status = p.get("status", "warning")
        icon = {"ok": "✅", "warning": "⚠️", "critical": "❌"}.get(status, "⚠️")
        issues_html = "<br>".join([f"• {i}" for i in p.get("issues", ["Keine Auffälligkeiten"])])
        gd = p.get("gefundene_daten", {})
        found_html = f"<small style='color:#666'>Gefunden → Name: <em>{gd.get('name','–')}</em> | Adresse: <em>{gd.get('adresse','–')}</em> | Tel: <em>{gd.get('telefon','–')}</em></small>" if any(gd.values()) else ""
        st.markdown(f"""
        <div class="issue-{status}">
          <strong>{icon} {p.get('name','')}</strong><br>
          {issues_html}<br>{found_html}
        </div>
        """, unsafe_allow_html=True)

    # ── SOFORTMASSNAHMEN ──────────────────────────────────────────────────────
    st.subheader("⚡ Sofortmaßnahmen")
    for i, action in enumerate(analysis.get("sofortmassnahmen", []), 1):
        st.markdown(f"**{i}.** {action}")

    # ── CTA ───────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🎯 Nächste Schritte mit Gernot Riedel Tourism Consulting")
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.markdown("**📦 GEO-Optimierungspaket — € 149**")
            st.markdown("FAQ, H1, USP, Keywords, Google Business Text, Meta-Descriptions, Über uns — alles KI-optimiert, fertig in 24h.")
            st.link_button("Jetzt bestellen →", "https://gernot-riedel.com", use_container_width=True)
    with col_b:
        with st.container(border=True):
            st.markdown("**⭐ ReviewRadar Professional — € 349**")
            st.markdown("400 Bewertungen ausgewertet, konkrete ROI-Maßnahmen, 90-Tage Implementierungsplan.")
            st.link_button("Anfragen →", "mailto:kontakt@gernot-riedel.com", use_container_width=True)

    st.markdown("""
    <div class="footer-box">
      <strong>Gernot Riedel Tourism Consulting</strong> | TÜV-zertifizierter KI-Trainer für Tourismus<br>
      kontakt@gernot-riedel.com | +43 676 7237811 | gernot-riedel.com
    </div>
    """, unsafe_allow_html=True)

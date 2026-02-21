import streamlit as st
import requests
import json
import re
from urllib.parse import quote_plus
import anthropic

st.set_page_config(
    page_title="NAP-Konsistenz-Checker | Gernot Riedel Tourism Consulting",
    page_icon="🔍",
    layout="centered"
)

st.markdown("""
<style>
  .top-banner { background:#1a3a5c; color:white; text-align:center; padding:10px;
    border-radius:6px; font-weight:600; margin-bottom:20px; font-size:14px; }
  .score-box { border-radius:12px; padding:24px; text-align:center; margin-bottom:20px; }
  .score-good   { background:linear-gradient(135deg,#27ae60,#2ecc71); color:white; }
  .score-medium { background:linear-gradient(135deg,#e67e22,#f39c12); color:white; }
  .score-bad    { background:linear-gradient(135deg,#c0392b,#e74c3c); color:white; }
  .score-number { font-size:3rem; font-weight:800; }
  .issue-critical { background:#fff0ef; border-left:4px solid #e74c3c; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .issue-warning  { background:#fff8ec; border-left:4px solid #f39c12; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .issue-ok       { background:#f0fff5; border-left:4px solid #27ae60; padding:10px 14px; border-radius:6px; margin-bottom:8px; }
  .google-auto { background:#e8f4fd; border:1px solid #2d6a9f; border-radius:8px;
    padding:12px; margin-bottom:16px; font-size:0.88rem; }
  .footer-box { text-align:center; color:#888; font-size:13px;
    border-top:1px solid #e0e7ef; padding-top:20px; margin-top:30px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-banner">🔍 NAP-Konsistenz-Checker | Gernot Riedel Tourism Consulting</div>', unsafe_allow_html=True)
st.title("Ist Ihr Hotel überall konsistent auffindbar?")
st.markdown("""
**So funktioniert das Tool:**
- 🔵 **Google Business** → wird automatisch abgerufen
- 🟡🟢🔴 **Andere Plattformen** → Sie tragen ein, was dort aktuell steht (3 Minuten Aufwand)
- 🤖 **Claude KI** → analysiert alle Daten und findet Inkonsistenzen
""")

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def get_google_data(name, city, api_key):
    try:
        query = f"{name} {city}"
        find_url = (
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
            f"?input={quote_plus(query)}&inputtype=textquery"
            "&fields=place_id,name"
            f"&key={api_key}"
        )
        r = requests.get(find_url, timeout=8)
        candidates = r.json().get("candidates", [])
        if not candidates:
            return None, "Kein Google Business Eintrag gefunden."
        place_id = candidates[0]["place_id"]
        detail_url = (
            "https://maps.googleapis.com/maps/api/place/details/json"
            f"?place_id={place_id}"
            "&fields=name,formatted_address,formatted_phone_number,address_components"
            f"&key={api_key}"
        )
        r2 = requests.get(detail_url, timeout=8)
        result = r2.json().get("result", {})
        street_num, route = "", ""
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            if "street_number" in types: street_num = comp["long_name"]
            if "route" in types: route = comp["long_name"]
        street = f"{route} {street_num}".strip() or result.get("formatted_address", "")
        return {
            "platform": "Google Business",
            "name":    result.get("name", ""),
            "address": street,
            "phone":   result.get("formatted_phone_number", ""),
            "auto":    True
        }, None
    except Exception as e:
        return None, str(e)

def analyze_nap(ref, platforms, client):
    lines = []
    for p in platforms:
        line = (f"- {p['platform']}: "
                f"Name='{p.get('name','')}' | "
                f"Adresse='{p.get('address','')}' | "
                f"Telefon='{p.get('phone','')}'"
                + (" [AUTO: Google Places API]" if p.get("auto") else " [manuell]")
                + (f" [HINWEIS: {p['note']}]" if p.get("note") else ""))
        lines.append(line)

    prompt = f"""Du bist NAP-Konsistenz-Experte für Hotels im DACH-Raum.

OFFIZIELLE STAMMDATEN DES HOTELS:
- Name: {ref['name']}
- Straße: {ref['street']}
- Ort: {ref['city']}
- Telefon: {ref['phone']}

EINGETRAGENE PLATTFORM-DATEN:
{chr(10).join(lines)}

Analysiere Konsistenz. Toleriere:
- Groß/Kleinschreibung
- Telefon-Varianten (+43 5356 12345 = 05356/12345 = +435356 12345)
- Adress-Abkürzungen (Str. = Straße)
- Leerzeichen-Varianten

KRITISCH: anderer Name, falsche Adresse, falsche/fehlende Telefonnummer
WARNUNG: leere Felder, nicht verifizierbar
OK: konsistente Daten

Antworte NUR als JSON ohne Markdown:
{{
  "score": 0-100,
  "bewertung": "Sehr gut|Gut|Verbesserungsbedarf|Kritisch",
  "zusammenfassung": "2 prägnante Sätze auf Deutsch",
  "plattformen": [
    {{
      "name": "Plattformname",
      "status": "ok|warning|critical",
      "issues": ["konkretes Issue auf Deutsch"],
      "gefunden": {{"name": "...", "adresse": "...", "telefon": "..."}}
    }}
  ],
  "sofortmassnahmen": ["Konkrete Maßnahme 1", "Maßnahme 2", "Maßnahme 3"]
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
            if text.startswith("json"): text = text[4:]
        s, e = text.find("{"), text.rfind("}") + 1
        return json.loads(text[s:e])
    except Exception as ex:
        return {"error": str(ex)}

# ─── SCHRITT 1: STAMMDATEN ────────────────────────────────────────────────────
st.subheader("📋 Schritt 1: Ihre offiziellen Stammdaten")
st.caption("Das ist Ihre Referenz — so sollen alle Plattformen eingetragen sein.")

c1, c2 = st.columns(2)
with c1:
    hotel_name = st.text_input("Offizieller Hotelname *", placeholder="Hotel Alpenblick Kitzbühel")
    street     = st.text_input("Straße & Hausnummer *",   placeholder="Hauptstraße 12")
with c2:
    city  = st.text_input("PLZ & Ort *",      placeholder="6370 Kitzbühel")
    phone = st.text_input("Telefonnummer *",  placeholder="+43 5356 12345")

st.divider()

# ─── SCHRITT 2: PLATTFORMEN ───────────────────────────────────────────────────
st.subheader("🌐 Schritt 2: Plattform-Daten eingeben")

google_key = st.secrets.get("GOOGLE_PLACES_API_KEY", "")

if google_key:
    st.markdown('<div class="google-auto">🔵 <strong>Google Business</strong> wird beim Prüfen automatisch via Google Places API abgerufen — kein Eintrag nötig.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="google-auto">🔵 <strong>Google Business</strong> — kein API Key hinterlegt. Bitte manuell eintragen.</div>', unsafe_allow_html=True)

# Plattform-Definitionen
PLATFORMS = [
    {"key": "booking",      "label": "🟡 Booking.com",    "url": "https://www.booking.com", "default": True},
    {"key": "tripadvisor",  "label": "🟢 TripAdvisor",    "url": "https://www.tripadvisor.com", "default": True},
    {"key": "holidaycheck", "label": "🔴 HolidayCheck",   "url": "https://www.holidaycheck.at", "default": False},
    {"key": "expedia",      "label": "🔵 Expedia",        "url": "https://www.expedia.com", "default": False},
    {"key": "website",      "label": "🌐 Eigene Website", "url": "", "default": True},
]
if not google_key:
    PLATFORMS.insert(0, {"key": "google", "label": "🔵 Google Business", "url": "https://business.google.com", "default": True})

manual_inputs = {}
for p in PLATFORMS:
    with st.expander(f"{p['label']}", expanded=p["default"]):
        if p.get("url"):
            st.caption(f"Öffnen Sie: {p['url']} → suchen Sie Ihren Betrieb → tragen Sie die dort gezeigten Daten ein.")
        active = st.checkbox("Auf dieser Plattform gelistet", value=p["default"], key=f"chk_{p['key']}")
        if active:
            col1, col2, col3 = st.columns(3)
            with col1: n = st.text_input("Name wie eingetragen",    key=f"n_{p['key']}", placeholder=hotel_name or "Hotelname")
            with col2: a = st.text_input("Straße wie eingetragen",  key=f"a_{p['key']}", placeholder="Hauptstraße 12")
            with col3: t = st.text_input("Telefon wie eingetragen", key=f"t_{p['key']}", placeholder="+43 5356 12345")
            manual_inputs[p["key"]] = {"label": p["label"], "name": n, "address": a, "phone": t, "active": True}
        else:
            manual_inputs[p["key"]] = {"active": False}

st.divider()
run = st.button("🔍 NAP-Konsistenz jetzt prüfen", use_container_width=True, type="primary")

# ─── ANALYSE ──────────────────────────────────────────────────────────────────
if run:
    if not hotel_name or not street or not phone:
        st.error("Bitte Hotelname, Straße und Telefonnummer ausfüllen.")
        st.stop()

    ref = {"name": hotel_name, "street": street, "city": city, "phone": phone}
    platforms_data = []

    with st.spinner("Analysiere..."):

        # Google automatisch
        if google_key:
            gdata, gerr = get_google_data(hotel_name, city, google_key)
            if gdata:
                st.success(f"✅ Google Business automatisch gefunden: **{gdata['name']}** | {gdata.get('address','')} | {gdata.get('phone','')}")
                platforms_data.append(gdata)
            else:
                st.warning(f"⚠️ Google Business: {gerr}")
                platforms_data.append({"platform": "Google Business", "name": "", "address": "", "phone": "", "note": gerr})

        # Manuelle Eingaben
        for key, data in manual_inputs.items():
            if not data.get("active"): continue
            label = next((p["label"] for p in PLATFORMS if p["key"] == key), key)
            if not any([data.get("name"), data.get("address"), data.get("phone")]):
                platforms_data.append({"platform": label, "name": "", "address": "", "phone": "", "note": "Keine Daten eingetragen"})
            else:
                platforms_data.append({
                    "platform": label,
                    "name":    data.get("name", ""),
                    "address": data.get("address", ""),
                    "phone":   data.get("phone", ""),
                })

        if not platforms_data:
            st.warning("Keine Plattformdaten zum Prüfen vorhanden.")
            st.stop()

        # Claude Analyse
        try:
            client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
            result = analyze_nap(ref, platforms_data, client)
        except Exception as e:
            st.error(f"Fehler: {e}")
            st.stop()

    if "error" in result:
        st.error(f"Analyse-Fehler: {result['error']}")
        st.stop()

    # ── SCORE ─────────────────────────────────────────────────────────────────
    score = result.get("score", 0)
    cls   = "score-good" if score >= 80 else "score-medium" if score >= 50 else "score-bad"
    st.markdown(f"""
    <div class="score-box {cls}">
      <div class="score-number">{score}%</div>
      <div style="font-size:1.3rem;font-weight:700;margin:8px 0">{result.get('bewertung','')}</div>
      <div style="font-size:0.95rem;opacity:0.9">{result.get('zusammenfassung','')}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── DETAILS ───────────────────────────────────────────────────────────────
    st.subheader("📋 Detailanalyse nach Plattform")
    for p in result.get("plattformen", []):
        status = p.get("status", "warning")
        icon   = {"ok": "✅", "warning": "⚠️", "critical": "❌"}.get(status, "⚠️")
        issues = "<br>".join([f"• {i}" for i in p.get("issues", ["–"])])
        gd     = p.get("gefunden", {})
        found  = (f"<small style='color:#555'>Gefunden → "
                  f"Name: <em>{gd.get('name','–')}</em> | "
                  f"Adresse: <em>{gd.get('adresse','–')}</em> | "
                  f"Tel: <em>{gd.get('telefon','–')}</em></small>") if any(gd.values()) else ""
        st.markdown(
            f'<div class="issue-{status}"><strong>{icon} {p.get("name","")}</strong>'
            f'<br>{issues}<br>{found}</div>',
            unsafe_allow_html=True
        )

    # ── MASSNAHMEN ────────────────────────────────────────────────────────────
    st.subheader("⚡ Sofortmaßnahmen")
    for i, action in enumerate(result.get("sofortmassnahmen", []), 1):
        st.markdown(f"**{i}.** {action}")

    # ── CTA ───────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🎯 Professionelle Unterstützung")
    ca, cb = st.columns(2)
    with ca:
        with st.container(border=True):
            st.markdown("**📦 GEO-Optimierungspaket — € 149**")
            st.markdown("FAQ, H1, USP, Keywords, Google Business Text, Meta-Descriptions — fertig in 24h.")
            st.link_button("Jetzt bestellen →", "https://gernot-riedel.com", use_container_width=True)
    with cb:
        with st.container(border=True):
            st.markdown("**⭐ ReviewRadar Professional — € 349**")
            st.markdown("400 Bewertungen ausgewertet, konkrete ROI-Maßnahmen.")
            st.link_button("Anfragen →", "mailto:kontakt@gernot-riedel.com", use_container_width=True)

    st.markdown("""
    <div class="footer-box">
      <strong>Gernot Riedel Tourism Consulting</strong> | TÜV-zertifizierter KI-Trainer für Tourismus<br>
      kontakt@gernot-riedel.com | +43 676 7237811 | gernot-riedel.com
    </div>
    """, unsafe_allow_html=True)

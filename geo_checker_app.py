import streamlit as st
import anthropic
import json
import requests
from datetime import datetime

# Konfiguration & Secrets
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
ZAPIER_WEBHOOK_URL = st.secrets["ZAPIER_WEBHOOK_URL"]

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def analyze_website(name, ort, url, typ, content):
    # Der verbesserte "Expert-Prompt" zur Vermeidung generischer Antworten
    system_prompt = f"""
    Du bist ein Experte für GEO (Generative Engine Optimization) im Tourismus. 
    Deine Aufgabe ist es, die Website von '{name}' in '{ort}' zu analysieren.
    
    KERNREGELN:
    1. KEINE HALLUZINATIONEN: Behaupte niemals, dass Informationen fehlen, wenn sie auf der Website stehen.
    2. H1 vs H2: Wenn der Ort/Region nicht in der H1, aber in der H2 steht, bewerte dies als 'vorhanden, aber optimierbar' (Teilpunkte).
    3. FAQ-DETEKTION: Suche aktiv nach Fragezeichen, Akkordeons oder Sektionen wie 'Wissenswertes' oder 'Anreise'. Wenn vorhanden, lobe dies und empfehle lediglich die Umwandlung in strukturierte Daten.
    4. INDIVIDUELLER SCORE: Ein SEO-gepflegter Betrieb muss deutlich mehr Punkte (z.B. 35-45) erhalten als ein ungepflegter (10-20).
    5. NAP-ERKLÄRUNG: Erkläre bei der NAP-Konsistenz kurz, dass es um die identische Schreibweise von Name, Adresse und Telefonnummer im Netz geht.

    AUSGABE-FORMAT: Ausschließlich JSON.
    """

    user_prompt = f"""
    Analysiere diesen Website-Content für den Betrieb {name} ({typ}) in {ort}:
    URL: {url}
    Content: {content}

    Erstelle das GEO-Optimierungspaket gemäß der definierten JSON-Struktur. 
    Achte darauf, dass die 'paket'-Inhalte (FAQ, H1, USP, Keywords, Google Business, Meta, Über uns) 
    STRENG auf den Fakten der Website basieren. Keine Erfindungen von regionalen Features, die der Betrieb nicht bietet.
    """

    response = client.messages.create(
        model="model="claude-3-5-sonnet-latest", # Oder dein bevorzugtes Modell
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    # Robustes JSON-Parsing
    text = response.content[0].text
    try:
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        st.error(f"Fehler beim Parsen der KI-Antwort: {e}")
        return None

# --- Streamlit UI Logik ---
st.title("🏔️ GEO-Readiness Checker für Tourismus")
st.write("Analysiere deine Website für die Welt von ChatGPT, Perplexity & Co.")

with st.form("checker_form"):
    betrieb = st.text_input("Name des Betriebs")
    ort = st.text_input("Ort / Region")
    url = st.text_input("Website-URL")
    typ = st.selectbox("Betriebstyp", ["Hotel", "Appartement/Ferienwohnung", "DMO/TVB", "Ausflugsziel"])
    email = st.text_input("Deine E-Mail für den Report")
    submit = st.form_submit_button("Analyse starten")

if submit and url:
    with st.spinner("Analysiere Website und erstelle GEO-Paket..."):
        # Hier fetch_content Logik (simuliert oder via Tool)
        # Für das Beispiel nutzen wir einen Platzhalter-Content
        website_content = "Hier stehen die extrahierten Texte der Website..." 
        
        result = analyze_website(betrieb, ort, url, typ, website_content)
        
        if result:
            # Anzeige der Ergebnisse (Score, Faktoren, Quick-Wins sichtbar)
            st.metric("Dein GEO-Score", f"{result['gesamtscore']} / 50")
            
            for f in result['faktoren']:
                st.write(f"**{f['name']} ({f['score']}/10):** {f['kommentar']}")
            
            # Button für Kauf / Zapier-Webhook
            if st.button("Jetzt vollständiges GEO-Optimierungspaket für € 149 bestellen"):
                payload = {
                    "betrieb": betrieb,
                    "ort": ort,
                    "email": email,
                    "website": url,
                    "typ": typ,
                    "score": result['gesamtscore'],
                    "datum": datetime.now().strftime("%d.%m.%Y"),
                    "zusammenfassung": result['zusammenfassung'],
                    "faktoren": result['faktoren'],
                    "quickwins": result['quickwins'],
                    "produkt": "GEO-Optimierungspaket Professional",
                    "preis": "149"
                }
                r = requests.post(ZAPIER_WEBHOOK_URL, json=payload)
                if r.status_code == 200:
                    st.success("Anfrage gesendet! Gernot Riedel wird sich innerhalb von 24h bei dir melden.")

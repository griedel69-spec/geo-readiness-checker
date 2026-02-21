---
name: geo-checker-tourism
description: GEO-Readiness Checker and optimization package creation for tourism businesses in the DACH region (Austria, Germany, Switzerland). Use when creating a GEO optimization package for a hotel, analyzing a tourism website for AI visibility, or developing the Streamlit app code. Also includes automated NAP consistency check (Name, Address, Phone) across platforms.
---

# GEO-Checker Tourism — Skill für Gernot Riedel Tourism Consulting

Automatisierte GEO-Optimierungspaket-Erstellung für Tourismus-Betriebe (Hotels, TVBs, DMOs) im DACH-Raum. Kombiniert Website-Analyse mit fertig formulierten Optimierungstexten als verkaufbares Produkt (€ 149). **Beinhaltet jetzt auch automatische NAP-Konsistenz-Prüfung als Bonus-Lieferung.**

---

## Produktportfolio

### GEO-Optimierungspaket Professional — € 149 (einmalig)
Das Kernprodukt. 7 fertige Lieferungen + 1 Bonus-Lieferung für einen Betrieb:

1. **FAQ-Sektion** — 10 Fragen & Antworten, KI-optimiert
2. **H1-Titel + Subheadline** — Startseite neu, max 70 / 120 Zeichen
3. **USP-Box** — 4 Alleinstellungsmerkmale mit Emoji, Titel, 1 Satz
4. **Lokale Keywords** — 20 Begriffe für die Region
5. **Google Business Profil-Text** — max 750 Zeichen, keyword-reich
6. **Meta-Descriptions** — Startseite, Zimmer, Preise (je max 155 Zeichen)
7. **"Über uns" neu** — 250–300 Wörter, KI-lesbar, mit Geschichte/Lage/USPs
8. **BONUS: NAP-Konsistenz-Report** — automatische Plattform-Prüfung (kein Aufpreis)

**Preis:** € 149 einmalig, kein Abo
**Lieferung:** Fertig formatiertes Dokument per E-Mail innerhalb 24h
**Aufwand Gernot:** ca. 25 Minuten pro Betrieb (inkl. NAP)

### ReviewRadar — ab € 149 (einmalig)
Upsell nach GEO-Paket. Bewertungsanalyse für Hotels.
- Quick Insight: € 149 (1 Plattform, 200 Bewertungen)
- Professional: € 349 (2 Plattformen, 400 Bewertungen) ← Bestseller
- Premium: € 599 (4 Plattformen, 800 Bewertungen + Wettbewerb)

Link: gernot-riedel.com/hotelbewertungen-analyse-mehr-umsatz-direktbuchungen-reviewradar/

---

## Workflow: Vollständiges Paket für einen Betrieb erstellen

### Schritt 1: Website analysieren
```
web_fetch(url) → Inhalte lesen
```
Relevante Daten notieren: Name, Adresse, Telefon, Zimmertypen, USPs, Region, Aktivitäten, Besonderheiten.

### Schritt 2: NAP-Konsistenz prüfen (automatisch via web_search)

**IMMER gleichzeitig mit Schritt 1 durchführen — kein Zusatzaufwand!**

```
web_search("[Betriebsname] [Ort] Google Business Booking TripAdvisor Adresse Telefon")
web_search("[Betriebsname] [Ort] NAP Konsistenz Plattformen")
```

Dabei prüfen:
- **Name:** Gleiche Schreibweise auf allen Plattformen? (z.B. "Hotel Alpenblick" vs "Alpenblick Hotel" vs "Hotel Alpen-Blick")
- **Adresse:** Straße, PLZ, Ort identisch? (Abkürzungen zählen als Abweichung)
- **Telefon:** Gleiche Nummer? (+43 664 = 0664 = tolerieret / aber andere Nummern = kritisch)
- **Plattformen prüfen:** Google Business, Booking.com, TripAdvisor, HolidayCheck, eigene Website, TVB-Eintrag

**NAP-Bewertung:**
- ✅ OK: Daten stimmen überein (Formatvarianten toleriert)
- ⚠️ WARNUNG: Leere Felder, nicht verifizierbar
- ❌ KRITISCH: Abweichender Name, andere Adresse, andere Telefonnummer

**NAP-Score:**
- 90–100%: Sehr gut
- 70–89%: Gut — kleine Korrekturen empfohlen
- 50–69%: Verbesserungsbedarf — konkrete Maßnahmen nötig
- unter 50%: Kritisch — sofortige Korrekturen nötig

### Schritt 3: 7 GEO-Lieferungen erstellen
Alle Texte direkt aus den Website-Informationen ableiten — **keine eigenständigen Schlussfolgerungen** (siehe Kernregel unten).

### Schritt 4: NAP-Report als Bonus-Lieferung 8 formatieren

Format für den NAP-Abschnitt im Gesamtdokument:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BONUS: NAP-KONSISTENZ-REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NAP-Score: [XX]% — [Bewertung]

REFERENZ-DATEN (Ihre offiziellen Stammdaten):
• Name:    [Name]
• Adresse: [Straße, PLZ Ort]
• Telefon: [Nummer]
• Web:     [URL]

PLATTFORM-ANALYSE:
[Plattform]     [✅/⚠️/❌]  [Befund]
Google Business  ✅         Konsistent
Booking.com      ❌         Name abweichend: "Appartements X" statt "X Appartements"
TripAdvisor      ⚠️         Telefonnummer fehlt
HolidayCheck     ✅         Konsistent
Eigene Website   ✅         Konsistent

SOFORTMASSNAHMEN:
1. [Konkrete Maßnahme]
2. [Konkrete Maßnahme]
3. [Konkrete Maßnahme]

WARUM DAS WICHTIG IST:
Inkonsistente NAP-Daten kosten Sie Google-Rankings und Direktbuchungen.
100% Konsistenz = mehr Vertrauen bei Google + Gästen.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Schritt 5: Gesamtdokument ausgeben
Reihenfolge im Dokument:
1. GEO-Score + Zusammenfassung
2. Lieferungen 1–7 (GEO-Optimierungstexte)
3. Bonus-Lieferung 8: NAP-Konsistenz-Report
4. Upsell-Hinweis ReviewRadar

### Schritt 6: E-Mail-Text + Rechnung
- E-Mail-Begleittext für Kundenversand formulieren
- Rechnungshinweis: € 149, Leistung "GEO-Optimierungspaket Professional inkl. NAP-Check, Website [url]"
- Empfänger: Betrieb (Name, Adresse von Website)
- Hinweis: Gernot versendet manuell von gernotriedel@icloud.com

---

## KERNREGEL: Keine eigenständigen Schlussfolgerungen

**Diese Regel gilt absolut und ausnahmslos für alle Ausarbeitungen:**

✅ Informationen von der Website werden **wörtlich und exakt** übernommen
✅ Regionale Angaben bleiben regional — sie werden **nicht dem Betrieb direkt zugeschrieben**
✅ Zahlen und Fakten werden **nur so verwendet wie sie explizit auf der Website stehen**
❌ Keine Verknüpfung von regionalen Daten mit dem Betrieb (Beispiel: "171 km Skipisten" der Region ≠ "Hotel mit Zugang zu 171 km Skipisten")
❌ Keine Interpretation oder Kombination von Informationen die so nicht auf der Website stehen
❌ Bei unklaren Zusammenhängen: Hinweis "bitte prüfen" statt eigener Interpretation

**Hintergrund:** In einem Test wurde die regionale Angabe "171 km Skipisten der SkiWelt" fälschlicherweise als "Hotel direkt am Skilift mit Zugang zu 171 km" formuliert. Korrekt wäre gewesen: Hotel Park liegt am Skigebiet St. Johann in Tirol (42 km Pisten). Dieser Fehler darf sich nicht wiederholen.

---

## Streamlit App — Technische Details

### Live-URL
https://geo-readiness-checker-mfk6vheyexwrqfkxmqvcav.streamlit.app

### NAP-Checker App (separates Tool, bei Bedarf)
https://nap-consistency-checker.streamlit.app
→ Nur relevant wenn Betriebe selbst prüfen sollen. Für Gernots eigene Arbeit: Chat-Abfrage bevorzugen (schneller, genauer).

### GitHub Repository
geo-readiness-checker (Gernots GitHub-Account)

### Datei
geo_checker_app.py

### Secrets (Streamlit Cloud)
```
ANTHROPIC_API_KEY = "..."
ZAPIER_WEBHOOK_URL = "..."
```

### App-Logik
1. Formular: Betriebsname, Ort, Website-URL, Betriebstyp
2. Claude-API-Aufruf (claude-opus-4-5, max_tokens: 4000)
3. JSON-Response mit Score, Faktoren, Quick Wins + vollständigem Paket
4. Anzeige: Score + Faktoren + Quick Wins (sichtbar)
5. Teaser-Block: 7 Lieferungen angekündigt aber **nicht gezeigt** (Verkaufsprinzip)
6. Kaufbutton → Webhook → Zapier → E-Mail an Betrieb + E-Mail an Gernot

### Verkaufsprinzip (wichtig!)
Der Betrieb sieht nach der Analyse:
- ✅ Score (0–50)
- ✅ Faktor-Analyse (5 Faktoren)
- ✅ Quick Wins (5 Maßnahmen)
- ✅ Teaser mit allen 7 Lieferungen angekündigt (Kacheln)
- ❌ Inhalte der Lieferungen NICHT sichtbar — erst nach Kauf

### JSON-Parsing (robuste Extraktion)
```python
if "```" in text:
    text = text.split("```")[1]
    if text.startswith("json"):
        text = text[4:]
start = text.find("{")
end = text.rfind("}") + 1
text = text[start:end]
return json.loads(text)
```

### JSON-Struktur (Claude-Prompt Ausgabe)
```json
{
  "gesamtscore": 0-50,
  "faktoren": [5 Objekte mit name/score/kommentar],
  "quickwins": [5 Objekte mit prioritaet/massnahme/impact],
  "zusammenfassung": "2-3 Sätze",
  "paket": {
    "faq": [10 Objekte mit frage/antwort],
    "h1_neu": "...",
    "h1_sub": "...",
    "usp_box": [4 Objekte mit emoji/titel/text],
    "keywords": [20 Strings],
    "google_business": "...",
    "meta_start": "...",
    "meta_zimmer": "...",
    "meta_preise": "...",
    "ueber_uns": "..."
  }
}
```

---

## Zapier-Automation

### Trigger
Webhooks by Zapier → Catch Hook (Pro-Feature, $20/Monat)

### Action 1 — E-Mail an Betrieb (Microsoft Outlook)
- To: {{email}} aus Webhook
- Subject: "Ihr GEO-Readiness Report ist fertig — {{betrieb}}"
- Body: Bestätigung + Lieferversprechen 24h + Kontaktdaten Gernot

### Action 2 — E-Mail an Gernot (Microsoft Outlook)
- To: kontakt@gernot-riedel.com
- Subject: "🔔 NEUER LEAD: {{betrieb}} (Score: {{score}}/50)"
- Body: Alle Lead-Daten + Handlungsanleitung (Claude öffnen → Texte erstellen → versenden → Rechnung)

### Webhook-Payload (JSON)
```json
{
  "betrieb": "...",
  "ort": "...",
  "email": "...",
  "website": "...",
  "typ": "...",
  "score": 0-50,
  "datum": "...",
  "zusammenfassung": "...",
  "faktoren": [...],
  "quickwins": [...],
  "produkt": "GEO-Optimierungspaket Professional",
  "preis": "149"
}
```

---

## Kontaktdaten Gernot Riedel

- **E-Mail:** kontakt@gernot-riedel.com (geschäftlich)
- **E-Mail:** gernotriedel@icloud.com (persönlich, für Pakete)
- **Telefon:** +43 676 7237811
- **Website:** gernot-riedel.com
- **Hashtags:** #GernotGoesAI #GernotGoesKI

---

## Häufige Trigger-Phrasen

Verwende diesen Skill wenn Gernot sagt:
- "Erstelle GEO-Optimierungspaket für [Betrieb]"
- "Analysiere [Website] für GEO"
- "GEO-Checker Code anpassen / erweitern"
- "Neuer Lead aus dem Checker"
- "Rechnung über 149 Euro ausstellen"
- "Fertige Texte per E-Mail senden"
- "NAP prüfen für [Betrieb]"
- "Prüfe NAP-Konsistenz"
- "Sind die Daten auf allen Plattformen konsistent?"

---

## Umsatzpotenzial (Referenz)

Bei 10 Outreaches/Monat + 20% Conversion:
- 2 GEO-Pakete à € 149 = € 298
- 1 ReviewRadar à € 349 = € 349
- **Gesamt: ca. € 650/Monat** bei ~40 Min Aufwand gesamt

NAP-Check ist im Paket enthalten — kein Zusatzaufwand, aber starkes Verkaufsargument:
→ "Sie bekommen GEO-Optimierung UND NAP-Konsistenz-Check für € 149"

# Phase 0 — Ist-Lage: GEO-Readiness-Checker & geo-radar

**Stand:** 21.07.2026 · **Autor:** Claude (Arbeitspaket „GEO-Checker auf gemeinsame Prüf-Logik mit geo-radar heben")
**Regel dieses Arbeitspakets:** Nichts umbauen, nur berichten. Es wurde nichts am Code verändert.

---

## Ist-Lage: GEO-Readiness-Checker (Repo `griedel69-spec/geo-readiness-checker`)

### Aufbau der App

Das Repo ist bewusst schlank — keine Ordnerstruktur, sondern zwei eigenständige Streamlit-Apps direkt im Hauptverzeichnis:

- **`geo_checker_app.py`** (ca. 830 Zeilen) — die eigentliche App, die auf Render läuft. Alles in einer Datei: Design (CSS), Messlogik, Bewertung, Formular, Ergebnisanzeige, Lead-Speicherung und Admin-Bereich.
- **`nap_checker_app.py`** — ein zweiter, separater NAP-Konsistenz-Checker (Name/Adresse/Telefon über Plattformen vergleichen). Er nutzt die Claude-API und optional die Google Places API. **Wichtig: Diese Datei wird auf Render gar nicht gestartet** — sie liegt nur im Repo.

Ablauf der Haupt-App: Formular (Betrieb, Ort, Website, Typ, E-Mail) → 18 technische Checkpunkte → je bestandener Punkt 2 Punkte → **Score 0–36** mit Prozentwert und Text-Einstufung (die geplante Ampel gibt es noch nicht, nur farbige Score-Zahl und vier Interpretationsstufen). Danach: Handlungsempfehlungen in drei Prioritätsstufen mit „So setzen Sie es um"-Anleitungen, Werbe-Block, Kontakt-Buttons.

**Keine KI im Spiel:** Anders als im alten Konzept (Claude-Analyse + Zapier-Webhook, siehe Skill-Doku) ist die aktuelle Version rein technisch-deterministisch — kein Anthropic-Aufruf, kein Zapier, kein E-Mail-Versand. Die E-Mail-Adresse des Besuchers wird nur gespeichert.

### Wie robots.txt und HTML abgerufen werden

Alles mit Python-Bordmitteln (`urllib.request`), ohne externe Bibliothek:

1. **robots.txt**: Abruf von `domain/robots.txt` mit User-Agent „GEO-Checker/1.0", 5 s Timeout. Selbstgebauter, einfacher Parser, der prüft, ob 5 KI-Bots (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, Bytespider) per `Disallow` gesperrt sind.
2. **sitemap.xml**: gleicher Abruf, nur „gibt es / gibt es nicht".
3. **Startseiten-HTML**: ein Abruf mit 10 s Timeout, Ladezeit wird gestoppt. Das HTML wird komplett mit **regulären Ausdrücken** durchsucht — Meta-Description, Title, H1, Canonical, Open Graph, JSON-LD, Alt-Texte, Wortzahl, interne Links usw. Kein BeautifulSoup, kein JavaScript-Rendering (`beautifulsoup4` steht zwar in den requirements, wird von dieser App aber nicht benutzt).

### Google-Sheets-Anbindung

- Sheet-ID `1bNBtr9w__zlPL_5XETHhewu3TZAc7qAR1wm8sRO5WVI` ist **fest im Code** (Tab „Leads").
- Zugriff über `gspread` + Service-Account `geo-checker-sheets@gen-lang-client-0004027448.iam.gserviceaccount.com`. Die Zugangsdaten kommen aus `st.secrets["gcp_service_account"]` — der Schlüssel liegt korrekt **nicht** im Repo, sondern in den Render-Umgebungsvariablen.
- Nach jeder Analyse wird eine Zeile angehängt: Datum, Betrieb, Ort, E-Mail, Website, Typ, Score, Max, Score %. Schlägt das fehl, gibt es nur eine Warnung — die Analyse läuft trotzdem durch.
- Passwortgeschützter Admin-Bereich (Secret `ADMIN_PASSWORD`) mit Session-Leads, CSV-Export und Link zum Sheet.

### Render-Anbindung

- **`render.yaml`** definiert einen Web-Service `geo-readiness-checker` (Python, `pip install -r requirements.txt`, Start über `start.sh`).
- **`start.sh`** baut beim Start aus den Render-Umgebungsvariablen (`ADMIN_PASSWORD`, `GCP_SERVICE_ACCOUNT_TOML`) die Datei `.streamlit/secrets.toml` und startet `streamlit run geo_checker_app.py` auf Port 10000.
- Schönheitsfehler: `render.yaml` deklariert `GCP_SERVICE_ACCOUNT_JSON`, das Skript liest `GCP_SERVICE_ACCOUNT_TOML` — funktioniert nur, weil die Variable im Render-Dashboard unter dem TOML-Namen angelegt wurde.
- **Deployed wird dieses Repo.** Der Auto-Deploy-Branch steht nur im Render-Dashboard; Standard ist `main` mit Auto-Deploy bei jedem Push → **jeder Push auf `main` geht sofort live** (im Dashboard verifizieren). Der Arbeitsbranch `claude/geo-checker-architecture-review-clxqy7` ist davon nicht betroffen.
- Nebenbefund: Laut alter Skill-Doku lief die App früher auf Streamlit Cloud (`geo-readiness-checker-…streamlit.app`). Falls diese Instanz noch aktiv ist, läuft sie parallel — beim Umzug klären/abschalten.

---

## Ist-Lage: geo-radar (Repo `griedel69-spec/geo-radar`, privat)

Lokales CLI-Werkzeug (kein Web, Windows-Doppelklick über `Neuer-Kunde.bat`), sauber modular mit Tests:

- **5 Signal-Module** in `src/`:
  - Signal 1 KI-Crawler-Zugang (robots.txt; Bot-Klassen A = sichtbarkeitskritisch → ROT, B = Training → GELB; 13 Bots)
  - Signal 2 Schema.org/JSON-LD (BeautifulSoup; Lodging-Typen, Kernfelder, FAQPage, sameAs; Ehrlichkeitsregel „vorhanden, aber defekt")
  - Signal 3 Maschinenlesbarkeit/SSR (sichtbarer Text, SPA-Erkennung, Adresse+Telefon im Roh-HTML; optional Playwright im Tiefenaudit)
  - Signal 4 NAP-Konsistenz (Website vs. Google Business, deterministisch normalisiert — nicht per Claude wie im NAP-Checker der Streamlit-App)
  - Signal 5 GBP-Vollständigkeit. Signale 4+5 teilen sich einen Places-Aufruf, laufen nur mit `--deep`.
- **Ampel-Logik ist Standard:** GRÜN/GELB/ROT/**UNBEKANNT** („Null Halluzination — UNBEKANNT statt raten"), Schwellen dokumentiert in CLAUDE.md.
- Drei Stufen: `scanner.py` (Batch, CSV-Rangliste), `report.py` (Befund-PDF, reportlab), `production.py` (kostenpflichtige Lösungs-Bausteine per Claude-API, nur mit Auftragsnummer). Umfangreiche Tests je Modul.

---

## Das Wichtigste für die Umzugs-Entscheidung

1. **Null gemeinsamer Code.** Der Checker misst mit eigenem Regex-Code grob dasselbe wie Signale 1–3, aber einfacher und teils anders (5 Bots statt Klassen A/B; „schema.org kommt im HTML vor" statt echter JSON-LD-Validierung; kein UNBEKANNT — was nicht messbar ist, zählt teils als bestanden, teils als durchgefallen).
2. **Die Signal-Module sind bereits als Bibliothek nutzbar** (`from signal1_robots import check_robots`) — Einbindung in die Streamlit-App ist technisch problemlos; die Ampel-Logik inkl. UNBEKANNT gibt es geschenkt.
3. **Achtung beim Umbau:** Push auf `main` im Checker-Repo deployed vermutlich sofort auf Render — Umbau komplett auf dem Arbeitsbranch, Merge erst wenn fertig.
4. Für das Gesamtpaket (PDF per Mail, Benachrichtigung an Gernot, Verkaufs-Brücke) existiert im Checker **keinerlei** Versand-Infrastruktur — `reportlab` steht in den requirements, wird aber nicht benutzt; E-Mail-Versand gibt es nirgends. Wird komplett neu gebaut.

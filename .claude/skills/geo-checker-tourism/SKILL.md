---
name: geo-checker-tourism
description: GEO-Readiness Checker and optimization package creation for tourism businesses in the DACH region (Austria, Germany, Switzerland). Use when creating a GEO optimization package for a hotel, analyzing a tourism website for AI visibility, developing the Streamlit checker app, or working with the geo-radar signal modules / Ampel logic.
---

# GEO-Checker Tourism — Skill für Gernot Riedel Tourism Consulting

Automatisierte GEO-Sichtbarkeitsprüfung (Ampel) + optionales Optimierungspaket für Tourismus-Betriebe (Hotels, TVBs, DMOs) im DACH-Raum.

**Stand: 22.07.2026 — vollständig überarbeitet.** Der Checker läuft seit dieser Überarbeitung nicht mehr auf einem Claude-API-Score, sondern auf den deterministischen Signal-Modulen des Schwester-Repos **geo-radar** und liefert eine Ampel (GRÜN/GELB/ROT/UNBEKANNT) statt eines 0–50-Scores. Ältere Chat-Historie, Screenshots oder Erinnerungen, die von "Score", "Zapier" oder "streamlit.app" sprechen, beziehen sich auf die **abgelöste Vorversion** — für alles Technische gilt ab hier der neue Stand.

---

## Produktportfolio

### GEO-Optimierungspaket Professional — € 149 (einmalig)
Das kostenpflichtige Kernprodukt. **8 fertige Bausteine** für einen Betrieb:

1. **Strukturierter Datensatz (digitaler Steckbrief)** — Schema.org/JSON-LD-Auszeichnung als Beherbergungsbetrieb (Hotel/BedAndBreakfast/…). Behebt das häufigste ROT-Ergebnis des kostenlosen Checks ("Strukturierte Betriebsdaten").
2. **FAQ-Sektion** — 10 Fragen & Antworten, KI-optimiert
3. **H1-Titel + Subheadline** — Startseite neu
4. **USP-Box** — 4 Alleinstellungsmerkmale
5. **Lokale Keywords** — 20 Begriffe für die Region
6. **Google Business Profil-Text** — max 750 Zeichen, keyword-reich
7. **Meta-Descriptions** — Startseite, Zimmer, Preise
8. **"Über uns" neu** — 250–300 Wörter, KI-lesbar

**Preis:** € 149 einmalig, kein Abo · **Lieferung:** fertig formatiertes Dokument, i.d.R. per E-Mail innerhalb 24h

### ReviewRadar — ab € 149 (einmalig)
Upsell nach GEO-Paket bzw. bei GELB/ROT-Ampel direkt mitbeworben. Bewertungsanalyse für Hotels — eigener, ausführlicher Skill: `reviewradar`.
- **Quick Insight** — € 149 (1 Plattform, bis 200 Bewertungen)
- **Professional** — € 349 (2 Plattformen, bis 400 Bewertungen) ← Bestseller
- **Platin** — € 849 (3 Plattformen, 800+ Bewertungen, Markteinordnung & GEO-Readiness, USP-Matrix) ← empfohlen
- **ReviewRadar Plus** — € 1.950 (vollständige Platin-Analyse + 4h-Workshop vor Ort, für das Führungsteam)

Link: gernot-riedel.com/hotelbewertungen-analyse-mehr-umsatz-direktbuchungen-reviewradar/

Verwandtes, aber **separates** Produkt: destinationsweites Screening für TVBs/DMOs (alle Mitgliedsbetriebe einer Kategorie, Ampel + Destinations-Ranking, via geo-radar `scanner.py`). Eigener Vertriebs-Thread, nicht Teil dieses technischen Skills.

---

## Wie der kostenlose Checker heute funktioniert (Ampel statt Score)

### Live
- **App:** https://geo-readiness-checker.onrender.com (Render, Free-Tier — durch einen UptimeRobot-Monitor, ID 802425159, alle 5 Min. wach gehalten, daher kein Kaltstart)
- **Eingebettet auf:** gernot-riedel.com/geo-readiness-check-hotel/ (iframe)
- **GitHub:** `griedel69-spec/geo-readiness-checker` (öffentlich). `main` = automatisch deployed (Render Auto-Deploy: On Commit) — **nie direkt auf `main` pushen ohne getesteten Stand**, jeder Push geht sofort live.
- **Frühere Streamlit-Cloud-Instanz der Haupt-App wurde gelöscht.** `nap_checker_app.py` (separater NAP-Konsistenz-Checker, eigenständiges Tool) läuft weiterhin bewusst auf Streamlit Cloud — **diese Datei nicht löschen**, sie ist die Live-Quelle dieser anderen App.

### Ablauf
1. Formular: Betriebsname, Ort, Website-URL, Betriebstyp, E-Mail
2. **Signale 1–3** aus dem geo-radar-Repo prüfen die Website (kein KI-Aufruf, reine HTTP/Parsing-Checks, daher kostenlos):
   - **Signal 1** — KI-Zugang (robots.txt, Bot-Klassen A/B)
   - **Signal 2** — Strukturierte Betriebsdaten (Schema.org/JSON-LD, Lodging-Entität)
   - **Signal 3** — Maschinenlesbarkeit der Startseite (Adresse/Telefon im Roh-HTML, SPA-Erkennung)
3. **Gesamt-Ampel** aus den drei Signalen (`signals/__init__.py::compute_overall`): ein ROT → ROT; sonst GELB wenn GELB/UNBEKANNT dabei; GRÜN nur wenn alle drei GRÜN. "Null Halluzination" — was nicht messbar ist, wird ehrlich als UNBEKANNT ausgewiesen, nie geraten.
4. Zusätzlich **14 ergänzende technische Checkpunkte** (HTTPS, Ladezeit, Viewport, Sitemap, Canonical, interne Links, Meta-Description, Title, H1, Alt-Texte, Open Graph, lang/hreflang …) — eigener Regex-Code in `geo_checker_app.py`, in der UI zugeklappt unter "Technische Details für Ihren Webentwickler".
5. **Kurz-Befund-PDF** (eine Seite, `befund_pdf.py`/reportlab) wird automatisch erzeugt und **per E-Mail an den Betrieb verschickt** — bei GELB/ROT mit Verkaufs-Brücke zum € 149-Paket.
6. **Benachrichtigung an Gernot bei jedem Versand** (nicht erst beim Kauf) — bei GELB/ROT als "💰 VERKAUFSCHANCE" markiert, PDF im Anhang.
7. Lead landet im Google Sheet (Spalten: Datum, Betrieb, Ort, E-Mail, Website, Typ, Ampel, Signale, Versand-Status).

### Verkaufsprinzip
Anders als in der Vorversion sieht der Betrieb heute **sofort und kostenlos** seinen technischen Befund (Ampel + Details + PDF) — das ist bewusst großzügig, um Vertrauen zu schaffen. **Nicht enthalten** sind die 8 fertigen Text-Bausteine des € 149-Pakets — die bleiben das kostenpflichtige Upsell, das nach der Ampel beworben wird ("Ihre Ampel steht auf {Ampel} — wir bringen sie auf GRÜN").

### Mail-Versand (technisch wichtig)
Render blockt ausgehende SMTP-Verbindungen (GMX/iCloud liefen nachweislich in Timeouts). Versand läuft daher über die **Brevo-Web-API** (`BREVO_API_KEY` + `MAIL_FROM` als Render-Umgebungsvariablen; SMTP bleibt als Fallback im Code, funktioniert aber praktisch nicht von Render aus). In Brevo muss "Authorised IPs" deaktiviert bleiben (Render-Server haben wechselnde Adressen). `NOTIFY_EMAIL` (Standard: kontakt@gernot-riedel.com) bestimmt den Empfänger der Verkaufschance-Benachrichtigung. Diagnose + Test-Mail-Knopf: Admin-Bereich der App (Passwort `ADMIN_PASSWORD`).

### Google Sheet
Sheet-ID `1bNBtr9w__zlPL_5XETHhewu3TZAc7qAR1wm8sRO5WVI`, Tab "Leads". Zugriff über Service-Account `geo-checker-sheets@gen-lang-client-0004027448.iam.gserviceaccount.com` (Schlüssel in Render-Variable `GCP_SERVICE_ACCOUNT_TOML`, nicht im Repo). Schreiblogik in `sheets.py` — schreibt bündig ab Spalte A, migriert bei Bedarf automatisch eine neue Kopfzeile (Altdaten aus der Vorversion bleiben darunter erhalten).

---

## Workflow: Bezahltes € 149-Paket ausliefern

**Wichtig — anders als in der Vorversion:** Die 8 Bausteine werden **nicht** direkt in einem Claude-Chat aus `web_fetch` heraus formuliert, sondern über das dafür gebaute CLI-Werkzeug im **geo-radar**-Repo:

```
python src/production.py --auftrag <Auftragsnummer> <domain>
```

Dieses Skript (privates Repo `griedel69-spec/geo-radar`) hat eigene Kostensicherungen (Start nur mit Pflicht-Flag, Kostenbestätigung vor Lauf, Kostengrenzen) und einen eingebauten Halluzinationsschutz (Marker `[bitte prüfen und ergänzen]` für Unbekanntes, separater Kontrolldurchlauf). Es ist der **primäre Weg**, um ein bestelltes Paket zu erzeugen.

**Fallback / falls ohne CLI direkt im Chat gearbeitet wird:** dann gilt die Kernregel unten absolut und ausnahmslos.

### Schritt 1: Website analysieren (Fallback-Weg)
```
web_fetch(url) → Inhalte lesen
```
Relevante Daten notieren: Name, Adresse, Telefon, Zimmertypen, USPs, Region, Aktivitäten, Besonderheiten.

### Schritt 2: 8 Bausteine erstellen
Alle Texte direkt aus den Website-Informationen ableiten — keine eigenständigen Schlussfolgerungen (siehe Kernregel).

### Schritt 3: Ausgabe formatieren
Als strukturiertes Dokument mit klaren Abschnitten je Baustein.

### Schritt 4: E-Mail-Text + Rechnung
- E-Mail-Begleittext für Kundenversand formulieren
- Rechnung über den `ausgangsrechnung`-Skill: € 149, Leistung "GEO-Optimierungspaket Professional, Website [url]"
- Empfänger: Betrieb (Name, Adresse von Website)

---

## KERNREGEL: Keine eigenständigen Schlussfolgerungen

**Diese Regel gilt absolut und ausnahmslos für alle Ausarbeitungen — egal ob über `production.py` oder manuell im Chat:**

✅ Informationen von der Website werden **wörtlich und exakt** übernommen
✅ Regionale Angaben bleiben regional — sie werden **nicht dem Betrieb direkt zugeschrieben**
✅ Zahlen und Fakten werden **nur so verwendet wie sie explizit auf der Website stehen**
❌ Keine Verknüpfung von regionalen Daten mit dem Betrieb (Beispiel: "171 km Skipisten" der Region ≠ "Hotel mit Zugang zu 171 km Skipisten")
❌ Keine Interpretation oder Kombination von Informationen die so nicht auf der Website stehen
❌ Bei unklaren Zusammenhängen: Hinweis "bitte prüfen" statt eigener Interpretation

**Hintergrund:** In einem Test wurde die regionale Angabe "171 km Skipisten der SkiWelt" fälschlicherweise als "Hotel direkt am Skilift mit Zugang zu 171 km" formuliert. Korrekt wäre gewesen: Hotel Park liegt am Skigebiet St. Johann in Tirol (42 km Pisten). Dieser Fehler darf sich nicht wiederholen.

---

## Technischer Aufbau (Repo geo-readiness-checker)

- `geo_checker_app.py` — Streamlit-App: Formular, Ampel-Anzeige, 14 Zusatz-Checks, Handlungsempfehlungen, Verkaufs-Brücke, Admin-Bereich
- `signals/` — **unverändert übernommene** Kopie der Signal-Module 1–3 aus geo-radar (Herkunfts-Commit in `signals/__init__.py` gepinnt: `c6546a3839829776ccbfc3b24d384057e4ad1817`). Änderungen an der Prüf-Logik gehören ins geo-radar-Repo, danach hierher nachkopieren und den Commit-Stand aktualisieren.
- `befund.py` — baut aus den drei Signal-Ergebnissen die Ampel + Klartext + Empfehlungen
- `befund_pdf.py` — erzeugt das einseitige Kurz-Befund-PDF (reportlab)
- `mailer.py` — Versand (Brevo bevorzugt, SMTP-Fallback), inkl. Diagnose-Funktionen
- `sheets.py` — Google-Sheets-Schreiblogik (Spalte-A-bündig, Kopfzeilen-Migration)
- `nap_checker_app.py` — **separates** Tool (NAP-Konsistenz), läuft auf Streamlit Cloud, nicht Teil des Render-Deploys, nicht löschen
- `tests/` — 26 automatisierte Tests (`python -m pytest tests/`)

### Render-Umgebungsvariablen
`ADMIN_PASSWORD`, `GCP_SERVICE_ACCOUNT_TOML`, `BREVO_API_KEY`, `MAIL_FROM`, `NOTIFY_EMAIL`, `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASS` (Fallback, praktisch ungenutzt)

### geo-radar (Schwester-Repo, privat: `griedel69-spec/geo-radar`)
CLI-Tool, drei Stufen aus derselben Codebasis: `scanner.py` (kostenloser Batch-Scan vieler Betriebe, z.B. für TVB-Destinations-Screening), `report.py` (Einzel-PDF), `production.py` (bezahlte Bausteine, s.o.). Die Signale 1–3 sind hier die **Quelle** — der Checker im anderen Repo hält nur eine gepinnte Kopie.

---

## Kontaktdaten Gernot Riedel

- **E-Mail:** kontakt@gernot-riedel.com (geschäftlich, auch Standard-Absender/Empfänger im automatisierten Mail-Versand)
- **E-Mail:** gernotriedel@icloud.com (persönlich — nicht mehr Teil des automatisierten Versand-Workflows)
- **Telefon:** +43 676 7237811
- **Website:** gernot-riedel.com
- **Adresse:** Gernot Riedel Tourism Consulting e.U., Uferstrasse 4, A-5751 Maishofen
- **Hashtags:** #GernotGoesAI #GernotGoesKI

---

## Häufige Trigger-Phrasen

Verwende diesen Skill wenn Gernot sagt:
- "GEO-Checker Code anpassen / erweitern"
- "Warum zeigt der Checker [X] an" / Fragen zur Ampel-Logik
- "Bezahltes Paket für [Betrieb] erstellen" / "GEO-Optimierungspaket für [Betrieb]"
- "Neuer Lead aus dem Checker" (→ Google Sheet prüfen)
- "Rechnung über 149 Euro ausstellen"
- "Mail-Versand funktioniert nicht" / SMTP-/Brevo-Diagnose
- "Signal-Module aktualisieren" / Sync mit geo-radar

---

## Umsatzpotenzial (Referenz, unverändert seit Vorversion)

Bei 10 Outreaches/Monat + 20% Conversion:
- 2 GEO-Pakete à € 149 = € 298
- 1 ReviewRadar à € 349 = € 349
- **Gesamt: ca. € 650/Monat** bei ~40 Min Aufwand gesamt

Zusätzliches, separates Potenzial: destinationsweites Screening für TVBs (eigener Vertriebs-Thread, siehe oben) — noch kein Pilot gefahren, keine Preislogik fixiert.

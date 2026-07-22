# Gesamtpaket: Gemeinsame Prüf-Logik + Ampel + PDF-Versand

**Stand: 21.07.2026 — LIVE auf Render.** Kompletter Testlauf bestanden
(Analyse haus-steger.at, PDF an Betrieb, Benachrichtigung an Gernot).

**Wichtige Betriebsfakten:**
- **Mail-Versand läuft über die Brevo-Web-API** (`BREVO_API_KEY` + `MAIL_FROM`
  in den Render-Umgebungsvariablen). Grund: Render blockt ausgehende
  SMTP-Verbindungen (GMX/iCloud liefen in Timeouts). SMTP bleibt als
  Fallback im Code. In Brevo muss „Authorised IPs" deaktiviert bleiben,
  weil Render-Server wechselnde Adressen haben.
- Diagnose + Test-Mail-Knopf: Admin-Bereich der App.
- Alte Streamlit-Cloud-Instanz (`geo_checker_app.py`) wurde gelöscht;
  der NAP-Checker läuft dort weiter.
- Auto-Deploy auf Render: „On Commit" — Push auf `main` geht automatisch live.
- Ergebnisseite gestrafft: Ampel vorn, die 14 Zusatz-Checkpunkte zugeklappt
  unter „Technische Details für Ihren Webentwickler".
- **Render-Kaltstart abgedeckt via UptimeRobot.** Die Render-Free-Instanz
  schläft nach ~15 Min ohne Zugriff ein (Kaltstart ~50 s). Ein UptimeRobot-
  Monitor (HTTP, alle 5 Min auf `https://geo-readiness-checker.onrender.com/`,
  Monitor-ID 802425159) hält sie warm → kein Kaltstart. Render-Upgrade auf den
  bezahlten Tarif damit **optional** — erst nötig bei großem, parallelem
  Ad-Traffic (Leistung/Parallelität), nicht mehr wegen des Kaltstarts.
  Hinweis: Render-Free hat ein Monats-Stundenkontingent (~750 h) — 24/7 warm
  ≈ 730 h; bei mehreren Free-Diensten ggf. Monitor auf Tagesfenster begrenzen.

**Ready-to-go-to-market (Stand 22.07.2026):** Soft Launch startklar
(kostenlose Funnel-Front trägt real getestet; Kaltstart via UptimeRobot
gelöst). Seiten-Funnel konsistent (GEO-Seite + ReviewRadar-Seite + Seminar
abgeglichen). Offene Geschäftsentscheidung: Kaufweg bleibt vorerst
„Reply-to-E-Mail" (kein Checkout) — für Soft Launch okay, Skalierung später.
Auslieferung des € 149-Pakets: manueller CLI-Lauf via `geo-radar/production.py`
(8 Bausteine inkl. Schema-Steckbrief) — funktioniert, Automatisierung = P2.

**Noch offen (Kosmetik / Aufräumen):**
- `nap_checker_app.py` liegt ungenutzt im Repo (alter Zapier/Claude-4-5-Stand)
  → entfernen oder bewusst deployen.
- Alte Streamlit-Cloud-NAP-Instanz prüfen/abschalten.
- Alter „ZAPIER SETUP"-Tab im Google Sheet kann gelöscht werden.
- Google-Kundenstimmen-Link in Schritt 3 der GEO-Seite von Gernot klick-testen
  (aus der Cloud-Session nicht auflösbar — Proxy blockt Google).

---

*Ursprüngliche Umsetzungs-Doku (Historie):*

## Was umgesetzt wurde

1. **Gemeinsame Signal-Module** — `signals/` enthält die unveränderten
   Module 1–3 aus geo-radar (Stand-Commit steht in `signals/__init__.py`).
   Änderungen an der Prüf-Logik gehören ins geo-radar-Repo, danach die drei
   Dateien nachkopieren.
2. **Ampel statt 0–36-Score** — Gesamt-Ampel GRÜN/GELB/ROT/UNBEKANNT nach der
   geo-radar-Regel (ein ROT → ROT; UNBEKANNT ist kein GRÜN). Die früheren
   Regex-Checkpunkte robots.txt, Schema.org, JSON-LD und Textsubstanz sind
   ersetzt; die übrigen **14** laufen als „Ergänzende technische Checkpunkte"
   ohne Punktwert weiter.
3. **Kurz-Befund-PDF** (`befund_pdf.py`, reportlab, 1 Seite, gebrandet) wird
   nach jeder Analyse erzeugt: Ampel, drei Prüfbereiche mit Beleg,
   Maßnahmen, bei GELB/ROT Verkaufs-Brücke (€ 149-Paket).
4. **Automatischer Mail-Versand** (`mailer.py`): PDF an den Betrieb +
   **Benachrichtigung an Gernot bei jedem Versand** (bei GELB/ROT als
   VERKAUFSCHANCE markiert, PDF hängt mit an). Ohne SMTP-Konfiguration
   fällt die App sauber auf einen PDF-Download-Button zurück.
5. **Google Sheet**: neue Zeilen schreiben jetzt
   `Datum, Betrieb, Ort, E-Mail, Website, Typ, Ampel, Signale, Versand`
   — **bündig ab Spalte A** (`sheets.py`). Hintergrund: Im Alt-Sheet stand
   ein manuell angelegter Kopf (Score-0-50-Layout), wodurch die bisherige App
   ihre Zeilen versetzt ab Spalte G angehängt hat. Beim ersten Schreiben fügt
   die neue Version automatisch die passende Kopfzeile oben ein; Alt-Daten
   bleiben unverändert darunter. **Keine manuelle Sheet-Arbeit nötig.**
6. **Tests**: `tests/` (17 Stück) — Ampel-Regeln, PDF-Erzeugung, Mail-Logik
   (ohne echten SMTP), und als Regressionstest der haus-steger-Befund:
   generische WordPress-Typen müssen ROT bleiben. `python -m pytest tests/`

## Verifiziert (in dieser Session)

- Alle 17 Tests grün; alle Module kompilieren.
- App im echten Chromium gerendert (Startseite + kompletter Analyse-Lauf
  gegen eine lokale Test-Website): Ampel-Karte, drei Signal-Karten mit
  Belegen, PDF-Download, Mail-Fallback, 14 Zusatz-Checkpunkte, Verkaufs-Brücke.
- Muster-PDF erzeugt (GELB/ROT-Fall).

## Vor dem Merge auf `main` (= Live-Gang) erledigen

- [ ] **Render-Umgebungsvariablen setzen:** `SMTP_HOST`, `SMTP_PORT` (587),
      `SMTP_USER`, `SMTP_PASS`, optional `MAIL_FROM`,
      `NOTIFY_EMAIL` (Standard: kontakt@gernot-riedel.com).
      GMX: `mail.gmx.net` (Achtung: bei GMX „POP3/IMAP-Zugriff erlauben"
      aktivieren). Outlook/Microsoft 365: `smtp.office365.com`.
      Ohne diese Werte läuft die App, versendet aber nicht (nur Download).
- [x] ~~Variablen-Name `GCP_SERVICE_ACCOUNT_TOML` im Dashboard prüfen~~ —
      per Beleg erledigt (21.07.2026): Die Live-App schreibt erfolgreich ins
      Sheet, der Name im Dashboard stimmt also mit `start.sh` überein.
- [x] ~~Sheet-Spaltenköpfe umbenennen~~ — entfällt, macht die App jetzt
      automatisch (siehe Punkt 5).
- [ ] Einmal mit echtem SMTP einen Testlauf machen (eigene E-Mail als
      „Betrieb" eintragen) und beide Mails prüfen.
- [ ] Merge auf `main` → Render deployed automatisch.
- [ ] Alte Streamlit-Cloud-Instanz prüfen/abschalten:
      https://geo-readiness-checker-mfk6vheyexwrqfkxmqvcav.streamlit.app
      (aus der Cloud-Session nicht erreichbar — bitte kurz im Browser öffnen).

## Offen aus Phase 0.5

- Live-Score-Vergleich für haus-steger.at (Netz-Allowlist der Cloud-Session) —
  Skript liegt in `docs/phase0/vergleich_haus_steger.py`, läuft auf jedem
  normalen Rechner. Nach dem Umbau ist er v. a. noch als Beleg interessant.

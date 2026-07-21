# Gesamtpaket: Gemeinsame Prüf-Logik + Ampel + PDF-Versand

**Stand:** 21.07.2026 · Branch `claude/geo-checker-architecture-review-clxqy7` · **noch nicht auf `main` gemergt, nichts deployed.**

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
   `Datum, Betrieb, Ort, E-Mail, Website, Typ, Ampel, Signale, Versand`.
   Im bestehenden Sheet die Spaltenköpfe G/H/I einmalig von
   „Score/Max/Score %" auf „Ampel/Signale/Versand" umbenennen.
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
- [ ] **Achtung Variablen-Name:** `render.yaml` verlangt jetzt korrekt
      `GCP_SERVICE_ACCOUNT_TOML` (vorher stand dort fälschlich `_JSON`).
      Im Render-Dashboard prüfen, dass die Variable so heißt.
- [ ] Einmal mit echtem SMTP einen Testlauf machen (eigene E-Mail als
      „Betrieb" eintragen) und beide Mails prüfen.
- [ ] Sheet-Spaltenköpfe umbenennen (siehe oben).
- [ ] Merge auf `main` → Render deployed automatisch.
- [ ] Alte Streamlit-Cloud-Instanz (falls noch aktiv) abschalten.

## Offen aus Phase 0.5

- Live-Score-Vergleich für haus-steger.at (Netz-Allowlist der Cloud-Session) —
  Skript liegt in `docs/phase0/vergleich_haus_steger.py`, läuft auf jedem
  normalen Rechner. Nach dem Umbau ist er v. a. noch als Beleg interessant.

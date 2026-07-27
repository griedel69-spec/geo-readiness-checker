# geo-readiness-checker

GEO-Radar für Gernot Riedel Tourism Consulting e.U.: kostenloser
KI-Sichtbarkeits-Check für Tourismusbetriebe (Ampel GRÜN/GELB/ROT/UNBEKANNT)
plus bezahltes GEO-Optimierungspaket (€ 149).

**Lies zuerst `.claude/skills/geo-checker-tourism/SKILL.md`** — das ist die
laufend gepflegte, ausführliche Projekt-Doku (Produktportfolio, Live-Status,
Workflows, Kontaktdaten). Diese Datei hier ist nur der schnelle Einstieg.

## Live-Status (siehe SKILL.md für Details/Datum)

- App: https://geo-readiness-checker.onrender.com — deployed automatisch
  von `main` (Render Auto-Deploy: On Commit). **Nie direkt auf `main`
  pushen ohne getesteten Stand** — jeder Push geht sofort live.
- Eingebettet auf gernot-riedel.com/geo-readiness-check-hotel/ (iframe).
- Ampel-Logik kommt aus den vendored Signal-Modulen in `signals/`
  (Quelle: privates Schwester-Repo `geo-radar`, Herkunfts-Commit gepinnt
  in `signals/__init__.py`).

## Wichtigste Dateien

| Datei/Ordner | Zweck |
|---|---|
| `geo_checker_app.py` | Streamlit-App (Formular, Ampel, 14 Zusatzchecks) |
| `signals/` | Ampel-Prüflogik (vendored aus geo-radar) |
| `befund.py` / `befund_pdf.py` | Ampel-Auswertung + Kurz-Befund-PDF |
| `mailer.py` / `sheets.py` | Mailversand (Brevo) / Google-Sheet-Leads |
| `templates/geo_optimierungspaket/` | Gebrandeter Word-Report-Generator fürs bezahlte Paket — **jeder** Betriebs-Report läuft hierüber, siehe README dort |
| `nap_checker_app.py` | separates Tool, läuft auf Streamlit Cloud — **nicht löschen** |
| `docs/UMSETZUNG-GESAMTPAKET.md` | Laufender Stand/Changelog des Gesamtprojekts |
| `.claude/skills/geo-checker-tourism/` | Vollständige Projekt-Doku (siehe oben) |

## Design/Marke

GEO-Radar-Sub-Marke, konsistent in App/PDF/Word-Report: Navy `#1A2332`,
Gold `#C9A84C`, Ampelfarben `#27AE60`/`#E67E22`/`#C0392B`, Schrift Archivo
(Überschriften) + Open Sans (Fließtext). Nicht mit dem allgemeinen
grün/orangenen Beratungs-CI von Gernot Riedel Tourism Consulting
verwechseln (eigener Design-Skill `gernot-riedel-tourism-consulting-design`).

## Branch-Regel

Entwickeln auf einem Feature-Branch, **nicht direkt auf `main`** — Merge
auf `main` erst nach expliziter Freigabe (löst sofortigen Render-Deploy aus).

## Sonstiges

- `python -m pytest tests/` — 26 Tests, vor jedem Merge grün halten.
- Kontakt: kontakt@gernot-riedel.com · +43 676 7237811 · gernot-riedel.com

# Übergabe-Notiz — Stand 21.07.2026

Arbeitspaket: **GEO-Checker auf gemeinsame Prüf-Logik mit geo-radar heben.**
Dieser Ordner (`docs/phase0/`) sichert den kompletten Zwischenstand, damit auf
jedem Rechner nahtlos weitergearbeitet werden kann. Am App-Code wurde
**nichts** verändert; `main` ist unberührt (Render deployed von `main`!).

---

## Was ist erledigt

1. **Phase 0 — Ist-Lage beider Repos** → `BERICHT-phase0-ist-lage.md`
   (Aufbau Checker, robots/HTML-Abruf, Google-Sheets, Render-Anbindung, geo-radar-Überblick, Umzugs-Hinweise).
2. **Phase 0.5 — Score-Vergleich für haus-steger.at** → `score-vergleich-haus-steger.md`
   Kernbefund (deterministisch belegt): Signal 2 stuft die vom Live-Checker
   gemeldeten JSON-LD-Typen (WebPage, ReadAction, BreadcrumbList, ListItem,
   WebSite) als **ROT** ein — der Regex-Checker wertet dieselben Daten als
   2× bestanden (JSON-LD ✅, Schema.org ✅). Score fiele von 30/36 auf max. 26/36.
   Kosten: 0 USD.
3. **Vergleichsskript** → `vergleich_haus_steger.py` (lauffähig, portabel).
4. **Rohergebnis des blockierten Cloud-Laufs** → `ergebnis-blockierter-lauf.json`
   (zeigt den Nebenbefund: Regex-Checker liefert bei nicht erreichbarer
   Website 8/36 mit 4 „bestandenen" Punkten; Signale sagen 3× UNBEKANNT).

## Was ist offen

- [ ] **Live-Lauf des Vergleichs** gegen haus-steger.at. In der Cloud-Session
      scheiterte er an der Netzwerk-Allowlist der Umgebung (Gateway-403).
      Auf einem normalen Notebook läuft er ohne diese Hürde — siehe unten.
      Danach die `n. e.`-Zellen in der Tabelle von
      `score-vergleich-haus-steger.md` füllen.
- [ ] Entscheidung von Gernot: Signal-Module per Kopie oder als gemeinsames
      Paket (z. B. pip-installierbar aus geo-radar) in den Checker.
- [ ] Danach das Gesamtpaket: gemeinsame Signal-Module, Ampel statt
      0-36-Score, Kurz-Befund-PDF per Mail, E-Mail-Benachrichtigung an
      Gernot bei jedem Versand, Verkaufs-Brücke bei GELB/ROT.
- [ ] Im Render-Dashboard verifizieren: Auto-Deploy-Branch (vermutlich `main`).
- [ ] Klären, ob die alte Streamlit-Cloud-Instanz noch parallel läuft.
- [ ] Kleinkram fürs Aufräumen notiert: `render.yaml` deklariert
      `GCP_SERVICE_ACCOUNT_JSON`, `start.sh` liest `GCP_SERVICE_ACCOUNT_TOML`.

## So geht es auf dem anderen Notebook weiter

```bash
# 1. Beide Repos nebeneinander holen/aktualisieren
git clone https://github.com/griedel69-spec/geo-readiness-checker.git   # oder: git pull
git clone https://github.com/griedel69-spec/geo-radar.git               # privat, Login nötig
cd geo-readiness-checker
git checkout claude/geo-checker-architecture-review-clxqy7               # DIESER Branch = der Stand hier

# 2. Abhängigkeiten für das Vergleichsskript
pip install requests beautifulsoup4 lxml

# 3. Offenen Live-Vergleich nachholen (kostenlos, ~30 Sekunden)
python docs/phase0/vergleich_haus_steger.py > docs/phase0/ergebnis-live-lauf.json
```

Liegt geo-radar woanders: `--radar <pfad>/geo-radar/src` anhängen.
Andere Domain testen: `--domain hotel-beispiel.at`.

## Regeln, die weiter gelten

- **Nie auf `main` pushen** — Render deployed von dort automatisch.
  Alle Arbeit auf `claude/geo-checker-architecture-review-clxqy7`.
- Produktionsstufe des geo-radar (`production.py`, Claude-API) nur mit
  Auftrag/Bestätigung — für Diagnosen nie nötig.
- Kein Umbau ohne Freigabe von Gernot; Phase 0/0.5 waren reine Diagnose.
